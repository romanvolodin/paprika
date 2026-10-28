from http import HTTPStatus

import pytest

from apps.projects.models import Project, ProjectMembership


pytestmark = pytest.mark.django_db


class TestGetProject:
    def test_returns_the_project_for_a_member(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory(name="Mine")
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(f"/api/v1/projects/{project.id}/")

        assert response.status_code == 200
        assert response.json()["name"] == "Mine"

    def test_created_by_is_null_when_unset(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory(created_by=None, updated_by=None)
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(f"/api/v1/projects/{project.id}/")

        body = response.json()
        assert body["created_by"] is None
        assert body["updated_by"] is None

    def test_created_by_reflects_the_user_who_created_the_project(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory(created_by=auth_user, updated_by=auth_user)
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(f"/api/v1/projects/{project.id}/")

        body = response.json()
        assert body["created_by"]["id"] == auth_user.id
        assert body["updated_by"]["id"] == auth_user.id

    def test_non_member_gets_a_404_not_a_403(
        self, auth_client, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(project=project)  # some other user

        response = auth_client.get(f"/api/v1/projects/{project.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_company_member_who_is_not_a_project_member_gets_404(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="executor")
        project = project_factory(company=company)

        response = auth_client.get(f"/api/v1/projects/{project.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unknown_id_returns_404(self, auth_client):
        response = auth_client.get("/api/v1/projects/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project_factory):
        project = project_factory()

        response = client.get(f"/api/v1/projects/{project.id}/")

        assert response.status_code == 401


class TestUpdateProject:
    def test_updates_the_name(
        self,
        auth_client,
        auth_user,
        multipart_patch,
        project_factory,
        project_membership_factory,
    ):
        project = project_factory(name="Old Name")
        project_membership_factory(user=auth_user, project=project)

        response = multipart_patch(
            auth_client, f"/api/v1/projects/{project.id}/", {"name": "New Name"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_code_cannot_be_changed(
        self,
        auth_client,
        auth_user,
        multipart_patch,
        project_factory,
        project_membership_factory,
    ):
        # `code` is intentionally absent from the update schema - passing
        # it is simply ignored, not an error, since extra fields aren't
        # rejected by default.
        project = project_factory(code="PRJ")
        project_membership_factory(user=auth_user, project=project)

        response = multipart_patch(
            auth_client,
            f"/api/v1/projects/{project.id}/",
            {"code": "HACKED"},
        )

        assert response.status_code == 200
        assert response.json()["code"] == "PRJ"

    def test_can_archive_a_project(
        self,
        auth_client,
        auth_user,
        multipart_patch,
        project_factory,
        project_membership_factory,
    ):
        project = project_factory(is_active=True)
        project_membership_factory(user=auth_user, project=project)

        response = multipart_patch(
            auth_client, f"/api/v1/projects/{project.id}/", {"is_active": "false"}
        )

        assert response.json()["is_active"] is False

    def test_rejects_deadline_before_start_date(
        self,
        auth_client,
        auth_user,
        multipart_patch,
        project_factory,
        project_membership_factory,
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)

        response = multipart_patch(
            auth_client,
            f"/api/v1/projects/{project.id}/",
            {"start_date": "2026-06-01", "deadline": "2026-01-01"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_empty_body_changes_nothing(
        self,
        auth_client,
        auth_user,
        multipart_patch,
        project_factory,
        project_membership_factory,
    ):
        project = project_factory(name="Untouched")
        project_membership_factory(user=auth_user, project=project)

        response = multipart_patch(auth_client, f"/api/v1/projects/{project.id}/", {})

        assert response.status_code == 200
        assert response.json()["name"] == "Untouched"

    def test_non_member_gets_404(
        self,
        auth_client,
        multipart_patch,
        project_factory,
        project_membership_factory,
    ):
        project = project_factory()
        project_membership_factory(project=project)

        response = multipart_patch(
            auth_client, f"/api/v1/projects/{project.id}/", {"name": "Hacked"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, multipart_patch, project_factory):
        project = project_factory()

        response = multipart_patch(
            client, f"/api/v1/projects/{project.id}/", {"name": "Hacked"}
        )

        assert response.status_code == 401


class TestDeleteProject:
    @pytest.mark.parametrize("role", ["admin", "producer"])
    def test_admin_and_producer_can_delete_the_project(
        self, auth_client, auth_user, project_factory, project_membership_factory, role
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project, role=role)

        response = auth_client.delete(f"/api/v1/projects/{project.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Project.objects.filter(id=project.id).exists()

    @pytest.mark.parametrize(
        "role",
        [
            "coordinator",
            "executor",
            "freelancer",
            "client",
        ],
    )
    def test_other_roles_get_403(
        self, auth_client, auth_user, project_factory, project_membership_factory, role
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project, role=role)

        response = auth_client.delete(f"/api/v1/projects/{project.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Project.objects.filter(id=project.id).exists()

    def test_deleting_a_project_cascades_its_memberships(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory()
        membership = project_membership_factory(
            user=auth_user, project=project, role="admin"
        )

        auth_client.delete(f"/api/v1/projects/{project.id}/")

        assert not ProjectMembership.objects.filter(id=membership.id).exists()

    def test_non_member_gets_404(
        self, auth_client, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(project=project)

        response = auth_client.delete(f"/api/v1/projects/{project.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Project.objects.filter(id=project.id).exists()

    def test_requires_authentication(self, client, project_factory):
        project = project_factory()

        response = client.delete(f"/api/v1/projects/{project.id}/")

        assert response.status_code == 401
        assert Project.objects.filter(id=project.id).exists()
