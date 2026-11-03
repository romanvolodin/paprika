from decimal import Decimal
from http import HTTPStatus
import json

import pytest

from apps.tasks.models import ShotTask


pytestmark = pytest.mark.django_db


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def member_shot(auth_user, shot, project_membership_factory):
    project_membership_factory(user=auth_user, project=shot.project)
    return shot


@pytest.fixture
def client_shot(auth_user, shot, project_membership_factory):
    """A shot in a project where the logged-in user is a read-only `client`."""
    project_membership_factory(user=auth_user, project=shot.project, role="client")
    return shot


def _url(shot):
    return f"/api/v1/shots/{shot.id}/tasks/"


def _status(project, name):
    return project.company.task_statuses.get(name=name)


class TestListShotTasks:
    def test_returns_the_shots_tasks_in_creation_order(
        self, auth_client, member_shot, task_factory, shot_task_factory
    ):
        project = member_shot.project
        first = shot_task_factory(shot=member_shot, task=task_factory(project=project))
        second = shot_task_factory(shot=member_shot, task=task_factory(project=project))
        shot_task_factory()  # on some other shot

        response = auth_client.get(_url(member_shot))

        assert response.status_code == HTTPStatus.OK
        assert [i["id"] for i in response.json()["items"]] == [first.id, second.id]

    def test_item_carries_the_tracking_and_the_nested_task(
        self, auth_client, auth_user, member_shot, task_factory, shot_task_factory
    ):
        task = task_factory(project=member_shot.project, name="Замена неба")
        shot_task = shot_task_factory(
            shot=member_shot,
            task=task,
            assignee=auth_user,
            estimated_hours=Decimal("4.5"),
            actual_hours=Decimal("2"),
        )

        item = auth_client.get(_url(member_shot)).json()["items"][0]

        assert item["id"] == shot_task.id
        assert item["shot_id"] == member_shot.id
        assert item["status_id"] == shot_task.status_id
        assert item["assignee"]["id"] == auth_user.id
        assert item["estimated_hours"] == 4.5
        assert item["actual_hours"] == 2.0
        assert item["task"]["code"] == task.code
        assert item["task"]["name"] == "Замена неба"
        assert item["task"]["type_id"] == task.type_id
        assert item["task"]["shot_ids"] == [member_shot.id]

    def test_unset_tracking_fields_are_null(
        self, auth_client, member_shot, task_factory, shot_task_factory
    ):
        shot_task_factory(
            shot=member_shot, task=task_factory(project=member_shot.project)
        )

        item = auth_client.get(_url(member_shot)).json()["items"][0]

        assert item["assignee"] is None
        assert item["estimated_hours"] is None
        assert item["actual_hours"] is None

    def test_a_shot_without_tasks_returns_an_empty_list(self, auth_client, member_shot):
        response = auth_client.get(_url(member_shot))

        assert response.json() == {"items": []}

    def test_read_only_client_can_list(self, auth_client, client_shot):
        response = auth_client.get(_url(client_shot))

        assert response.status_code == HTTPStatus.OK

    def test_non_member_gets_a_404(self, auth_client, shot, project_membership_factory):
        project_membership_factory(project=shot.project)  # some other user

        response = auth_client.get(_url(shot))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot):
        response = client.get(_url(shot))

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestPlaceTaskOnShot:
    def test_places_a_task_with_the_default_status(
        self, auth_client, auth_user, member_shot, task_factory
    ):
        task = task_factory(project=member_shot.project)

        response = _post_json(auth_client, _url(member_shot), {"task_id": task.id})

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert body["shot_id"] == member_shot.id
        assert body["task"]["id"] == task.id
        assert body["task"]["shot_ids"] == [member_shot.id]
        assert body["status_id"] == _status(member_shot.project, "Не начата").id
        assert body["assignee"] is None
        assert body["estimated_hours"] is None
        assert body["created_by"]["id"] == auth_user.id

    def test_places_a_task_with_all_tracking_fields(
        self, auth_client, auth_user, member_shot, task_factory
    ):
        task = task_factory(project=member_shot.project)
        in_progress = _status(member_shot.project, "В работе")

        response = _post_json(
            auth_client,
            _url(member_shot),
            {
                "task_id": task.id,
                "status_id": in_progress.id,
                "assignee_id": auth_user.id,
                "estimated_hours": 6.25,
                "actual_hours": 1.5,
            },
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert body["status_id"] == in_progress.id
        assert body["assignee"]["id"] == auth_user.id
        assert body["estimated_hours"] == 6.25
        assert body["actual_hours"] == 1.5

    def test_the_same_task_can_go_on_several_shots(
        self, auth_client, auth_user, member_shot, shot_factory, task_factory
    ):
        task = task_factory(project=member_shot.project)
        other_shot = shot_factory(project=member_shot.project)

        first = _post_json(auth_client, _url(member_shot), {"task_id": task.id})
        second = _post_json(auth_client, _url(other_shot), {"task_id": task.id})

        assert first.status_code == second.status_code == HTTPStatus.CREATED
        assert ShotTask.objects.filter(task=task).count() == 2

    def test_placing_the_same_task_twice_gets_a_409(
        self, auth_client, member_shot, task_factory
    ):
        task = task_factory(project=member_shot.project)
        _post_json(auth_client, _url(member_shot), {"task_id": task.id})

        response = _post_json(auth_client, _url(member_shot), {"task_id": task.id})

        assert response.status_code == HTTPStatus.CONFLICT
        assert task.code in response.content.decode()
        assert ShotTask.objects.count() == 1

    def test_losing_a_race_is_a_409(
        self, auth_client, member_shot, task_factory, mocker
    ):
        from apps.tasks.api import views

        task = task_factory(project=member_shot.project)
        _post_json(auth_client, _url(member_shot), {"task_id": task.id})
        # The cheap pre-check misses it, the database constraint doesn't.
        mocker.patch.object(
            views.ShotTask.objects,
            "filter",
            return_value=mocker.Mock(exists=lambda: False),
        )

        response = _post_json(auth_client, _url(member_shot), {"task_id": task.id})

        assert response.status_code == HTTPStatus.CONFLICT

    def test_a_task_of_another_project_is_rejected(
        self, auth_client, member_shot, task_factory
    ):
        foreign = task_factory()

        response = _post_json(auth_client, _url(member_shot), {"task_id": foreign.id})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not ShotTask.objects.exists()

    def test_an_unknown_task_is_rejected(self, auth_client, member_shot):
        response = _post_json(auth_client, _url(member_shot), {"task_id": 999999})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_task_id_is_required(self, auth_client, member_shot):
        response = _post_json(auth_client, _url(member_shot), {})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_a_status_of_another_company_is_rejected(
        self, auth_client, member_shot, task_factory, task_status_factory
    ):
        task = task_factory(project=member_shot.project)

        response = _post_json(
            auth_client,
            _url(member_shot),
            {"task_id": task.id, "status_id": task_status_factory().id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_without_a_default_status_one_must_be_given(
        self, auth_client, member_shot, task_factory
    ):
        task = task_factory(project=member_shot.project)
        member_shot.project.company.task_statuses.update(is_default=False)

        response = _post_json(auth_client, _url(member_shot), {"task_id": task.id})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "default" in response.content.decode()

    def test_an_assignee_must_be_a_project_member(
        self, auth_client, member_shot, task_factory, user_factory
    ):
        task = task_factory(project=member_shot.project)

        response = _post_json(
            auth_client,
            _url(member_shot),
            {"task_id": task.id, "assignee_id": user_factory().id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not ShotTask.objects.exists()

    def test_another_project_member_can_be_the_assignee(
        self,
        auth_client,
        member_shot,
        task_factory,
        user_factory,
        project_membership_factory,
    ):
        colleague = user_factory()
        project_membership_factory(user=colleague, project=member_shot.project)
        task = task_factory(project=member_shot.project)

        response = _post_json(
            auth_client,
            _url(member_shot),
            {"task_id": task.id, "assignee_id": colleague.id},
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["assignee"]["id"] == colleague.id

    @pytest.mark.parametrize("field", ["estimated_hours", "actual_hours"])
    @pytest.mark.parametrize("value", [-1, 1.234, 10_000_000])
    def test_rejects_invalid_hours(
        self, auth_client, member_shot, task_factory, field, value
    ):
        task = task_factory(project=member_shot.project)

        response = _post_json(
            auth_client, _url(member_shot), {"task_id": task.id, field: value}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_zero_hours_are_allowed(self, auth_client, member_shot, task_factory):
        task = task_factory(project=member_shot.project)

        response = _post_json(
            auth_client, _url(member_shot), {"task_id": task.id, "estimated_hours": 0}
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["estimated_hours"] == 0

    def test_read_only_client_gets_a_403(self, auth_client, client_shot, task_factory):
        task = task_factory(project=client_shot.project)

        response = _post_json(auth_client, _url(client_shot), {"task_id": task.id})

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not ShotTask.objects.exists()

    def test_non_member_gets_a_404(
        self, auth_client, shot, task_factory, project_membership_factory
    ):
        project_membership_factory(project=shot.project)  # some other user
        task = task_factory(project=shot.project)

        response = _post_json(auth_client, _url(shot), {"task_id": task.id})

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGetShotTask:
    def test_returns_the_shot_task_for_a_project_member(
        self, auth_client, auth_user, shot_task, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=shot_task.shot.project)

        response = auth_client.get(f"/api/v1/shot-tasks/{shot_task.id}/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["task"]["code"] == shot_task.task.code

    def test_non_member_gets_a_404(
        self, auth_client, shot_task, project_membership_factory
    ):
        project_membership_factory(project=shot_task.shot.project)  # some other user

        response = auth_client.get(f"/api/v1/shot-tasks/{shot_task.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot_task):
        response = client.get(f"/api/v1/shot-tasks/{shot_task.id}/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestUpdateShotTask:
    @pytest.fixture
    def member_shot_task(self, auth_user, shot_task, project_membership_factory):
        project_membership_factory(user=auth_user, project=shot_task.shot.project)
        return shot_task

    def _url(self, shot_task):
        return f"/api/v1/shot-tasks/{shot_task.id}/"

    def test_changes_the_status(self, auth_client, auth_user, member_shot_task):
        done = _status(member_shot_task.shot.project, "Готова")

        response = _patch_json(
            auth_client, self._url(member_shot_task), {"status_id": done.id}
        )

        assert response.status_code == HTTPStatus.OK
        member_shot_task.refresh_from_db()
        assert member_shot_task.status == done
        assert member_shot_task.updated_by == auth_user

    def test_changes_hours_and_leaves_the_rest(self, auth_client, member_shot_task):
        status_before = member_shot_task.status_id

        response = _patch_json(
            auth_client,
            self._url(member_shot_task),
            {"estimated_hours": 8, "actual_hours": 3.25},
        )

        assert response.status_code == HTTPStatus.OK
        member_shot_task.refresh_from_db()
        assert member_shot_task.estimated_hours == Decimal("8")
        assert member_shot_task.actual_hours == Decimal("3.25")
        assert member_shot_task.status_id == status_before

    def test_hours_can_be_cleared(self, auth_client, member_shot_task):
        member_shot_task.estimated_hours = Decimal("5")
        member_shot_task.save()

        response = _patch_json(
            auth_client, self._url(member_shot_task), {"estimated_hours": None}
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["estimated_hours"] is None

    def test_assigns_and_unassigns(self, auth_client, auth_user, member_shot_task):
        assigned = _patch_json(
            auth_client, self._url(member_shot_task), {"assignee_id": auth_user.id}
        )
        unassigned = _patch_json(
            auth_client, self._url(member_shot_task), {"assignee_id": None}
        )

        assert assigned.json()["assignee"]["id"] == auth_user.id
        assert unassigned.status_code == HTTPStatus.OK
        assert unassigned.json()["assignee"] is None

    def test_an_assignee_must_be_a_project_member(
        self, auth_client, member_shot_task, user_factory
    ):
        response = _patch_json(
            auth_client, self._url(member_shot_task), {"assignee_id": user_factory().id}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_status_cannot_be_null(self, auth_client, member_shot_task):
        response = _patch_json(
            auth_client, self._url(member_shot_task), {"status_id": None}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_a_status_of_another_company_is_rejected(
        self, auth_client, member_shot_task, task_status_factory
    ):
        response = _patch_json(
            auth_client,
            self._url(member_shot_task),
            {"status_id": task_status_factory().id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_the_task_and_the_shot_cannot_be_changed(
        self, auth_client, member_shot_task, task_factory
    ):
        original_task, original_shot = (
            member_shot_task.task_id,
            member_shot_task.shot_id,
        )
        other = task_factory(project=member_shot_task.shot.project)

        response = _patch_json(
            auth_client,
            self._url(member_shot_task),
            {"task_id": other.id, "shot_id": 1},
        )

        assert response.status_code == HTTPStatus.OK
        member_shot_task.refresh_from_db()
        assert (member_shot_task.task_id, member_shot_task.shot_id) == (
            original_task,
            original_shot,
        )

    def test_rejects_invalid_hours(self, auth_client, member_shot_task):
        response = _patch_json(
            auth_client, self._url(member_shot_task), {"actual_hours": -2}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_progress_is_independent_per_shot(
        self,
        auth_client,
        auth_user,
        project_membership_factory,
        shot_factory,
        task_factory,
        shot_task_factory,
    ):
        task = task_factory()
        project_membership_factory(user=auth_user, project=task.project)
        on_a = shot_task_factory(shot=shot_factory(project=task.project), task=task)
        on_b = shot_task_factory(shot=shot_factory(project=task.project), task=task)
        done = _status(task.project, "Готова")

        _patch_json(
            auth_client, f"/api/v1/shot-tasks/{on_a.id}/", {"status_id": done.id}
        )

        on_a.refresh_from_db()
        on_b.refresh_from_db()
        assert on_a.status == done
        assert on_b.status != done

    def test_read_only_client_gets_a_403(
        self, auth_client, auth_user, shot_task, project_membership_factory
    ):
        project_membership_factory(
            user=auth_user, project=shot_task.shot.project, role="client"
        )

        response = _patch_json(
            auth_client, f"/api/v1/shot-tasks/{shot_task.id}/", {"estimated_hours": 1}
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_non_member_gets_a_404(
        self, auth_client, shot_task, project_membership_factory
    ):
        project_membership_factory(project=shot_task.shot.project)  # some other user

        response = _patch_json(
            auth_client, f"/api/v1/shot-tasks/{shot_task.id}/", {"estimated_hours": 1}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestUpdateOwnShotTask:
    @pytest.fixture
    def own_task(self, auth_user, shot_task, project_membership_factory):
        project_membership_factory(
            user=auth_user, project=shot_task.shot.project, role="executor"
        )
        shot_task.assignee = auth_user
        shot_task.save()
        return shot_task

    def _patch(self, client, shot_task, payload):
        return _patch_json(client, f"/api/v1/shot-tasks/{shot_task.id}/", payload)

    def test_the_assignee_can_enter_actual_hours(self, auth_client, own_task):
        response = self._patch(auth_client, own_task, {"actual_hours": "3.5"})

        assert response.status_code == HTTPStatus.OK
        own_task.refresh_from_db()
        assert own_task.actual_hours == Decimal("3.5")

    def test_the_assignee_can_change_the_status_and_hours_together(
        self, auth_client, own_task
    ):
        done = _status(own_task.shot.project, "Готова")

        response = self._patch(
            auth_client, own_task, {"status_id": done.id, "actual_hours": "2"}
        )

        assert response.status_code == HTTPStatus.OK
        own_task.refresh_from_db()
        assert own_task.status == done
        assert own_task.actual_hours == Decimal("2")

    def test_the_assignee_cannot_change_the_planned_hours_or_the_assignee(
        self, auth_client, own_task
    ):
        planned = self._patch(auth_client, own_task, {"estimated_hours": "1"})
        reassigned = self._patch(auth_client, own_task, {"assignee_id": None})

        assert planned.status_code == HTTPStatus.FORBIDDEN
        assert reassigned.status_code == HTTPStatus.FORBIDDEN

    def test_an_empty_update_is_not_an_own_change(self, auth_client, own_task):
        response = self._patch(auth_client, own_task, {})

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_hours_of_someone_elses_task_need_task_edit(
        self, auth_client, own_task, user_factory, project_membership_factory
    ):
        other = user_factory()
        project_membership_factory(
            user=other, project=own_task.shot.project, role="executor"
        )
        own_task.assignee = other
        own_task.save()

        response = self._patch(auth_client, own_task, {"actual_hours": "1"})

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestRemoveTaskFromShot:
    def test_removes_the_placement_but_keeps_the_task(
        self, auth_client, auth_user, shot_task, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=shot_task.shot.project)

        response = auth_client.delete(f"/api/v1/shot-tasks/{shot_task.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not ShotTask.objects.filter(pk=shot_task.pk).exists()
        shot_task.task.refresh_from_db()  # still there

    def test_the_task_can_be_placed_again_afterwards(
        self, auth_client, auth_user, shot_task, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=shot_task.shot.project)
        auth_client.delete(f"/api/v1/shot-tasks/{shot_task.id}/")

        response = _post_json(
            auth_client, _url(shot_task.shot), {"task_id": shot_task.task_id}
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_read_only_client_gets_a_403(
        self, auth_client, auth_user, shot_task, project_membership_factory
    ):
        project_membership_factory(
            user=auth_user, project=shot_task.shot.project, role="client"
        )

        response = auth_client.delete(f"/api/v1/shot-tasks/{shot_task.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert ShotTask.objects.filter(pk=shot_task.pk).exists()

    def test_non_member_gets_a_404(
        self, auth_client, shot_task, project_membership_factory
    ):
        project_membership_factory(project=shot_task.shot.project)  # some other user

        response = auth_client.delete(f"/api/v1/shot-tasks/{shot_task.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert ShotTask.objects.filter(pk=shot_task.pk).exists()
