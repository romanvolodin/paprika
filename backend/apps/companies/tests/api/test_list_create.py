from http import HTTPStatus
import json

import pytest

from apps.companies.models import Company, CompanyMembership


pytestmark = pytest.mark.django_db


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


class TestListCompanies:
    def test_returns_only_companies_the_user_belongs_to(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        my_company = company_factory(name="Mine")
        company_membership_factory(user=auth_user, company=my_company)
        other_company = company_factory(name="Someone Else's")
        company_membership_factory(company=other_company)  # different user

        response = auth_client.get("/api/v1/companies/")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Mine"

    def test_search_filters_by_name(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        findable = company_factory(name="Findable Studio")
        company_membership_factory(user=auth_user, company=findable)
        other = company_factory(name="Other Studio")
        company_membership_factory(user=auth_user, company=other)

        response = auth_client.get("/api/v1/companies/?search=findable")

        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Findable Studio"

    def test_pagination_page_size_is_respected(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        for _ in range(5):
            company = company_factory()
            company_membership_factory(user=auth_user, company=company)

        response = auth_client.get("/api/v1/companies/?page_size=2")

        body = response.json()
        assert len(body["items"]) == 2
        assert body["page_size"] == 2

    def test_page_size_over_max_is_rejected(self, auth_client):
        response = auth_client.get("/api/v1/companies/?page_size=1000")

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_requires_authentication(self, client):
        response = client.get("/api/v1/companies/")

        assert response.status_code == 401


class TestCreateCompany:
    def test_creates_a_company(self, auth_client):
        response = _post_json(
            auth_client, "/api/v1/companies/", {"name": "Acme Studio"}
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["name"] == "Acme Studio"
        assert body["slug"] == "acme-studio"
        assert Company.objects.filter(name="Acme Studio").exists()

    def test_creator_becomes_an_admin_member(self, auth_client, auth_user):
        response = _post_json(
            auth_client, "/api/v1/companies/", {"name": "Acme Studio"}
        )

        company = Company.objects.get(id=response.json()["id"])
        membership = CompanyMembership.objects.get(company=company, user=auth_user)
        assert membership.role.name == "Админ"
        assert membership.role.company_id == company.id

    def test_creator_can_immediately_see_their_new_company(self, auth_client):
        create_response = _post_json(
            auth_client, "/api/v1/companies/", {"name": "Acme Studio"}
        )
        company_id = create_response.json()["id"]

        response = auth_client.get(f"/api/v1/companies/{company_id}/")

        assert response.status_code == 200

    def test_accepts_an_explicit_slug(self, auth_client):
        response = _post_json(
            auth_client,
            "/api/v1/companies/",
            {"name": "Acme Studio", "slug": "custom-slug"},
        )

        assert response.json()["slug"] == "custom-slug"

    def test_rejects_duplicate_slug(self, auth_client, company_factory):
        company_factory(slug="taken")

        response = _post_json(
            auth_client,
            "/api/v1/companies/",
            {"name": "Acme Studio", "slug": "taken"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_blank_name(self, auth_client):
        response = _post_json(auth_client, "/api/v1/companies/", {"name": ""})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_requires_authentication(self, client):
        response = _post_json(client, "/api/v1/companies/", {"name": "Acme Studio"})

        assert response.status_code == 401
