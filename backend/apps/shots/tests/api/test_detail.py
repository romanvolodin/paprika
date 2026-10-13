from http import HTTPStatus
import json

import pytest

from apps.shots.models import ShotGroup


pytestmark = pytest.mark.django_db


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


class TestGetShotGroup:
    def test_returns_the_shot_group_for_a_project_member(
        self, auth_client, auth_user, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory(name="Int. Office")
        project_membership_factory(user=auth_user, project=shot_group.project)

        response = auth_client.get(f"/api/v1/shot-groups/{shot_group.id}/")

        assert response.status_code == 200
        assert response.json()["name"] == "Int. Office"

    def test_non_member_gets_a_404_not_a_403(
        self, auth_client, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory()
        project_membership_factory(project=shot_group.project)  # some other user

        response = auth_client.get(f"/api/v1/shot-groups/{shot_group.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unknown_id_returns_404(self, auth_client):
        response = auth_client.get("/api/v1/shot-groups/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot_group):
        response = client.get(f"/api/v1/shot-groups/{shot_group.id}/")

        assert response.status_code == 401


class TestUpdateShotGroup:
    def test_renames_the_shot_group(
        self, auth_client, auth_user, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory(name="Old Name")
        project_membership_factory(user=auth_user, project=shot_group.project)

        response = _patch_json(
            auth_client,
            f"/api/v1/shot-groups/{shot_group.id}/",
            {"name": "New Name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_rejects_duplicate_name_within_the_same_project(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_group_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot_group_factory(project=project, name="Taken")
        shot_group = shot_group_factory(project=project, name="Mine")

        response = _patch_json(
            auth_client,
            f"/api/v1/shot-groups/{shot_group.id}/",
            {"name": "Taken"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_renaming_to_its_own_current_name_is_allowed(
        self, auth_client, auth_user, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory(name="Same Name")
        project_membership_factory(user=auth_user, project=shot_group.project)

        response = _patch_json(
            auth_client,
            f"/api/v1/shot-groups/{shot_group.id}/",
            {"name": "Same Name"},
        )

        assert response.status_code == 200

    def test_rejects_blank_name(
        self, auth_client, auth_user, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory()
        project_membership_factory(user=auth_user, project=shot_group.project)

        response = _patch_json(
            auth_client, f"/api/v1/shot-groups/{shot_group.id}/", {"name": ""}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_gets_404(
        self, auth_client, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory()
        project_membership_factory(project=shot_group.project)

        response = _patch_json(
            auth_client, f"/api/v1/shot-groups/{shot_group.id}/", {"name": "Hacked"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot_group):
        response = _patch_json(
            client, f"/api/v1/shot-groups/{shot_group.id}/", {"name": "Hacked"}
        )

        assert response.status_code == 401


class TestDeleteShotGroup:
    def test_deletes_the_shot_group(
        self, auth_client, auth_user, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory()
        project_membership_factory(user=auth_user, project=shot_group.project)

        response = auth_client.delete(f"/api/v1/shot-groups/{shot_group.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not ShotGroup.objects.filter(id=shot_group.id).exists()

    def test_non_member_gets_404(
        self, auth_client, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory()
        project_membership_factory(project=shot_group.project)

        response = auth_client.delete(f"/api/v1/shot-groups/{shot_group.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert ShotGroup.objects.filter(id=shot_group.id).exists()

    def test_requires_authentication(self, client, shot_group):
        response = client.delete(f"/api/v1/shot-groups/{shot_group.id}/")

        assert response.status_code == 401
        assert ShotGroup.objects.filter(id=shot_group.id).exists()


class TestClientRoleCannotChangeShotGroups:
    def test_client_cannot_rename_or_delete(
        self, auth_client, auth_user, shot_group, project_membership_factory
    ):
        project_membership_factory(
            user=auth_user, project=shot_group.project, role="client"
        )
        original_name = shot_group.name

        rename = _patch_json(
            auth_client, f"/api/v1/shot-groups/{shot_group.id}/", {"name": "Renamed"}
        )
        delete = auth_client.delete(f"/api/v1/shot-groups/{shot_group.id}/")

        assert rename.status_code == HTTPStatus.FORBIDDEN
        assert delete.status_code == HTTPStatus.FORBIDDEN
        shot_group.refresh_from_db()
        assert shot_group.name == original_name
