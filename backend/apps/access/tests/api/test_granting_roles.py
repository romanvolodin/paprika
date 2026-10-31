from http import HTTPStatus
import json

import pytest

from apps.access.defaults import get_default_role


pytestmark = pytest.mark.django_db


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _patch(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


def _new_person(email, role_id):
    return {
        "email": email,
        "first_name": "New",
        "last_name": "Person",
        "password": "temporary-passphrase-77",
        "role_id": role_id,
    }


class TestCompanyRoles:
    @pytest.fixture
    def producer_company(self, auth_user, company, company_membership_factory):
        company_membership_factory(user=auth_user, company=company, role="producer")
        return company

    def test_a_producer_cannot_make_someone_an_admin(
        self, auth_client, producer_company
    ):
        admin_id = get_default_role(producer_company, "admin").id

        response = _post(
            auth_client,
            f"/api/v1/companies/{producer_company.id}/members/",
            _new_person("boss@example.com", admin_id),
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_a_producer_can_hand_out_roles_with_no_more_rights_than_their_own(
        self, auth_client, producer_company
    ):
        coordinator_id = get_default_role(producer_company, "coordinator").id

        response = _post(
            auth_client,
            f"/api/v1/companies/{producer_company.id}/members/",
            _new_person("coord@example.com", coordinator_id),
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_a_producer_cannot_promote_themselves(
        self, auth_client, auth_user, producer_company
    ):
        admin_id = get_default_role(producer_company, "admin").id

        response = _patch(
            auth_client,
            f"/api/v1/companies/{producer_company.id}/members/{auth_user.id}/",
            {"role_id": admin_id},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_a_producer_cannot_demote_or_remove_an_admin(
        self, auth_client, producer_company, company_membership_factory
    ):
        admin = company_membership_factory(company=producer_company, role="admin")
        client_id = get_default_role(producer_company, "client").id

        demoted = _patch(
            auth_client,
            f"/api/v1/companies/{producer_company.id}/members/{admin.user_id}/",
            {"role_id": client_id},
        )
        removed = auth_client.delete(
            f"/api/v1/companies/{producer_company.id}/members/{admin.user_id}/"
        )

        assert demoted.status_code == HTTPStatus.FORBIDDEN
        assert removed.status_code == HTTPStatus.FORBIDDEN

    def test_an_admin_can_hand_out_any_role(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = _post(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _new_person("second@example.com", get_default_role(company, "admin").id),
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_a_role_that_sees_all_projects_needs_one_that_does_too(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        role_factory,
    ):
        manager = role_factory(
            company=company, name="Менеджер", permissions=["company.members"]
        )
        wide = role_factory(
            company=company,
            name="Широкий",
            permissions=[],
            sees_all_projects=True,
        )
        company_membership_factory(user=auth_user, company=company, role=manager)

        response = _post(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _new_person("wide@example.com", wide.id),
        )

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestProjectRoles:
    @pytest.fixture
    def coordinator_project(
        self,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project, role="coordinator")
        return project

    def test_a_coordinator_cannot_give_the_right_to_delete_the_project(
        self, auth_client, coordinator_project, company_membership_factory
    ):
        member = company_membership_factory(company=coordinator_project.company)
        producer_id = get_default_role(coordinator_project.company, "producer").id

        response = _post(
            auth_client,
            f"/api/v1/projects/{coordinator_project.id}/members/",
            {"user_id": member.user_id, "role_id": producer_id},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_a_coordinator_can_give_a_role_within_their_own_rights(
        self, auth_client, coordinator_project, company_membership_factory
    ):
        member = company_membership_factory(company=coordinator_project.company)
        executor_id = get_default_role(coordinator_project.company, "executor").id

        response = _post(
            auth_client,
            f"/api/v1/projects/{coordinator_project.id}/members/",
            {"user_id": member.user_id, "role_id": executor_id},
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_a_coordinator_cannot_remove_someone_with_more_rights(
        self,
        auth_client,
        coordinator_project,
        company_membership_factory,
        project_membership_factory,
    ):
        member = company_membership_factory(company=coordinator_project.company)
        project_membership_factory(
            user=member.user, project=coordinator_project, role="producer"
        )

        response = auth_client.delete(
            f"/api/v1/projects/{coordinator_project.id}/members/{member.user_id}/"
        )

        assert response.status_code == HTTPStatus.FORBIDDEN
