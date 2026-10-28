from http import HTTPStatus
import json

import pytest

from apps.access.defaults import get_default_role
from apps.access.models import Role
from apps.access.permissions import ALL_CODES


pytestmark = pytest.mark.django_db


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _patch(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


@pytest.fixture
def admin_company(auth_user, company, company_membership_factory):
    company_membership_factory(user=auth_user, company=company, role="admin")
    return company


class TestPermissionList:
    def test_returns_every_permission(self, auth_client):
        response = auth_client.get("/api/v1/permissions/")

        assert response.status_code == HTTPStatus.OK
        items = response.json()["items"]
        assert {item["code"] for item in items} == ALL_CODES
        assert {item["level"] for item in items} == {"company", "project"}

    def test_requires_authentication(self, client):
        assert client.get("/api/v1/permissions/").status_code == HTTPStatus.UNAUTHORIZED


class TestListRoles:
    def test_returns_the_companys_roles_with_member_counts(
        self, auth_client, admin_company
    ):
        response = auth_client.get(f"/api/v1/companies/{admin_company.id}/roles/")

        assert response.status_code == HTTPStatus.OK
        by_name = {role["name"]: role for role in response.json()["items"]}
        assert len(by_name) == 6
        assert by_name["Админ"]["company_members_count"] == 1
        assert by_name["Клиент"]["company_members_count"] == 0
        assert by_name["Админ"]["sees_all_projects"] is True

    def test_any_member_can_read_the_roles(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="client")

        response = auth_client.get(f"/api/v1/companies/{company.id}/roles/")

        assert response.status_code == HTTPStatus.OK

    def test_other_companys_roles_are_a_404(self, auth_client, company):
        response = auth_client.get(f"/api/v1/companies/{company.id}/roles/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCreateRole:
    def test_creates_a_role(self, auth_client, admin_company):
        response = _post(
            auth_client,
            f"/api/v1/companies/{admin_company.id}/roles/",
            {
                "name": "Старший исполнитель",
                "color": "#112233",
                "permissions": ["version.upload", "chat.write", "version.upload"],
                "sees_all_projects": False,
            },
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["permissions"] == ["chat.write", "version.upload"]
        assert Role.objects.filter(company=admin_company, name=body["name"]).exists()

    def test_an_unknown_permission_is_rejected(self, auth_client, admin_company):
        response = _post(
            auth_client,
            f"/api/v1/companies/{admin_company.id}/roles/",
            {"name": "X", "color": "#112233", "permissions": ["rule.the.world"]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_a_taken_name_is_a_409(self, auth_client, admin_company):
        response = _post(
            auth_client,
            f"/api/v1/companies/{admin_company.id}/roles/",
            {"name": "Клиент", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.CONFLICT

    def test_a_bad_color_is_rejected(self, auth_client, admin_company):
        response = _post(
            auth_client,
            f"/api/v1/companies/{admin_company.id}/roles/",
            {"name": "X", "color": "red"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_a_role_without_the_permission_gets_a_403(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")

        response = _post(
            auth_client,
            f"/api/v1/companies/{company.id}/roles/",
            {"name": "X", "color": "#112233"},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestUpdateRole:
    def test_updates_the_fields(self, auth_client, admin_company, role_factory):
        role = role_factory(company=admin_company, name="Old", permissions=[])

        response = _patch(
            auth_client,
            f"/api/v1/roles/{role.id}/",
            {"name": "New", "permissions": ["shot.create"], "sees_all_projects": True},
        )

        assert response.status_code == HTTPStatus.OK
        role.refresh_from_db()
        assert role.name == "New"
        assert role.permissions == ["shot.create"]
        assert role.sees_all_projects

    def test_null_is_rejected(self, auth_client, admin_company, role_factory):
        role = role_factory(company=admin_company)

        response = _patch(auth_client, f"/api/v1/roles/{role.id}/", {"name": None})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_a_taken_name_is_a_409(self, auth_client, admin_company, role_factory):
        role = role_factory(company=admin_company)

        response = _patch(auth_client, f"/api/v1/roles/{role.id}/", {"name": "Клиент"})

        assert response.status_code == HTTPStatus.CONFLICT

    def test_the_last_role_that_can_edit_roles_keeps_that_permission(
        self, auth_client, admin_company
    ):
        admin_role = get_default_role(admin_company, "admin")

        response = _patch(
            auth_client,
            f"/api/v1/roles/{admin_role.id}/",
            {"permissions": ["shot.create"]},
        )

        assert response.status_code == HTTPStatus.CONFLICT
        admin_role.refresh_from_db()
        assert "company.roles" in admin_role.permissions

    def test_a_role_without_the_permission_gets_a_403(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")
        role = get_default_role(company, "client")

        response = _patch(auth_client, f"/api/v1/roles/{role.id}/", {"name": "X"})

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_another_companys_role_is_a_404(self, auth_client, company):
        role = get_default_role(company, "client")

        response = _patch(auth_client, f"/api/v1/roles/{role.id}/", {"name": "X"})

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestDeleteRole:
    def test_deletes_an_unused_role(self, auth_client, admin_company, role_factory):
        role = role_factory(company=admin_company)

        response = auth_client.delete(f"/api/v1/roles/{role.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Role.objects.filter(pk=role.pk).exists()

    def test_a_role_in_use_is_a_409(
        self, auth_client, admin_company, company_membership_factory
    ):
        role = get_default_role(admin_company, "executor")
        company_membership_factory(company=admin_company, role=role)

        response = auth_client.delete(f"/api/v1/roles/{role.id}/")

        assert response.status_code == HTTPStatus.CONFLICT
        assert Role.objects.filter(pk=role.pk).exists()

    def test_a_role_used_in_a_project_is_a_409(
        self,
        auth_client,
        admin_company,
        project_factory,
        project_membership_factory,
    ):
        role = get_default_role(admin_company, "executor")
        project = project_factory(company=admin_company)
        project_membership_factory(project=project, role=role)

        response = auth_client.delete(f"/api/v1/roles/{role.id}/")

        assert response.status_code == HTTPStatus.CONFLICT

    def test_a_role_without_the_permission_gets_a_403(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")
        role = get_default_role(company, "client")

        response = auth_client.delete(f"/api/v1/roles/{role.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN
