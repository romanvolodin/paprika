from http import HTTPStatus
import json

import pytest

from apps.chat.models import Message
from apps.shots.models import Shot, ShotGroup
from apps.tasks.models import ShotTask, Task


pytestmark = pytest.mark.django_db


def _url(project) -> str:
    return f"/api/v1/projects/{project.id}/shot-imports/"


def _post(client, project, payload):
    return client.post(
        _url(project), data=json.dumps(payload), content_type="application/json"
    )


def _errors(response) -> list[dict]:
    return response.json()["detail"]


@pytest.fixture
def member_project(auth_user, project, project_membership_factory):
    project_membership_factory(user=auth_user, project=project)
    return project


class TestCreatesShots:
    def test_creates_shots_with_default_status_and_timecode(
        self, auth_client, auth_user, member_project
    ):
        response = _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {"name": "VRG_01_0150", "rec_timecode": 4000},
                    {"name": "VRG_01_0160"},
                ]
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json() == {
            "shots_created": 2,
            "groups_created": 0,
            "tasks_created": 0,
            "messages_created": 0,
        }
        shots = Shot.objects.filter(project=member_project).order_by("name")
        assert [shot.name for shot in shots] == ["VRG_01_0150", "VRG_01_0160"]
        assert [shot.rec_timecode for shot in shots] == [4000, None]
        assert all(shot.status.is_default for shot in shots)
        assert all(shot.created_by == auth_user for shot in shots)
        assert all(shot.duration is None for shot in shots)


class TestGroups:
    def test_creates_missing_groups_and_reuses_existing(
        self, auth_client, member_project, shot_group_factory
    ):
        existing = shot_group_factory(project=member_project, name="01 СЕРИЯ")

        response = _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {"name": "A", "groups": ["01 СЕРИЯ"]},
                    {"name": "B", "groups": ["01 СЕРИЯ", "02 СЕРИЯ"]},
                    {"name": "C", "groups": ["02 СЕРИЯ"]},
                ]
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["groups_created"] == 1
        assert ShotGroup.objects.filter(project=member_project).count() == 2
        second = ShotGroup.objects.get(project=member_project, name="02 СЕРИЯ")
        assert set(Shot.objects.get(name="A").groups.all()) == {existing}
        assert set(Shot.objects.get(name="B").groups.all()) == {existing, second}
        assert set(Shot.objects.get(name="C").groups.all()) == {second}

    def test_group_names_are_trimmed_and_repeats_in_a_row_collapse(
        self, auth_client, member_project
    ):
        response = _post(
            auth_client,
            member_project,
            {"shots": [{"name": "A", "groups": [" 01 ", "01"]}]},
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert ShotGroup.objects.filter(project=member_project).count() == 1
        assert Shot.objects.get(name="A").groups.count() == 1

    def test_an_existing_group_of_another_project_is_not_reused(
        self, auth_client, member_project, shot_group_factory
    ):
        other = shot_group_factory(name="01 СЕРИЯ")

        _post(
            auth_client,
            member_project,
            {"shots": [{"name": "A", "groups": ["01 СЕРИЯ"]}]},
        )

        assert not Shot.objects.get(name="A").groups.filter(pk=other.pk).exists()
        assert ShotGroup.objects.filter(project=member_project).count() == 1


class TestTasks:
    def test_new_task_given_for_several_shots_is_created_once(
        self, auth_client, member_project, task_type_factory
    ):
        task_type = task_type_factory(company=member_project.company)
        new_task = {"name": "Вставка в монитор", "type_id": task_type.id}

        response = _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {"name": "A", "tasks": [new_task]},
                    {"name": "B", "tasks": [new_task]},
                ]
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["tasks_created"] == 1
        task = Task.objects.get(project=member_project)
        assert (task.name, task.type) == ("Вставка в монитор", task_type)
        assert task.code.startswith(task_type.abbreviation)
        placed = ShotTask.objects.filter(task=task)
        assert {shot_task.shot.name for shot_task in placed} == {"A", "B"}
        assert all(shot_task.status.is_default for shot_task in placed)

    def test_several_tasks_per_shot_existing_and_new(
        self, auth_client, member_project, task_factory, task_type_factory
    ):
        existing = task_factory(project=member_project)
        task_type = task_type_factory(company=member_project.company)

        response = _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {
                        "name": "A",
                        "tasks": [
                            {"task_id": existing.id},
                            {"name": "Клинап", "type_id": task_type.id},
                        ],
                    }
                ]
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["tasks_created"] == 1
        shot = Shot.objects.get(name="A")
        assert shot.shot_tasks.count() == 2
        assert Task.objects.filter(project=member_project).count() == 2
        assert shot.shot_tasks.filter(task=existing).exists()

    def test_the_same_new_name_with_different_types_makes_two_tasks(
        self, auth_client, member_project, task_type_factory
    ):
        first = task_type_factory(company=member_project.company)
        second = task_type_factory(company=member_project.company)

        response = _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {"name": "A", "tasks": [{"name": "Х", "type_id": first.id}]},
                    {"name": "B", "tasks": [{"name": "Х", "type_id": second.id}]},
                ]
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["tasks_created"] == 2

    def test_no_system_chat_messages_are_recorded(
        self, auth_client, member_project, task_type_factory
    ):
        task_type = task_type_factory(company=member_project.company)

        _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {
                        "name": "A",
                        "tasks": [{"name": "Х", "type_id": task_type.id}],
                    }
                ]
            },
        )

        assert not Message.objects.filter(type=Message.Type.SYSTEM).exists()


