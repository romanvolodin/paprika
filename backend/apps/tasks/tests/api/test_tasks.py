from http import HTTPStatus
import json

import pytest

from apps.tasks.models import ShotTask, Task


pytestmark = pytest.mark.django_db


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def member_project(auth_user, project, project_membership_factory):
    project_membership_factory(user=auth_user, project=project)
    return project


@pytest.fixture
def client_project(auth_user, project, project_membership_factory):
    """A project in which the logged-in user has the read-only `client` role."""
    project_membership_factory(user=auth_user, project=project, role="client")
    return project


def _type_id(project, abbreviation="CLN"):
    return project.company.task_types.get(abbreviation=abbreviation).id


class TestListTasks:
    def test_returns_the_projects_tasks_newest_first(
        self, auth_client, member_project, task_factory
    ):
        older = task_factory(project=member_project)
        newer = task_factory(project=member_project)
        task_factory()  # a task of some other project

        response = auth_client.get(f"/api/v1/projects/{member_project.id}/tasks/")

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert [i["id"] for i in body["items"]] == [newer.id, older.id]
        assert (body["total"], body["page"], body["page_size"]) == (2, 1, 20)

    def test_item_shape(
        self, auth_client, member_project, task_factory, shot_task_factory, shot_factory
    ):
        task = task_factory(project=member_project, name="Замена неба", description="d")
        shot = shot_factory(project=member_project)
        shot_task_factory(shot=shot, task=task)

        item = auth_client.get(f"/api/v1/projects/{member_project.id}/tasks/").json()[
            "items"
        ][0]

        assert item["code"] == task.code
        assert item["name"] == "Замена неба"
        assert item["description"] == "d"
        assert item["type_id"] == task.type_id
        assert item["project_id"] == member_project.id
        assert item["shot_ids"] == [shot.id]

    def test_a_standalone_task_has_no_shots(
        self, auth_client, member_project, task_factory
    ):
        task_factory(project=member_project)

        item = auth_client.get(f"/api/v1/projects/{member_project.id}/tasks/").json()[
            "items"
        ][0]

        assert item["shot_ids"] == []

    def test_paginates(self, auth_client, member_project, task_factory):
        for _ in range(3):
            task_factory(project=member_project)

        body = auth_client.get(
            f"/api/v1/projects/{member_project.id}/tasks/?page=2&page_size=2"
        ).json()

        assert len(body["items"]) == 1
        assert body["total"] == 3

    def test_search_matches_the_name_or_the_code(
        self, auth_client, member_project, task_factory
    ):
        sky = task_factory(project=member_project, name="Замена неба")
        wires = task_factory(project=member_project, name="Клинап тросов")

        by_name = auth_client.get(
            f"/api/v1/projects/{member_project.id}/tasks/?search=неба"
        ).json()
        by_code = auth_client.get(
            f"/api/v1/projects/{member_project.id}/tasks/?search={wires.code.lower()}"
        ).json()

        assert [i["id"] for i in by_name["items"]] == [sky.id]
        assert [i["id"] for i in by_code["items"]] == [wires.id]

    def test_filters_by_type(self, auth_client, member_project, task_factory):
        company = member_project.company
        cleanup = task_factory(
            project=member_project, type=company.task_types.get(abbreviation="CLN")
        )
        task_factory(
            project=member_project, type=company.task_types.get(abbreviation="COMP")
        )

        body = auth_client.get(
            f"/api/v1/projects/{member_project.id}/tasks/?type={cleanup.type_id}"
        ).json()

        assert [i["id"] for i in body["items"]] == [cleanup.id]

    def test_read_only_client_can_list(self, auth_client, client_project, task_factory):
        task_factory(project=client_project)

        response = auth_client.get(f"/api/v1/projects/{client_project.id}/tasks/")

        assert response.status_code == HTTPStatus.OK

    def test_non_member_gets_a_404(
        self, auth_client, project, project_membership_factory
    ):
        project_membership_factory(project=project)  # some other user

        response = auth_client.get(f"/api/v1/projects/{project.id}/tasks/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project):
        response = client.get(f"/api/v1/projects/{project.id}/tasks/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestCreateTask:
    def test_creates_a_standalone_task_with_a_generated_code(
        self, auth_client, auth_user, member_project
    ):
        response = _post_json(
            auth_client,
            f"/api/v1/projects/{member_project.id}/tasks/",
            {
                "name": "Клинап тросов",
                "description": "Убрать тросы",
                "type_id": _type_id(member_project),
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert body["name"] == "Клинап тросов"
        assert body["description"] == "Убрать тросы"
        assert body["code"].startswith("CLN")
        assert len(body["code"]) == 7
        assert body["shot_ids"] == []
        assert body["created_by"]["id"] == auth_user.id
        assert Task.objects.get().project == member_project

    def test_description_is_optional(self, auth_client, member_project):
        response = _post_json(
            auth_client,
            f"/api/v1/projects/{member_project.id}/tasks/",
            {"name": "Финальные титры", "type_id": _type_id(member_project, "COMP")},
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["description"] == ""

    def test_two_tasks_may_share_a_name(self, auth_client, member_project):
        payload = {"name": "Замена неба", "type_id": _type_id(member_project)}
        url = f"/api/v1/projects/{member_project.id}/tasks/"

        first = _post_json(auth_client, url, payload)
        second = _post_json(auth_client, url, payload)

        assert first.status_code == second.status_code == HTTPStatus.CREATED
        assert first.json()["code"] != second.json()["code"]

    def test_type_is_required(self, auth_client, member_project):
        response = _post_json(
            auth_client, f"/api/v1/projects/{member_project.id}/tasks/", {"name": "X"}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_type_of_another_company_is_rejected(
        self, auth_client, member_project, task_type_factory
    ):
        foreign = task_type_factory()

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{member_project.id}/tasks/",
            {"name": "X", "type_id": foreign.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Task.objects.exists()

    def test_name_cannot_be_empty(self, auth_client, member_project):
        response = _post_json(
            auth_client,
            f"/api/v1/projects/{member_project.id}/tasks/",
            {"name": "", "type_id": _type_id(member_project)},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_read_only_client_gets_a_403(self, auth_client, client_project):
        response = _post_json(
            auth_client,
            f"/api/v1/projects/{client_project.id}/tasks/",
            {"name": "X", "type_id": _type_id(client_project)},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not Task.objects.exists()

    @pytest.mark.parametrize("role", ["executor", "freelancer"])
    def test_roles_without_the_permission_cannot_create(
        self, auth_client, auth_user, project, project_membership_factory, role
    ):
        project_membership_factory(user=auth_user, project=project, role=role)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/tasks/",
            {"name": "X", "type_id": _type_id(project)},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.parametrize("role", ["admin", "producer", "coordinator"])
    def test_other_roles_can_create(
        self, auth_client, auth_user, project, project_membership_factory, role
    ):
        project_membership_factory(user=auth_user, project=project, role=role)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/tasks/",
            {"name": "X", "type_id": _type_id(project)},
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_non_member_gets_a_404(
        self, auth_client, project, project_membership_factory
    ):
        project_membership_factory(project=project)  # some other user

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/tasks/",
            {"name": "X", "type_id": _type_id(project)},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGetTask:
    def test_returns_the_task_for_a_project_member(
        self, auth_client, member_project, task_factory
    ):
        task = task_factory(project=member_project)

        response = auth_client.get(f"/api/v1/tasks/{task.id}/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["code"] == task.code

    def test_non_member_gets_a_404(self, auth_client, task, project_membership_factory):
        project_membership_factory(project=task.project)  # some other user

        response = auth_client.get(f"/api/v1/tasks/{task.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, task):
        response = client.get(f"/api/v1/tasks/{task.id}/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestUpdateTask:
    @pytest.fixture
    def member_task(self, auth_user, task_factory, project_membership_factory):
        task = task_factory()
        project_membership_factory(user=auth_user, project=task.project)
        return task

    def test_updates_name_and_description(self, auth_client, auth_user, member_task):
        response = _patch_json(
            auth_client,
            f"/api/v1/tasks/{member_task.id}/",
            {"name": "Новое имя", "description": "Новое описание"},
        )

        assert response.status_code == HTTPStatus.OK
        member_task.refresh_from_db()
        assert (member_task.name, member_task.description) == (
            "Новое имя",
            "Новое описание",
        )
        assert member_task.updated_by == auth_user

    def test_changing_the_type_keeps_the_code(self, auth_client, member_task):
        original = member_task.code
        new_type = member_task.project.company.task_types.exclude(
            pk=member_task.type_id
        ).first()

        response = _patch_json(
            auth_client, f"/api/v1/tasks/{member_task.id}/", {"type_id": new_type.id}
        )

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["type_id"] == new_type.id
        assert body["code"] == original

    def test_code_cannot_be_changed(self, auth_client, member_task):
        original = member_task.code

        response = _patch_json(
            auth_client, f"/api/v1/tasks/{member_task.id}/", {"code": "HACK1234"}
        )

        assert response.status_code == HTTPStatus.OK
        member_task.refresh_from_db()
        assert member_task.code == original

    def test_type_of_another_company_is_rejected(
        self, auth_client, member_task, task_type_factory
    ):
        response = _patch_json(
            auth_client,
            f"/api/v1/tasks/{member_task.id}/",
            {"type_id": task_type_factory().id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize("field", ["name", "description", "type_id"])
    def test_null_is_rejected(self, auth_client, member_task, field):
        response = _patch_json(
            auth_client, f"/api/v1/tasks/{member_task.id}/", {field: None}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_read_only_client_gets_a_403(
        self, auth_client, auth_user, task, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=task.project, role="client")

        response = _patch_json(auth_client, f"/api/v1/tasks/{task.id}/", {"name": "X"})

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_non_member_gets_a_404(self, auth_client, task, project_membership_factory):
        project_membership_factory(project=task.project)  # some other user

        response = _patch_json(auth_client, f"/api/v1/tasks/{task.id}/", {"name": "X"})

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestDeleteTask:
    def test_deletes_the_task_and_its_placements(
        self, auth_client, auth_user, shot_task, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=shot_task.task.project)

        response = auth_client.delete(f"/api/v1/tasks/{shot_task.task_id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Task.objects.filter(pk=shot_task.task_id).exists()
        assert not ShotTask.objects.filter(pk=shot_task.pk).exists()

    def test_read_only_client_gets_a_403(
        self, auth_client, auth_user, task, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=task.project, role="client")

        response = auth_client.delete(f"/api/v1/tasks/{task.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Task.objects.filter(pk=task.pk).exists()

    def test_non_member_gets_a_404(self, auth_client, task, project_membership_factory):
        project_membership_factory(project=task.project)  # some other user

        response = auth_client.delete(f"/api/v1/tasks/{task.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Task.objects.filter(pk=task.pk).exists()
