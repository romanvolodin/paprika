from http import HTTPStatus
import json

import pytest

from apps.shots.models import ShotStatus
from apps.shots.signals import DEFAULT_SHOT_STATUSES


pytestmark = pytest.mark.django_db


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


class TestListShotStatuses:
    def test_returns_the_seeded_defaults_for_a_member(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = auth_client.get(f"/api/v1/companies/{company.id}/shot-statuses/")

        assert response.status_code == 200
        names = {item["name"] for item in response.json()["items"]}
        assert names == {name for name, _color, _order in DEFAULT_SHOT_STATUSES}

    def test_search_filters_by_name(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = auth_client.get(
            f"/api/v1/companies/{company.id}/shot-statuses/?search=паузе"
        )

        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["name"] == "На паузе"

    def test_response_is_not_paginated(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = auth_client.get(f"/api/v1/companies/{company.id}/shot-statuses/")

        body = response.json()
        assert "items" in body
        assert "page" not in body
        assert "total" not in body

    def test_non_member_of_company_gets_404(
        self, auth_client, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(company=company)  # some other user

        response = auth_client.get(f"/api/v1/companies/{company.id}/shot-statuses/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company):
        response = client.get(f"/api/v1/companies/{company.id}/shot-statuses/")

        assert response.status_code == 401


class TestCreateShotStatus:
    def test_creates_a_shot_status(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": "Blocked", "color": "#AA00AA"},
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["name"] == "Blocked"
        assert body["color"] == "#AA00AA"
        assert body["order"] is None
        assert body["is_default"] is False

    def test_creates_with_an_explicit_order(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": "Blocked", "color": "#AA00AA", "order": 2},
        )

        assert response.json()["order"] == 2

    def test_setting_is_default_unsets_the_previous_default(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        old_default_name = DEFAULT_SHOT_STATUSES[0][0]

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": "New Default", "color": "#AA00AA", "is_default": True},
        )

        assert response.json()["is_default"] is True
        old_default = ShotStatus.objects.get(company=company, name=old_default_name)
        assert old_default.is_default is False
        assert ShotStatus.objects.filter(company=company, is_default=True).count() == 1

    def test_rejects_duplicate_name_within_company(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": DEFAULT_SHOT_STATUSES[0][0], "color": "#AA00AA"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_an_invalid_color(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": "Blocked", "color": "not-a-color"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_blank_name(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": "", "color": "#AA00AA"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_of_company_gets_404(
        self, auth_client, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(company=company)  # some other user

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": "Blocked", "color": "#AA00AA"},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company):
        response = _post_json(
            client,
            f"/api/v1/companies/{company.id}/shot-statuses/",
            {"name": "Blocked", "color": "#AA00AA"},
        )

        assert response.status_code == 401


class TestShotStatusWritesAreCompanyAdminOnly:
    def test_non_admin_member_can_list_but_not_create(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="producer")

        listed = auth_client.get(f"/api/v1/companies/{company.id}/shot-statuses/")
        created = auth_client.post(
            f"/api/v1/companies/{company.id}/shot-statuses/",
            data=json.dumps({"name": "Review", "color": "#aabbcc"}),
            content_type="application/json",
        )

        assert listed.status_code == HTTPStatus.OK
        assert created.status_code == HTTPStatus.FORBIDDEN
        assert not ShotStatus.objects.filter(company=company, name="Review").exists()
