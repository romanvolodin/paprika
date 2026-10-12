from http import HTTPStatus
import re

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from apps.projects.models import Project, ProjectMembership


pytestmark = pytest.mark.django_db

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _post_multipart(client, path, payload):
    # The endpoint now only accepts `multipart/form-data` (it can take a
    # `cover` file), so every create call goes through it - Django's test
    # client already defaults to multipart encoding for a plain dict.
    return client.post(path, data=payload)


class TestListProjects:
    def test_returns_only_projects_the_user_is_a_member_of(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        my_project = project_factory(company=company, name="Mine")
        project_membership_factory(user=auth_user, project=my_project)
        other_project = project_factory(company=company, name="Someone Else's")
        project_membership_factory(project=other_project)  # different user

        response = auth_client.get(f"/api/v1/companies/{company.id}/projects/")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Mine"

    def test_company_membership_alone_does_not_grant_visibility(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
    ):
        # Belonging to the company isn't enough - an explicit
        # `ProjectMembership` is required to see a project.
        company_membership_factory(user=auth_user, company=company)
        project_factory(company=company)

        response = auth_client.get(f"/api/v1/companies/{company.id}/projects/")

        assert response.json()["total"] == 0

    def test_search_filters_by_name(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        findable = project_factory(company=company, name="Findable Feature")
        project_membership_factory(user=auth_user, project=findable)
        other = project_factory(company=company, name="Other Feature")
        project_membership_factory(user=auth_user, project=other)

        response = auth_client.get(
            f"/api/v1/companies/{company.id}/projects/?search=findable"
        )

        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Findable Feature"

    def test_code_filters_by_exact_code_not_by_name_or_substring(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        for code, name in [
            ("VRG", "Feature"),
            ("VRG2", "VRG Sequel"),
            ("vrg", "Lower"),
        ]:
            project = project_factory(company=company, code=code, name=name)
            project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(f"/api/v1/companies/{company.id}/projects/?code=VRG")

        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["code"] == "VRG"

    def test_code_filter_only_returns_projects_the_user_is_a_member_of(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project_factory(company=company, code="VRG")  # no membership for the user

        response = auth_client.get(f"/api/v1/companies/{company.id}/projects/?code=VRG")

        assert response.json()["total"] == 0

    def test_non_member_of_company_gets_404(
        self, auth_client, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(company=company)  # some other user

        response = auth_client.get(f"/api/v1/companies/{company.id}/projects/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company):
        response = client.get(f"/api/v1/companies/{company.id}/projects/")

        assert response.status_code == 401


class TestCreateProject:
    def test_creates_a_project(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Acme Feature", "code": "PRJ"},
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["name"] == "Acme Feature"
        assert body["code"] == "PRJ"
        assert body["is_active"] is True
        assert Project.objects.filter(company=company, code="PRJ").exists()

    def test_response_includes_created_by_and_updated_by(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Acme Feature", "code": "PRJ"},
        )

        body = response.json()
        assert body["created_by"]["id"] == auth_user.id
        assert body["created_by"]["email"] == auth_user.email
        assert body["updated_by"]["id"] == auth_user.id

    def test_creator_becomes_an_admin_member(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Acme Feature", "code": "PRJ"},
        )

        project = Project.objects.get(id=response.json()["id"])
        membership = ProjectMembership.objects.get(project=project, user=auth_user)
        assert membership.role == ProjectMembership.Role.ADMIN

    def test_creator_can_immediately_see_their_new_project(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)
        create_response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Acme Feature", "code": "PRJ"},
        )
        project_id = create_response.json()["id"]

        response = auth_client.get(f"/api/v1/projects/{project_id}/")

        assert response.status_code == 200

    def test_creates_a_project_with_a_cover(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)
        cover = SimpleUploadedFile("cover.png", PNG_BYTES, content_type="image/png")

        response = auth_client.post(
            f"/api/v1/companies/{company.id}/projects/",
            data={"name": "Acme Feature", "code": "PRJ", "cover": cover},
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["cover"] is not None
        assert re.search(
            rf"/media/{company.storage_token}/PRJ/cover-[a-z0-9]{{8}}\.png$",
            response.json()["cover"],
        )

    def test_rejects_duplicate_code_within_company(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project_factory(company=company, code="PRJ")

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Another", "code": "PRJ"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_same_code_allowed_in_a_different_company(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        project_factory,
    ):
        other_company = company_factory()
        project_factory(company=other_company, code="PRJ")
        my_company = company_factory()
        company_membership_factory(user=auth_user, company=my_company)

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{my_company.id}/projects/",
            {"name": "Mine", "code": "PRJ"},
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_rejects_invalid_code_characters(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Acme Feature", "code": "PRJ 001!"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_blank_name(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "", "code": "PRJ"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_deadline_before_start_date(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company)

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {
                "name": "Acme Feature",
                "code": "PRJ",
                "start_date": "2026-06-01",
                "deadline": "2026-01-01",
            },
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_of_company_gets_404(
        self, auth_client, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(company=company)  # some other user

        response = _post_multipart(
            auth_client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Acme Feature", "code": "PRJ"},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company):
        response = _post_multipart(
            client,
            f"/api/v1/companies/{company.id}/projects/",
            {"name": "Acme Feature", "code": "PRJ"},
        )

        assert response.status_code == 401
