from http import HTTPStatus
import json

import pytest

from apps.shots.models import Shot


pytestmark = pytest.mark.django_db


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


class TestGetShot:
    def test_returns_the_shot_for_a_project_member(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        shot = shot_factory(name="0010")
        project_membership_factory(user=auth_user, project=shot.project)

        response = auth_client.get(f"/api/v1/shots/{shot.id}/")

        assert response.status_code == 200
        assert response.json()["name"] == "0010"

    def test_non_member_gets_a_404_not_a_403(
        self, auth_client, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(project=shot.project)  # some other user

        response = auth_client.get(f"/api/v1/shots/{shot.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unknown_id_returns_404(self, auth_client):
        response = auth_client.get("/api/v1/shots/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot):
        response = client.get(f"/api/v1/shots/{shot.id}/")

        assert response.status_code == 401


class TestUpdateShot:
    def test_updates_rec_timecode_and_duration(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(user=auth_user, project=shot.project)

        response = _patch_json(
            auth_client,
            f"/api/v1/shots/{shot.id}/",
            {"rec_timecode": 100, "duration": 24},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["rec_timecode"] == 100
        assert body["duration"] == 24

    def test_can_clear_rec_timecode_back_to_null(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        shot = shot_factory(rec_timecode=100)
        project_membership_factory(user=auth_user, project=shot.project)

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"rec_timecode": None}
        )

        assert response.status_code == 200
        assert response.json()["rec_timecode"] is None

    def test_name_cannot_be_changed(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        # `name` is intentionally absent from the update schema - passing
        # it is simply ignored, not an error.
        shot = shot_factory(name="0010")
        project_membership_factory(user=auth_user, project=shot.project)

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"name": "HACKED"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "0010"

    def test_replaces_group_membership_wholesale(
        self,
        auth_client,
        auth_user,
        shot_factory,
        shot_group_factory,
        project_membership_factory,
        project,
    ):
        project_membership_factory(user=auth_user, project=project)
        group_a = shot_group_factory(project=project)
        group_b = shot_group_factory(project=project)
        shot = shot_factory(project=project, groups=[group_a])

        response = _patch_json(
            auth_client,
            f"/api/v1/shots/{shot.id}/",
            {"group_ids": [group_b.id]},
        )

        assert response.status_code == 200
        shot.refresh_from_db()
        assert set(shot.groups.all()) == {group_b}

    def test_empty_group_ids_clears_all_groups(
        self,
        auth_client,
        auth_user,
        shot_factory,
        shot_group_factory,
        project_membership_factory,
        project,
    ):
        project_membership_factory(user=auth_user, project=project)
        group = shot_group_factory(project=project)
        shot = shot_factory(project=project, groups=[group])

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"group_ids": []}
        )

        assert response.status_code == 200
        assert response.json()["group_ids"] == []

    def test_omitting_group_ids_leaves_groups_untouched(
        self,
        auth_client,
        auth_user,
        shot_factory,
        shot_group_factory,
        project_membership_factory,
        project,
    ):
        project_membership_factory(user=auth_user, project=project)
        group = shot_group_factory(project=project)
        shot = shot_factory(project=project, groups=[group])

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"rec_timecode": 10}
        )

        assert response.status_code == 200
        assert response.json()["group_ids"] == [group.id]

    def test_switches_to_a_different_status_in_the_same_company(
        self,
        auth_client,
        auth_user,
        shot_factory,
        shot_status_factory,
        project_membership_factory,
        project,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot = shot_factory(project=project)
        new_status = shot_status_factory(company=project.company, name="Blocked")

        response = _patch_json(
            auth_client,
            f"/api/v1/shots/{shot.id}/",
            {"status_id": new_status.id},
        )

        assert response.status_code == 200
        assert response.json()["status_id"] == new_status.id

    def test_rejects_null_status_id(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(user=auth_user, project=shot.project)

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"status_id": None}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        shot.refresh_from_db()
        assert shot.status is not None

    def test_rejects_a_status_from_a_different_company(
        self,
        auth_client,
        auth_user,
        shot_factory,
        shot_status_factory,
        project_membership_factory,
        project,
        company_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot = shot_factory(project=project)
        foreign_status = shot_status_factory(company=company_factory())

        response = _patch_json(
            auth_client,
            f"/api/v1/shots/{shot.id}/",
            {"status_id": foreign_status.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_omitting_status_id_leaves_status_untouched(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(user=auth_user, project=shot.project)
        original_status_id = shot.status_id

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"rec_timecode": 5}
        )

        assert response.status_code == 200
        assert response.json()["status_id"] == original_status_id

    def test_rejects_a_group_from_a_different_project(
        self,
        auth_client,
        auth_user,
        shot_factory,
        shot_group_factory,
        project_membership_factory,
        project_factory,
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)
        shot = shot_factory(project=project)
        other_project = project_factory()
        foreign_group = shot_group_factory(project=other_project)

        response = _patch_json(
            auth_client,
            f"/api/v1/shots/{shot.id}/",
            {"group_ids": [foreign_group.id]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_negative_rec_timecode(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(user=auth_user, project=shot.project)

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"rec_timecode": -1}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_gets_404(
        self, auth_client, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(project=shot.project)

        response = _patch_json(
            auth_client, f"/api/v1/shots/{shot.id}/", {"rec_timecode": 1}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot):
        response = _patch_json(client, f"/api/v1/shots/{shot.id}/", {"rec_timecode": 1})

        assert response.status_code == 401


class TestDeleteShot:
    def test_deletes_the_shot(
        self, auth_client, auth_user, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(user=auth_user, project=shot.project)

        response = auth_client.delete(f"/api/v1/shots/{shot.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Shot.objects.filter(id=shot.id).exists()

    def test_non_member_gets_404(
        self, auth_client, shot_factory, project_membership_factory
    ):
        shot = shot_factory()
        project_membership_factory(project=shot.project)

        response = auth_client.delete(f"/api/v1/shots/{shot.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Shot.objects.filter(id=shot.id).exists()

    def test_requires_authentication(self, client, shot):
        response = client.delete(f"/api/v1/shots/{shot.id}/")

        assert response.status_code == 401
        assert Shot.objects.filter(id=shot.id).exists()


class TestClientRoleIsReadOnly:
    def test_client_can_read_but_not_update_or_delete(
        self, auth_client, auth_user, shot, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=shot.project, role="client")

        read = auth_client.get(f"/api/v1/shots/{shot.id}/")
        update = _patch_json(auth_client, f"/api/v1/shots/{shot.id}/", {"duration": 24})
        delete = auth_client.delete(f"/api/v1/shots/{shot.id}/")

        assert read.status_code == HTTPStatus.OK
        assert update.status_code == HTTPStatus.FORBIDDEN
        assert delete.status_code == HTTPStatus.FORBIDDEN
        shot.refresh_from_db()
        assert shot.duration != 24
        assert Shot.objects.filter(id=shot.id).exists()