class TestMessages:
    def test_posts_user_messages_in_order_as_the_importing_user(
        self, auth_client, auth_user, member_project
    ):
        response = _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {"name": "A", "messages": ["  Текст задачи ", "Комментарий"]},
                    {"name": "B", "messages": ["Только комментарий"]},
                    {"name": "C"},
                ]
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["messages_created"] == 3
        shot_a = Shot.objects.get(name="A")
        messages = list(Message.objects.filter(shot=shot_a))
        assert [message.text for message in messages] == [
            "Текст задачи",
            "Комментарий",
        ]
        assert all(message.type == Message.Type.USER for message in messages)
        assert all(message.created_by == auth_user for message in messages)
        assert not Message.objects.filter(shot__name="C").exists()


class TestValidation:
    def test_one_invalid_row_creates_nothing_and_all_problems_are_listed(
        self,
        auth_client,
        member_project,
        shot_factory,
        task_factory,
        task_type_factory,
    ):
        shot_factory(project=member_project, name="TAKEN")
        foreign_task = task_factory()
        foreign_type = task_type_factory()
        good_type = task_type_factory(company=member_project.company)

        response = _post(
            auth_client,
            member_project,
            {
                "shots": [
                    {"name": "OK", "groups": ["G"]},
                    {"name": "TAKEN"},
                    {"name": "bad name"},
                    {"name": "OK"},
                    {"name": "", "messages": [" "]},
                    {
                        "name": "T",
                        "tasks": [
                            {"task_id": foreign_task.id},
                            {"name": "N", "type_id": foreign_type.id},
                            {"name": "M", "type_id": good_type.id},
                            {"name": "M", "type_id": good_type.id},
                        ],
                    },
                ]
            },
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        locs = [error["loc"] for error in _errors(response)]
        assert locs == [
            ["shots", 1, "name"],
            ["shots", 2, "name"],
            ["shots", 3, "name"],
            ["shots", 4, "name"],
            ["shots", 4, "messages", 0],
            ["shots", 5, "tasks", 0, "task_id"],
            ["shots", 5, "tasks", 1, "type_id"],
            ["shots", 5, "tasks", 3],
        ]
        assert Shot.objects.filter(project=member_project).count() == 1
        assert not ShotGroup.objects.filter(project=member_project).exists()
        assert not Task.objects.filter(project=member_project, name="M").exists()

    def test_too_long_message_is_rejected(self, auth_client, member_project, settings):
        settings.CHAT_MESSAGE_MAX_LENGTH = 5

        response = _post(
            auth_client,
            member_project,
            {"shots": [{"name": "A", "messages": ["123456"]}]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert _errors(response)[0]["loc"] == ["shots", 0, "messages", 0]
        assert not Shot.objects.filter(project=member_project).exists()

    def test_too_many_rows_are_rejected(self, auth_client, member_project, settings):
        settings.SHOT_IMPORT_MAX_ROWS = 2

        response = _post(
            auth_client,
            member_project,
            {"shots": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Shot.objects.filter(project=member_project).exists()

    def test_empty_list_is_rejected(self, auth_client, member_project):
        response = _post(auth_client, member_project, {"shots": []})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize(
        "task",
        [
            {},
            {"name": "Только имя"},
            {"task_id": 1, "name": "И то и другое", "type_id": 1},
        ],
    )
    def test_task_must_be_either_existing_or_new(
        self, auth_client, member_project, task
    ):
        response = _post(
            auth_client,
            member_project,
            {"shots": [{"name": "A", "tasks": [task]}]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_company_without_default_shot_status_is_rejected(
        self, auth_client, member_project
    ):
        member_project.company.shot_statuses.update(is_default=False)

        response = _post(auth_client, member_project, {"shots": [{"name": "A"}]})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Shot.objects.filter(project=member_project).exists()


class TestPermissions:
    def test_requires_authentication(self, client, project):
        response = _post(client, project, {"shots": [{"name": "A"}]})

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_non_member_gets_404(self, auth_client, project):
        response = _post(auth_client, project, {"shots": [{"name": "A"}]})

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert not Shot.objects.filter(project=project).exists()

    def test_client_role_gets_403(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="client")

        response = _post(auth_client, project, {"shots": [{"name": "A"}]})

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not Shot.objects.filter(project=project).exists()
