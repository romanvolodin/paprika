from http import HTTPStatus

import pytest

from apps.versions.models import Version


pytestmark = pytest.mark.django_db


class TestGetVersion:
    def test_returns_the_version_for_a_project_member(
        self, auth_client, auth_user, version, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=version.project)

        response = auth_client.get(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["name"] == version.name

    def test_non_member_gets_a_404_not_a_403(
        self, auth_client, version, project_membership_factory
    ):
        project_membership_factory(project=version.project)  # some other user

        response = auth_client.get(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unknown_id_returns_404(self, auth_client):
        response = auth_client.get("/api/v1/versions/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, version):
        response = client.get(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestDeleteVersion:
    def test_deletes_the_version_and_its_files(
        self,
        auth_client,
        auth_user,
        version,
        project_membership_factory,
        django_capture_on_commit_callbacks,
    ):
        project_membership_factory(user=auth_user, project=version.project)
        storage = version.source.storage
        names = [version.source.name, version.thumb.name]

        with django_capture_on_commit_callbacks(execute=True):
            response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Version.objects.filter(pk=version.pk).exists()
        assert not any(storage.exists(name) for name in names)

    def test_frees_the_name_for_a_new_upload(
        self,
        auth_client,
        auth_user,
        version_factory,
        project_membership_factory,
    ):
        version = version_factory(name="PRJ_0010_v01")
        project_membership_factory(user=auth_user, project=version.project)
        auth_client.delete(f"/api/v1/versions/{version.id}/")

        # No other version with that name remains in the project.
        assert not Version.objects.filter(
            project=version.project, name="PRJ_0010_v01"
        ).exists()

    @pytest.mark.parametrize("role", ["executor", "freelancer"])
    def test_deletes_their_own_version_with_the_own_permission(
        self, auth_client, auth_user, version_factory, project_membership_factory, role
    ):
        version = version_factory(created_by=auth_user)
        project_membership_factory(user=auth_user, project=version.project, role=role)

        response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Version.objects.filter(pk=version.pk).exists()

    @pytest.mark.parametrize("role", ["executor", "freelancer"])
    def test_cannot_delete_someone_elses_version_with_only_the_own_permission(
        self, auth_client, auth_user, version, project_membership_factory, role
    ):
        project_membership_factory(user=auth_user, project=version.project, role=role)

        response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Version.objects.filter(pk=version.pk).exists()

    def test_a_role_without_either_permission_cannot_delete_its_own_version(
        self, auth_client, auth_user, version_factory, project_membership_factory
    ):
        version = version_factory(created_by=auth_user)
        project_membership_factory(
            user=auth_user, project=version.project, role="client"
        )

        response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_read_only_client_gets_a_403(
        self, auth_client, auth_user, version, project_membership_factory
    ):
        project_membership_factory(
            user=auth_user, project=version.project, role="client"
        )

        response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Version.objects.filter(pk=version.pk).exists()

    def test_non_member_gets_a_404(
        self, auth_client, version, project_membership_factory
    ):
        project_membership_factory(project=version.project)  # some other user

        response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Version.objects.filter(pk=version.pk).exists()

    def test_requires_authentication(self, client, version):
        response = client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestVersionsCannotBeEdited:
    @pytest.mark.parametrize("method", ["patch", "put"])
    def test_there_is_no_update_endpoint(
        self, auth_client, auth_user, version, project_membership_factory, method
    ):
        project_membership_factory(user=auth_user, project=version.project)

        response = getattr(auth_client, method)(
            f"/api/v1/versions/{version.id}/",
            data='{"name": "other"}',
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
