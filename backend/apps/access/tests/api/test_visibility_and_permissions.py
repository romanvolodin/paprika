from http import HTTPStatus
import json

import pytest

from apps.access.permissions import COMPANY_CODES, PROJECT_CODES


pytestmark = pytest.mark.django_db


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _patch(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


class TestProjectsOfTheWholeCompany:
    @pytest.mark.parametrize("role", ["admin", "producer"])
    def test_a_role_that_sees_all_projects_sees_them_without_membership(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        role,
    ):
        company_membership_factory(user=auth_user, company=company, role=role)
        project = project_factory(company=company)

        listed = auth_client.get(f"/api/v1/companies/{company.id}/projects/")
        detail = auth_client.get(f"/api/v1/projects/{project.id}/")

        assert [p["id"] for p in listed.json()["items"]] == [project.id]
        assert detail.status_code == HTTPStatus.OK

    @pytest.mark.parametrize(
        "role", ["coordinator", "executor", "freelancer", "client"]
    )
    def test_other_roles_need_to_be_added_to_the_project(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        role,
    ):
        company_membership_factory(user=auth_user, company=company, role=role)
        project = project_factory(company=company)

        listed = auth_client.get(f"/api/v1/companies/{company.id}/projects/")
        detail = auth_client.get(f"/api/v1/projects/{project.id}/")

        assert listed.json()["total"] == 0
        assert detail.status_code == HTTPStatus.NOT_FOUND

    def test_it_does_not_reach_into_another_company(
        self,
        auth_client,
        auth_user,
        company,
        company_factory,
        company_membership_factory,
        project_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        foreign_project = project_factory(company=company_factory())

        response = auth_client.get(f"/api/v1/projects/{foreign_project.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_the_role_acts_inside_a_project_it_was_not_added_to(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        shot_status_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")
        project = project_factory(company=company)

        response = _post(
            auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": "SH010"}
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_shots_of_a_project_it_was_not_added_to_are_visible(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        shot_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        project = project_factory(company=company)
        shot = shot_factory(project=project)

        response = auth_client.get(f"/api/v1/shots/{shot.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_membership_in_the_project_wins_over_the_company_role(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project, role="client")

        response = auth_client.get(f"/api/v1/projects/{project.id}/")

        assert response.json()["my_permissions"] == ["chat.write"]


class TestMyPermissions:
    def test_a_company_reports_the_company_permissions_of_the_user(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")

        detail = auth_client.get(f"/api/v1/companies/{company.id}/")
        listed = auth_client.get("/api/v1/companies/")

        permissions = detail.json()["my_permissions"]
        assert "company.members" in permissions
        assert "company.delete" not in permissions
        assert set(permissions) <= COMPANY_CODES
        assert listed.json()["items"][0]["my_permissions"] == permissions

    def test_a_project_reports_the_project_permissions_of_the_user(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="executor")
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project, role="executor")

        detail = auth_client.get(f"/api/v1/projects/{project.id}/")
        listed = auth_client.get(f"/api/v1/companies/{company.id}/projects/")

        expected = [
            "chat.write",
            "feed.view",
            "task.update_own",
            "version.delete_own",
            "version.upload",
        ]
        assert detail.json()["my_permissions"] == expected
        assert listed.json()["items"][0]["my_permissions"] == expected


class TestWhatTheRoleDoesNotAllow:
    @pytest.fixture
    def executor_company(self, auth_user, company, company_membership_factory):
        company_membership_factory(user=auth_user, company=company, role="executor")
        return company

    def test_cannot_change_or_delete_the_company(self, auth_client, executor_company):
        updated = _patch(
            auth_client, f"/api/v1/companies/{executor_company.id}/", {"name": "Mine"}
        )
        deleted = auth_client.delete(f"/api/v1/companies/{executor_company.id}/")

        assert updated.status_code == HTTPStatus.FORBIDDEN
        assert deleted.status_code == HTTPStatus.FORBIDDEN
        executor_company.refresh_from_db()
        assert executor_company.name != "Mine"

    def test_can_still_read_the_company(self, auth_client, executor_company):
        response = auth_client.get(f"/api/v1/companies/{executor_company.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_cannot_create_projects(self, auth_client, executor_company):
        response = auth_client.post(
            f"/api/v1/companies/{executor_company.id}/projects/",
            {"name": "New", "code": "NEW"},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_cannot_change_or_delete_a_project_it_belongs_to(
        self,
        auth_client,
        auth_user,
        executor_company,
        project_factory,
        project_membership_factory,
        multipart_patch,
    ):
        project = project_factory(company=executor_company)
        project_membership_factory(user=auth_user, project=project, role="executor")

        updated = multipart_patch(
            auth_client, f"/api/v1/projects/{project.id}/", {"name": "Renamed"}
        )
        deleted = auth_client.delete(f"/api/v1/projects/{project.id}/")

        assert updated.status_code == HTTPStatus.FORBIDDEN
        assert deleted.status_code == HTTPStatus.FORBIDDEN

    def test_the_producer_cannot_delete_the_company(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")

        response = auth_client.delete(f"/api/v1/companies/{company.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_the_admin_can_delete_the_company(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = auth_client.delete(f"/api/v1/companies/{company.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT


class TestSuperuser:
    @pytest.fixture
    def superuser(self, auth_user):
        auth_user.is_superuser = True
        auth_user.save(update_fields=["is_superuser"])
        return auth_user

    def test_sees_every_company_and_project_without_membership(
        self, superuser, auth_client, company, project_factory
    ):
        project = project_factory(company=company)

        companies = auth_client.get("/api/v1/companies/")
        listed = auth_client.get(f"/api/v1/companies/{company.id}/projects/")
        detail = auth_client.get(f"/api/v1/projects/{project.id}/")

        assert company.id in [c["id"] for c in companies.json()["items"]]
        assert [p["id"] for p in listed.json()["items"]] == [project.id]
        assert detail.status_code == HTTPStatus.OK

    def test_has_every_permission(
        self, superuser, auth_client, company, project_factory
    ):
        project = project_factory(company=company)

        company_body = auth_client.get(f"/api/v1/companies/{company.id}/").json()
        project_body = auth_client.get(f"/api/v1/projects/{project.id}/").json()

        assert set(company_body["my_permissions"]) == COMPANY_CODES
        assert set(project_body["my_permissions"]) == PROJECT_CODES

    def test_can_change_and_delete_a_company_it_does_not_belong_to(
        self, superuser, auth_client, company
    ):
        updated = _patch(auth_client, f"/api/v1/companies/{company.id}/", {"name": "X"})
        deleted = auth_client.delete(f"/api/v1/companies/{company.id}/")

        assert updated.status_code == HTTPStatus.OK
        assert deleted.status_code == HTTPStatus.NO_CONTENT

    def test_creating_a_project_without_company_membership_works(
        self, superuser, auth_client, company
    ):
        response = auth_client.post(
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "New", "code": "NEW"},
        )

        assert response.status_code == HTTPStatus.CREATED


class TestChangingOwnTaskStatus:
    @pytest.fixture
    def setup(
        self,
        auth_user,
        shot_task_factory,
        project_membership_factory,
        task_status_factory,
    ):
        shot_task = shot_task_factory(assignee=None)
        project = shot_task.shot.project
        project_membership_factory(user=auth_user, project=project, role="executor")
        return shot_task, project, task_status_factory(company=project.company)

    def test_the_assignee_can_change_just_the_status(
        self, auth_client, auth_user, setup
    ):
        shot_task, project, status = setup
        shot_task.assignee = auth_user
        shot_task.save()

        response = _patch(
            auth_client, f"/api/v1/shot-tasks/{shot_task.id}/", {"status_id": status.id}
        )

        assert response.status_code == HTTPStatus.OK
        shot_task.refresh_from_db()
        assert shot_task.status_id == status.id

    def test_the_assignee_cannot_change_anything_else(
        self, auth_client, auth_user, setup
    ):
        shot_task, project, status = setup
        shot_task.assignee = auth_user
        shot_task.save()

        response = _patch(
            auth_client,
            f"/api/v1/shot-tasks/{shot_task.id}/",
            {"status_id": status.id, "estimated_hours": 5},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_someone_else_cannot_change_the_status(self, auth_client, setup):
        shot_task, project, status = setup

        response = _patch(
            auth_client, f"/api/v1/shot-tasks/{shot_task.id}/", {"status_id": status.id}
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_a_role_with_task_edit_changes_any_task(
        self, auth_client, auth_user, setup, project_membership_factory
    ):
        shot_task, project, status = setup
        project.memberships.filter(user=auth_user).delete()
        project_membership_factory(user=auth_user, project=project, role="coordinator")

        response = _patch(
            auth_client, f"/api/v1/shot-tasks/{shot_task.id}/", {"status_id": status.id}
        )

        assert response.status_code == HTTPStatus.OK
