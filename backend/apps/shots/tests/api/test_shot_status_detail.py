from http import HTTPStatus
import json

import pytest

from apps.shots.models import ShotStatus


pytestmark = pytest.mark.django_db


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


class TestGetShotStatus:
    def test_returns_the_status_for_a_company_member(
        self, auth_client, auth_user, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory(name="Blocked")
        company_membership_factory(user=auth_user, company=status.company, role="admin")

        response = auth_client.get(f"/api/v1/shot-statuses/{status.id}/")

        assert response.status_code == 200
        assert response.json()["name"] == "Blocked"

    def test_non_member_gets_a_404_not_a_403(
        self, auth_client, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory()
        company_membership_factory(company=status.company)  # some other user

        response = auth_client.get(f"/api/v1/shot-statuses/{status.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot_status):
        response = client.get(f"/api/v1/shot-statuses/{shot_status.id}/")

        assert response.status_code == 401


class TestUpdateShotStatus:
    def test_renames_and_recolors(
        self, auth_client, auth_user, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory(name="Old", color="#000000")
        company_membership_factory(user=auth_user, company=status.company, role="admin")

        response = _patch_json(
            auth_client,
            f"/api/v1/shot-statuses/{status.id}/",
            {"name": "New", "color": "#FFFFFF"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New"
        assert body["color"] == "#FFFFFF"

    def test_can_set_order_to_null(
        self, auth_client, auth_user, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory(order=3)
        company_membership_factory(user=auth_user, company=status.company, role="admin")

        response = _patch_json(
            auth_client, f"/api/v1/shot-statuses/{status.id}/", {"order": None}
        )

        assert response.status_code == 200
        assert response.json()["order"] is None

    def test_setting_is_default_unsets_the_previous_default(
        self,
        auth_client,
        auth_user,
        company,
        shot_status_factory,
        company_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        old_default = company.shot_statuses.get(is_default=True)
        other = shot_status_factory(company=company, name="Other", is_default=False)

        response = _patch_json(
            auth_client,
            f"/api/v1/shot-statuses/{other.id}/",
            {"is_default": True},
        )

        assert response.status_code == 200
        old_default.refresh_from_db()
        assert old_default.is_default is False
        assert ShotStatus.objects.filter(company=company, is_default=True).count() == 1

    def test_rejects_duplicate_name_within_the_same_company(
        self,
        auth_client,
        auth_user,
        company,
        shot_status_factory,
        company_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        shot_status_factory(company=company, name="Taken")
        status = shot_status_factory(company=company, name="Mine")

        response = _patch_json(
            auth_client, f"/api/v1/shot-statuses/{status.id}/", {"name": "Taken"}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_renaming_to_its_own_current_name_is_allowed(
        self, auth_client, auth_user, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory(name="Same Name")
        company_membership_factory(user=auth_user, company=status.company, role="admin")

        response = _patch_json(
            auth_client,
            f"/api/v1/shot-statuses/{status.id}/",
            {"name": "Same Name"},
        )

        assert response.status_code == 200

    def test_rejects_an_invalid_color(
        self, auth_client, auth_user, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory()
        company_membership_factory(user=auth_user, company=status.company, role="admin")

        response = _patch_json(
            auth_client,
            f"/api/v1/shot-statuses/{status.id}/",
            {"color": "not-a-color"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_gets_404(
        self, auth_client, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory()
        company_membership_factory(company=status.company)

        response = _patch_json(
            auth_client, f"/api/v1/shot-statuses/{status.id}/", {"name": "Hacked"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot_status):
        response = _patch_json(
            client, f"/api/v1/shot-statuses/{shot_status.id}/", {"name": "Hacked"}
        )

        assert response.status_code == 401


class TestDeleteShotStatus:
    def test_deletes_an_unused_status(
        self, auth_client, auth_user, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory()
        company_membership_factory(user=auth_user, company=status.company, role="admin")

        response = auth_client.delete(f"/api/v1/shot-statuses/{status.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not ShotStatus.objects.filter(id=status.id).exists()

    def test_deleting_the_default_status_is_allowed_when_unused(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        default_status = company.shot_statuses.get(is_default=True)

        response = auth_client.delete(f"/api/v1/shot-statuses/{default_status.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not company.shot_statuses.filter(is_default=True).exists()

    def test_rejects_deleting_a_status_still_used_by_a_shot(
        self,
        auth_client,
        auth_user,
        company,
        project_factory,
        project_membership_factory,
        shot_factory,
        company_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        status = company.shot_statuses.get(is_default=True)
        shot_factory(project=project, status=status)

        response = auth_client.delete(f"/api/v1/shot-statuses/{status.id}/")

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert ShotStatus.objects.filter(id=status.id).exists()

    def test_non_member_gets_404(
        self, auth_client, shot_status_factory, company_membership_factory
    ):
        status = shot_status_factory()
        company_membership_factory(company=status.company)

        response = auth_client.delete(f"/api/v1/shot-statuses/{status.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert ShotStatus.objects.filter(id=status.id).exists()

    def test_requires_authentication(self, client, shot_status):
        response = client.delete(f"/api/v1/shot-statuses/{shot_status.id}/")

        assert response.status_code == 401
        assert ShotStatus.objects.filter(id=shot_status.id).exists()


class TestShotStatusEditAndDeleteAreCompanyAdminOnly:
    def test_non_admin_member_cannot_update_or_delete(
        self, auth_client, auth_user, shot_status, company_membership_factory
    ):
        company_membership_factory(
            user=auth_user, company=shot_status.company, role="coordinator"
        )
        original_name = shot_status.name

        update = _patch_json(
            auth_client, f"/api/v1/shot-statuses/{shot_status.id}/", {"name": "Renamed"}
        )
        delete = auth_client.delete(f"/api/v1/shot-statuses/{shot_status.id}/")

        assert update.status_code == HTTPStatus.FORBIDDEN
        assert delete.status_code == HTTPStatus.FORBIDDEN
        shot_status.refresh_from_db()
        assert shot_status.name == original_name
