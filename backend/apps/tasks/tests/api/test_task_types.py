from http import HTTPStatus
import json

import pytest

from apps.tasks.models import TaskType


pytestmark = pytest.mark.django_db


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def member_company(auth_user, company, company_membership_factory):
    company_membership_factory(user=auth_user, company=company, role="admin")
    return company


class TestListTaskTypes:
    def test_returns_the_starter_set(self, auth_client, member_company):
        response = auth_client.get(f"/api/v1/companies/{member_company.id}/task-types/")

        assert response.status_code == HTTPStatus.OK
        items = response.json()["items"]
        assert {(i["name"], i["abbreviation"]) for i in items} == {
            ("Композ", "COMP"),
            ("Клинап", "CLN"),
            ("Трекинг", "TRK"),
            ("Ротоскоп", "ROTO"),
        }

    def test_item_shape(self, auth_client, member_company):
        item = auth_client.get(
            f"/api/v1/companies/{member_company.id}/task-types/"
        ).json()["items"][0]

        assert set(item) >= {
            "id",
            "company_id",
            "name",
            "abbreviation",
            "color",
            "created_at",
            "updated_at",
        }
        assert item["company_id"] == member_company.id

    @pytest.mark.parametrize("term", ["клин", "CLN", "cln"])
    def test_search_matches_the_name_or_the_abbreviation(
        self, auth_client, member_company, term
    ):
        response = auth_client.get(
            f"/api/v1/companies/{member_company.id}/task-types/?search={term}"
        )

        assert [i["abbreviation"] for i in response.json()["items"]] == ["CLN"]

    def test_does_not_include_other_companies_types(
        self, auth_client, member_company, task_type_factory
    ):
        task_type_factory(name="Foreign")

        response = auth_client.get(f"/api/v1/companies/{member_company.id}/task-types/")

        assert "Foreign" not in [i["name"] for i in response.json()["items"]]

    def test_non_member_gets_a_404(
        self, auth_client, company, company_membership_factory
    ):
        company_membership_factory(company=company)  # some other user

        response = auth_client.get(f"/api/v1/companies/{company.id}/task-types/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company):
        response = client.get(f"/api/v1/companies/{company.id}/task-types/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestCreateTaskType:
    def test_creates_a_task_type(self, auth_client, auth_user, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-types/",
            {"name": "Анимация", "abbreviation": "ANM", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert (body["name"], body["abbreviation"], body["color"]) == (
            "Анимация",
            "ANM",
            "#112233",
        )
        assert body["created_by"]["id"] == auth_user.id
        assert TaskType.objects.filter(
            company=member_company, abbreviation="ANM"
        ).exists()

    @pytest.mark.parametrize("abbreviation", ["a", "anm", "TOOLONG", "A-B", "", "ЖЖ"])
    def test_rejects_an_invalid_abbreviation(
        self, auth_client, member_company, abbreviation
    ):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-types/",
            {"name": "X", "abbreviation": abbreviation, "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_an_invalid_color(self, auth_client, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-types/",
            {"name": "X", "abbreviation": "XX", "color": "red"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_duplicate_name_gets_a_409(self, auth_client, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-types/",
            {"name": "Клинап", "abbreviation": "XX", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.CONFLICT

    def test_duplicate_abbreviation_gets_a_409(self, auth_client, member_company):
        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-types/",
            {"name": "Другое", "abbreviation": "CLN", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.CONFLICT

    def test_the_same_abbreviation_is_fine_in_another_company(
        self, auth_client, member_company, company_factory
    ):
        company_factory()  # has its own CLN

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{member_company.id}/task-types/",
            {"name": "Анимация", "abbreviation": "ANM", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_non_member_gets_a_404(
        self, auth_client, company, company_membership_factory
    ):
        company_membership_factory(company=company)  # some other user

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/task-types/",
            {"name": "X", "abbreviation": "XX", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGetTaskType:
    def test_returns_the_type_for_a_company_member(
        self, auth_client, auth_user, task_type, company_membership_factory
    ):
        company_membership_factory(
            user=auth_user, company=task_type.company, role="admin"
        )

        response = auth_client.get(f"/api/v1/task-types/{task_type.id}/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["id"] == task_type.id

    def test_non_member_gets_a_404(
        self, auth_client, task_type, company_membership_factory
    ):
        company_membership_factory(company=task_type.company)  # some other user

        response = auth_client.get(f"/api/v1/task-types/{task_type.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, task_type):
        response = client.get(f"/api/v1/task-types/{task_type.id}/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestUpdateTaskType:
    @pytest.fixture
    def member_type(self, auth_user, task_type, company_membership_factory):
        company_membership_factory(
            user=auth_user, company=task_type.company, role="admin"
        )
        return task_type

    def test_updates_the_given_fields_only(self, auth_client, auth_user, member_type):
        response = _patch_json(
            auth_client, f"/api/v1/task-types/{member_type.id}/", {"name": "Renamed"}
        )

        assert response.status_code == HTTPStatus.OK
        member_type.refresh_from_db()
        assert member_type.name == "Renamed"
        assert member_type.abbreviation.startswith("T")
        assert member_type.updated_by == auth_user

    def test_changing_the_abbreviation_keeps_existing_task_codes(
        self, auth_client, member_type, task_factory
    ):
        task = task_factory(project__company=member_type.company, type=member_type)
        code = task.code

        response = _patch_json(
            auth_client,
            f"/api/v1/task-types/{member_type.id}/",
            {"abbreviation": "NEW"},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["abbreviation"] == "NEW"
        task.refresh_from_db()
        assert task.code == code

    def test_duplicate_name_gets_a_409(self, auth_client, member_type):
        response = _patch_json(
            auth_client, f"/api/v1/task-types/{member_type.id}/", {"name": "Клинап"}
        )

        assert response.status_code == HTTPStatus.CONFLICT

    def test_duplicate_abbreviation_gets_a_409(self, auth_client, member_type):
        response = _patch_json(
            auth_client,
            f"/api/v1/task-types/{member_type.id}/",
            {"abbreviation": "CLN"},
        )

        assert response.status_code == HTTPStatus.CONFLICT

    def test_keeping_its_own_name_is_not_a_conflict(self, auth_client, member_type):
        response = _patch_json(
            auth_client,
            f"/api/v1/task-types/{member_type.id}/",
            {"name": member_type.name},
        )

        assert response.status_code == HTTPStatus.OK

    @pytest.mark.parametrize("field", ["name", "abbreviation", "color"])
    def test_null_is_rejected(self, auth_client, member_type, field):
        response = _patch_json(
            auth_client, f"/api/v1/task-types/{member_type.id}/", {field: None}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_gets_a_404(
        self, auth_client, task_type, company_membership_factory
    ):
        company_membership_factory(company=task_type.company)  # some other user

        response = _patch_json(
            auth_client, f"/api/v1/task-types/{task_type.id}/", {"name": "X"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestDeleteTaskType:
    @pytest.fixture
    def member_type(self, auth_user, task_type, company_membership_factory):
        company_membership_factory(
            user=auth_user, company=task_type.company, role="admin"
        )
        return task_type

    def test_deletes_an_unused_type(self, auth_client, member_type):
        response = auth_client.delete(f"/api/v1/task-types/{member_type.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not TaskType.objects.filter(pk=member_type.pk).exists()

    def test_a_type_in_use_gets_a_409(self, auth_client, member_type, task_factory):
        task_factory(project__company=member_type.company, type=member_type)

        response = auth_client.delete(f"/api/v1/task-types/{member_type.id}/")

        assert response.status_code == HTTPStatus.CONFLICT
        assert TaskType.objects.filter(pk=member_type.pk).exists()

    def test_non_member_gets_a_404(
        self, auth_client, task_type, company_membership_factory
    ):
        company_membership_factory(company=task_type.company)  # some other user

        response = auth_client.delete(f"/api/v1/task-types/{task_type.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert TaskType.objects.filter(pk=task_type.pk).exists()


class TestTaskTypeWritesAreCompanyAdminOnly:
    def test_non_admin_member_can_list_but_not_create_update_or_delete(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        task_type_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")
        task_type = task_type_factory(company=company, name="Roto", abbreviation="RTO")

        listed = auth_client.get(f"/api/v1/companies/{company.id}/task-types/")
        created = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/task-types/",
            {"name": "Paint", "abbreviation": "PNT", "color": "#aabbcc"},
        )
        updated = _patch_json(
            auth_client, f"/api/v1/task-types/{task_type.id}/", {"name": "Renamed"}
        )
        deleted = auth_client.delete(f"/api/v1/task-types/{task_type.id}/")

        assert listed.status_code == HTTPStatus.OK
        assert created.status_code == HTTPStatus.FORBIDDEN
        assert updated.status_code == HTTPStatus.FORBIDDEN
        assert deleted.status_code == HTTPStatus.FORBIDDEN
        task_type.refresh_from_db()
        assert task_type.name == "Roto"
        assert not TaskType.objects.filter(company=company, name="Paint").exists()
