from http import HTTPStatus
import json

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from apps.access.defaults import get_default_role
from apps.companies.models import CompanyMembership
from apps.users.models import User


pytestmark = pytest.mark.django_db


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _account(email, role_id, **overrides):
    """A request body that adds `email` to the company."""
    return {
        "email": email,
        "first_name": "New",
        "last_name": "Person",
        "password": "temporary-passphrase-77",
        "role_id": role_id,
        **overrides,
    }


def _role_id(company, key):
    return get_default_role(company, key).id


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


class TestListMembers:
    def test_returns_all_members(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        other_user = user_factory(email="other@example.com")
        company_membership_factory(user=other_user, company=company)

        response = auth_client.get(f"/api/v1/companies/{company.id}/members/")

        assert response.status_code == 200
        emails = {member["email"] for member in response.json()["items"]}
        assert emails == {auth_user.email, "other@example.com"}

    def test_member_without_an_avatar_gets_null(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)

        response = auth_client.get(f"/api/v1/companies/{company.id}/members/")

        [member] = response.json()["items"]
        assert member["avatar"] is None

    def test_member_with_an_avatar_gets_its_absolute_url(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
    ):
        auth_user.avatar = SimpleUploadedFile(
            "avatar.png", PNG_BYTES, content_type="image/png"
        )
        auth_user.save(update_fields=["avatar"])
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)

        response = auth_client.get(f"/api/v1/companies/{company.id}/members/")

        [member] = response.json()["items"]
        assert member["avatar"] is not None
        assert member["avatar"].startswith("http")
        assert auth_user.avatar.name.split("/")[-1] in member["avatar"]

    def test_non_member_gets_404(
        self, auth_client, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(company=company)

        response = auth_client.get(f"/api/v1/companies/{company.id}/members/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company_factory):
        company = company_factory()

        response = client.get(f"/api/v1/companies/{company.id}/members/")

        assert response.status_code == 401


class TestAddMember:
    def test_adds_an_existing_user_with_the_given_role(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        new_member = user_factory(email="newmember@example.com")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(new_member.email, _role_id(company, "producer")),
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["email"] == "newmember@example.com"
        assert body["role"]["name"] == "Продюсер"
        assert CompanyMembership.objects.filter(
            company=company, user=new_member, role__name="Продюсер"
        ).exists()

    def test_adds_a_member_with_the_executor_role(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        new_member = user_factory()

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(new_member.email, _role_id(company, "executor")),
        )

        assert response.json()["role"]["name"] == "Исполнитель"

    def test_rejects_a_user_who_is_already_a_member(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        existing_member = user_factory()
        company_membership_factory(user=existing_member, company=company)

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(existing_member.email, _role_id(company, "executor")),
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_creates_an_account_for_a_new_email(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account("fresh@example.com", _role_id(company, "freelancer")),
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["role"]["name"] == "Фрилансер"
        created = User.objects.get(email="fresh@example.com")
        assert (created.first_name, created.last_name) == ("New", "Person")
        assert created.check_password("temporary-passphrase-77")
        assert created.must_change_password is True
        assert CompanyMembership.objects.filter(company=company, user=created).exists()

    def test_the_email_is_matched_without_regard_to_case(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        existing = user_factory(email="mixed@example.com")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account("MIXED@example.com", _role_id(company, "executor")),
        )

        assert response.status_code == HTTPStatus.CREATED
        assert User.objects.filter(email__iexact="mixed@example.com").count() == 1
        assert CompanyMembership.objects.filter(company=company, user=existing).exists()

    def test_an_existing_account_is_added_as_is(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        existing = user_factory(first_name="Kept")
        old_hash = existing.password

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(
                existing.email,
                _role_id(company, "executor"),
                first_name="Changed",
                password="another-passphrase-88",
            ),
        )

        assert response.status_code == HTTPStatus.CREATED
        existing.refresh_from_db()
        assert existing.first_name == "Kept"
        assert existing.password == old_hash
        assert existing.must_change_password is False

    def test_a_weak_temporary_password_is_rejected(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(
                "weak@example.com", _role_id(company, "executor"), password="12345678"
            ),
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not User.objects.filter(email="weak@example.com").exists()

    def test_an_invalid_email_is_rejected(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account("not-an-email", _role_id(company, "executor")),
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_cannot_add_members(
        self,
        auth_client,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(company=company)
        new_member = user_factory()

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(new_member.email, _role_id(company, "executor")),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, company_factory, user_factory):
        company = company_factory()
        new_member = user_factory()

        response = _post_json(
            client,
            f"/api/v1/companies/{company.id}/members/",
            _account(new_member.email, _role_id(company, "executor")),
        )

        assert response.status_code == 401


class TestUpdateMember:
    def test_updates_the_role(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        member = user_factory()
        company_membership_factory(user=member, company=company, role="executor")

        response = _patch_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/{member.id}/",
            {"role_id": _role_id(company, "coordinator")},
        )

        assert response.status_code == 200
        assert response.json()["role"]["name"] == "Координатор"

    def test_unknown_member_returns_404(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)

        response = _patch_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/999999/",
            {"role_id": _role_id(company, "coordinator")},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_non_member_gets_404(
        self,
        auth_client,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        member = user_factory()
        company_membership_factory(user=member, company=company)

        response = _patch_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/{member.id}/",
            {"role_id": _role_id(company, "coordinator")},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(
        self, client, company_factory, company_membership_factory, user_factory
    ):
        company = company_factory()
        member = user_factory()
        company_membership_factory(user=member, company=company)

        response = _patch_json(
            client,
            f"/api/v1/companies/{company.id}/members/{member.id}/",
            {"role_id": _role_id(company, "coordinator")},
        )

        assert response.status_code == 401


class TestRemoveMember:
    def test_removes_the_member(
        self,
        auth_client,
        auth_user,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)
        member = user_factory()
        company_membership_factory(user=member, company=company)

        response = auth_client.delete(
            f"/api/v1/companies/{company.id}/members/{member.id}/"
        )

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not CompanyMembership.objects.filter(
            company=company, user=member
        ).exists()

    def test_unknown_member_returns_404(
        self, auth_client, auth_user, company_factory, company_membership_factory
    ):
        company = company_factory()
        company_membership_factory(user=auth_user, company=company)

        response = auth_client.delete(f"/api/v1/companies/{company.id}/members/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(
        self, client, company_factory, company_membership_factory, user_factory
    ):
        company = company_factory()
        member = user_factory()
        company_membership_factory(user=member, company=company)

        response = client.delete(f"/api/v1/companies/{company.id}/members/{member.id}/")

        assert response.status_code == 401


class TestMemberPermissions:
    def test_a_role_without_the_permission_cannot_manage_members(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")
        member = user_factory()
        company_membership_factory(user=member, company=company)
        new_user = user_factory()
        role_id = _role_id(company, "executor")

        added = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(new_user.email, role_id),
        )
        changed = _patch_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/{member.id}/",
            {"role_id": role_id},
        )
        removed = auth_client.delete(
            f"/api/v1/companies/{company.id}/members/{member.id}/"
        )

        assert added.status_code == HTTPStatus.FORBIDDEN
        assert changed.status_code == HTTPStatus.FORBIDDEN
        assert removed.status_code == HTTPStatus.FORBIDDEN

    def test_a_role_of_another_company_is_rejected(
        self,
        auth_client,
        auth_user,
        company,
        company_factory,
        company_membership_factory,
        user_factory,
    ):
        company_membership_factory(user=auth_user, company=company)
        foreign_role_id = _role_id(company_factory(), "executor")

        response = _post_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/",
            _account(user_factory().email, foreign_role_id),
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_the_last_person_who_can_edit_roles_cannot_be_removed_or_demoted(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")

        removed = auth_client.delete(
            f"/api/v1/companies/{company.id}/members/{auth_user.id}/"
        )
        demoted = _patch_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/{auth_user.id}/",
            {"role_id": _role_id(company, "producer")},
        )

        assert removed.status_code == HTTPStatus.CONFLICT
        assert demoted.status_code == HTTPStatus.CONFLICT

    def test_an_admin_can_be_demoted_while_another_one_remains(
        self, auth_client, auth_user, company, company_membership_factory, user_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="admin")
        company_membership_factory(user=user_factory(), company=company, role="admin")

        response = _patch_json(
            auth_client,
            f"/api/v1/companies/{company.id}/members/{auth_user.id}/",
            {"role_id": _role_id(company, "producer")},
        )

        assert response.status_code == HTTPStatus.OK

    def test_removing_a_member_removes_them_from_the_companys_projects(
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
        member = user_factory()
        company_membership_factory(user=member, company=company)
        project = project_factory(company=company)
        project_membership_factory(user=member, project=project)

        response = auth_client.delete(
            f"/api/v1/companies/{company.id}/members/{member.id}/"
        )

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not project.memberships.filter(user=member).exists()
