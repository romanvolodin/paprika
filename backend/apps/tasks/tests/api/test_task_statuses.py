from http import HTTPStatus
import json

import pytest

from apps.tasks.models import TaskStatus


pytestmark = pytest.mark.django_db


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def member_company(auth_user, company, company_membership_factory):
    company_membership_factory(user=auth_user, company=company, role="admin")
    return company


class TestListTaskStatuses:
    def test_returns_the_starter_set(self, auth_client, member_company):
        response = auth_client.get(
            f"/api/v1/companies/{member_company.id}/task-statuses/"
        )

        assert response.status_code == HTTPStatus.OK
        items = response.json()["items"]
        assert {i["name"] for i in items} == {
            "Не начата",
            "В работе",
            "Готова",
            "Отмена",
            "На паузе",
        }
        assert [i["name"] for i in items if i["is_default"]] == ["Не начата"]

    def test_side_states_have_a_null_order(self, auth_client, member_company):
        items = auth_client.get(
            f"/api/v1/companies/{member_company.id}/task-statuses/"
        ).json()["items"]

        by_name = {i["name"]: i for i in items}
        assert by_name["Не начата"]["order"] == 0
        assert by_name["Отмена"]["order"] is None

    def test_search_matches_the_name(self, auth_client, member_company):
        response = auth_client.get(
            f"/api/v1/companies/{member_company.id}/task-statuses/?search=работе"
        )

        assert [i["name"] for i in response.json()["items"]] == ["В работе"]

    def test_non_member_gets_a_404(
        self, auth_client, company, company_membership_factory
    ):
        company_membership_factory(company=company)  # some other user

        response = auth_client.get(f"/api/v1/companies/{company.id}/task-statuses/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company):
        response = client.get(f"/api/v1/companies/{company.id}/task-statuses/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestCreateTaskStatus:
    def test_creates_a_status(self, auth_client, auth_user, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-statuses/",
            {"name": "На ревью", "color": "#112233", "order": 3},
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert (body["name"], body["color"], body["order"]) == (
            "На ревью",
            "#112233",
            3,
        )
        assert body["is_default"] is False
        assert body["created_by"]["id"] == auth_user.id

    def test_a_new_default_replaces_the_old_one(self, auth_client, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-statuses/",
            {"name": "Новая", "color": "#112233", "is_default": True},
        )

        assert response.status_code == HTTPStatus.CREATED
        defaults = TaskStatus.objects.filter(company=member_company, is_default=True)
        assert [s.name for s in defaults] == ["Новая"]

    def test_duplicate_name_gets_a_409(self, auth_client, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-statuses/",
            {"name": "Готова", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.CONFLICT

    def test_rejects_an_invalid_color(self, auth_client, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-statuses/",
            {"name": "X", "color": "red"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_gets_a_404(
        self, auth_client, company, company_membership_factory
    ):
        company_membership_factory(company=company)  # some other user

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/task-statuses/",
            {"name": "X", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGetTaskStatus:
    def test_returns_the_status_for_a_company_member(
        self, auth_client, auth_user, task_status, company_membership_factory
    ):
        company_membership_factory(
            user=auth_user, company=task_status.company, role="admin"
        )

        response = auth_client.get(f"/api/v1/task-statuses/{task_status.id}/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["id"] == task_status.id

    def test_non_member_gets_a_404(
        self, auth_client, task_status, company_membership_factory
    ):
        company_membership_factory(company=task_status.company)  # some other user

        response = auth_client.get(f"/api/v1/task-statuses/{task_status.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, task_status):
        response = client.get(f"/api/v1/task-statuses/{task_status.id}/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestUpdateTaskStatus:
    @pytest.fixture
    def member_status(self, auth_user, task_status, company_membership_factory):
        company_membership_factory(
            user=auth_user, company=task_status.company, role="admin"
        )
        return task_status

    def test_updates_the_given_fields_only(self, auth_client, auth_user, member_status):
        response = _patch_json(
            auth_client,
            f"/api/v1/task-statuses/{member_status.id}/",
            {"color": "#00FF00"},
        )

        assert response.status_code == HTTPStatus.OK
        member_status.refresh_from_db()
        assert member_status.color == "#00FF00"
        assert member_status.name.startswith("Task Status")
        assert member_status.updated_by == auth_user

    def test_order_can_be_cleared(self, auth_client, member_status):
        member_status.order = 5
        member_status.save()

        response = _patch_json(
            auth_client, f"/api/v1/task-statuses/{member_status.id}/", {"order": None}
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["order"] is None

    def test_making_a_status_default_unsets_the_previous_default(
        self, auth_client, member_status
    ):
        response = _patch_json(
            auth_client,
            f"/api/v1/task-statuses/{member_status.id}/",
            {"is_default": True},
        )

        assert response.status_code == HTTPStatus.OK
        defaults = TaskStatus.objects.filter(
            company=member_status.company, is_default=True
        )
        assert list(defaults) == [member_status]

    def test_duplicate_name_gets_a_409(self, auth_client, member_status):
        response = _patch_json(
            auth_client,
            f"/api/v1/task-statuses/{member_status.id}/",
            {"name": "Готова"},
        )

        assert response.status_code == HTTPStatus.CONFLICT

    @pytest.mark.parametrize("field", ["name", "color", "is_default"])
    def test_null_is_rejected_for_required_fields(
        self, auth_client, member_status, field
    ):
        response = _patch_json(
            auth_client, f"/api/v1/task-statuses/{member_status.id}/", {field: None}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_gets_a_404(
        self, auth_client, task_status, company_membership_factory
    ):
        company_membership_factory(company=task_status.company)  # some other user

        response = _patch_json(
            auth_client, f"/api/v1/task-statuses/{task_status.id}/", {"name": "X"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestDeleteTaskStatus:
    @pytest.fixture
    def member_status(self, auth_user, task_status, company_membership_factory):
        company_membership_factory(
            user=auth_user, company=task_status.company, role="admin"
        )
        return task_status

    def test_deletes_an_unused_status(self, auth_client, member_status):
        response = auth_client.delete(f"/api/v1/task-statuses/{member_status.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not TaskStatus.objects.filter(pk=member_status.pk).exists()

    def test_a_status_in_use_gets_a_409(
        self,
        auth_client,
        member_status,
        shot_task_factory,
        shot_factory,
        project_factory,
    ):
        project = project_factory(company=member_status.company)
        shot_task_factory(shot=shot_factory(project=project), status=member_status)

        response = auth_client.delete(f"/api/v1/task-statuses/{member_status.id}/")

        assert response.status_code == HTTPStatus.CONFLICT
        assert TaskStatus.objects.filter(pk=member_status.pk).exists()

    def test_non_member_gets_a_404(
        self, auth_client, task_status, company_membership_factory
    ):
        company_membership_factory(company=task_status.company)  # some other user

        response = auth_client.delete(f"/api/v1/task-statuses/{task_status.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert TaskStatus.objects.filter(pk=task_status.pk).exists()


class TestTaskStatusWritesAreCompanyAdminOnly:
    def test_non_admin_member_can_list_but_not_create_update_or_delete(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        task_status_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")
        task_status = task_status_factory(company=company, name="In progress")

        listed = auth_client.get(f"/api/v1/companies/{company.id}/task-statuses/")
        created = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/task-statuses/",
            {"name": "На ревью", "color": "#aabbcc"},
        )
        updated = _patch_json(
            auth_client, f"/api/v1/task-statuses/{task_status.id}/", {"name": "Renamed"}
        )
        deleted = auth_client.delete(f"/api/v1/task-statuses/{task_status.id}/")

        assert listed.status_code == HTTPStatus.OK
        assert created.status_code == HTTPStatus.FORBIDDEN
        assert updated.status_code == HTTPStatus.FORBIDDEN
        assert deleted.status_code == HTTPStatus.FORBIDDEN
        task_status.refresh_from_db()
        assert task_status.name == "In progress"
        assert not TaskStatus.objects.filter(company=company, name="На ревью").exists()
