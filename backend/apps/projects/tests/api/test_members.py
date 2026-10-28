from http import HTTPStatus
import json

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from apps.access.defaults import get_default_role
from apps.projects.models import ProjectMembership


pytestmark = pytest.mark.django_db


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _role_id(project, key):
    return get_default_role(project.company, key).id


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


class TestListMembers:
    def test_returns_all_members(
        self,
        auth_client,
        auth_user,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)
        other_user = user_factory(email="other@example.com")
        project_membership_factory(user=other_user, project=project)

        response = auth_client.get(f"/api/v1/projects/{project.id}/members/")

        assert response.status_code == 200
        emails = {member["email"] for member in response.json()["items"]}
        assert emails == {auth_user.email, "other@example.com"}

    def test_member_without_an_avatar_gets_null(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(f"/api/v1/projects/{project.id}/members/")

        [member] = response.json()["items"]
        assert member["avatar"] is None

    def test_member_with_an_avatar_gets_its_absolute_url(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        auth_user.avatar = SimpleUploadedFile(
            "avatar.png", PNG_BYTES, content_type="image/png"
        )
        auth_user.save(update_fields=["avatar"])
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(f"/api/v1/projects/{project.id}/members/")

        [member] = response.json()["items"]
        assert member["avatar"] is not None
        assert member["avatar"].startswith("http")

    def test_non_member_gets_404(
        self, auth_client, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(project=project)  # some other user

        response = auth_client.get(f"/api/v1/projects/{project.id}/members/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project_factory):
        project = project_factory()

        response = client.get(f"/api/v1/projects/{project.id}/members/")

        assert response.status_code == 401


class TestAddMember:
    def test_adds_an_existing_company_member_with_the_given_role(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        new_member = user_factory(email="newmember@example.com")
        company_membership_factory(user=new_member, company=company)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": new_member.id, "role_id": _role_id(project, "producer")},
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["email"] == "newmember@example.com"
        assert body["role"]["name"] == "Продюсер"
        assert ProjectMembership.objects.filter(
            project=project, user=new_member, role__name="Продюсер"
        ).exists()

    def test_adds_a_member_with_the_executor_role(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        new_member = user_factory()
        company_membership_factory(user=new_member, company=company)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": new_member.id, "role_id": _role_id(project, "executor")},
        )

        assert response.json()["role"]["name"] == "Исполнитель"

    def test_rejects_a_user_who_is_not_a_company_member(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        outsider = user_factory()  # not a member of `company`

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": outsider.id, "role_id": _role_id(project, "executor")},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert not ProjectMembership.objects.filter(
            project=project, user=outsider
        ).exists()

    def test_rejects_a_user_who_is_already_a_project_member(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        existing_member = user_factory()
        company_membership_factory(user=existing_member, company=company)
        project_membership_factory(user=existing_member, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": existing_member.id, "role_id": _role_id(project, "executor")},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_an_unknown_user_id(
        self,
        auth_client,
        auth_user,
        project_factory,
        project_membership_factory,
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": 999999, "role_id": _role_id(project, "executor")},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_non_member_cannot_add_members(
        self,
        auth_client,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        project = project_factory()
        project_membership_factory(project=project)  # some other user
        new_member = user_factory()

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": new_member.id, "role_id": _role_id(project, "executor")},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project_factory, user_factory):
        project = project_factory()
        new_member = user_factory()

        response = _post_json(
            client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": new_member.id, "role_id": _role_id(project, "executor")},
        )

        assert response.status_code == 401


class TestUpdateMember:
    def test_updates_the_role(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        member = user_factory()
        company_membership_factory(user=member, company=company)
        project_membership_factory(user=member, project=project, role="executor")

        response = _patch_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/{member.id}/",
            {"role_id": _role_id(project, "coordinator")},
        )

        assert response.status_code == 200
        assert response.json()["role"]["name"] == "Координатор"

    def test_unknown_member_returns_404(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)

        response = _patch_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/999999/",
            {"role_id": _role_id(project, "coordinator")},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_non_member_gets_404(
        self,
        auth_client,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        project = project_factory()
        member = user_factory()
        project_membership_factory(user=member, project=project)

        response = _patch_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/{member.id}/",
            {"role_id": _role_id(project, "coordinator")},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(
        self, client, project_factory, project_membership_factory, user_factory
    ):
        project = project_factory()
        member = user_factory()
        project_membership_factory(user=member, project=project)

        response = _patch_json(
            client,
            f"/api/v1/projects/{project.id}/members/{member.id}/",
            {"role_id": _role_id(project, "coordinator")},
        )

        assert response.status_code == 401


class TestRemoveMember:
    def test_removes_the_member(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        member = user_factory()
        company_membership_factory(user=member, company=company)
        project_membership_factory(user=member, project=project)

        response = auth_client.delete(
            f"/api/v1/projects/{project.id}/members/{member.id}/"
        )

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not ProjectMembership.objects.filter(
            project=project, user=member
        ).exists()

    def test_unknown_member_returns_404(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.delete(f"/api/v1/projects/{project.id}/members/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(
        self, client, project_factory, project_membership_factory, user_factory
    ):
        project = project_factory()
        member = user_factory()
        project_membership_factory(user=member, project=project)

        response = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}/")

        assert response.status_code == 401


class TestMemberPermissions:
    @pytest.fixture
    def executor_project(
        self,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="executor")
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project, role="executor")
        return project

    def test_a_role_without_the_permission_cannot_manage_members(
        self,
        auth_client,
        executor_project,
        company_membership_factory,
        project_membership_factory,
        user_factory,
    ):
        project = executor_project
        member = user_factory()
        company_membership_factory(user=member, company=project.company)
        project_membership_factory(user=member, project=project)
        new_user = user_factory()
        company_membership_factory(user=new_user, company=project.company)
        role_id = _role_id(project, "coordinator")

        added = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": new_user.id, "role_id": role_id},
        )
        changed = _patch_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/{member.id}/",
            {"role_id": role_id},
        )
        removed = auth_client.delete(
            f"/api/v1/projects/{project.id}/members/{member.id}/"
        )

        assert added.status_code == HTTPStatus.FORBIDDEN
        assert changed.status_code == HTTPStatus.FORBIDDEN
        assert removed.status_code == HTTPStatus.FORBIDDEN
        assert ProjectMembership.objects.filter(project=project, user=member).exists()

    def test_a_role_of_another_company_is_rejected(
        self,
        auth_client,
        auth_user,
        company,
        company_factory,
        company_membership_factory,
        project_factory,
        project_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project)
        new_user = user_factory()
        company_membership_factory(user=new_user, company=company)
        foreign_role_id = get_default_role(company_factory(), "executor").id

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": new_user.id, "role_id": foreign_role_id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_role_id_is_required(
        self, auth_client, auth_user, project, project_membership_factory, user_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": user_factory().id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
