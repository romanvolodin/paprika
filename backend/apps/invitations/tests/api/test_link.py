from datetime import timedelta
from http import HTTPStatus
import json

from django.test import Client
from django.utils import timezone
import pytest

from apps.access.defaults import get_default_role
from apps.companies.models import CompanyMembership
from apps.invitations.models import Invitation, InvitationProject
from apps.projects.models import ProjectMembership
from apps.users.models import User
from apps.users.tests.factories import DEFAULT_PASSWORD


pytestmark = pytest.mark.django_db

PASSWORD = "a-fresh-passphrase-2026"


def _register(client, token, **overrides):
    return client.post(
        f"/api/v1/invite/{token}/register/",
        data=json.dumps(
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "password": PASSWORD,
                **overrides,
            }
        ),
        content_type="application/json",
    )


@pytest.fixture
def invitation(invitation_factory, company, project_factory):
    invitation = invitation_factory(
        company=company, email="invitee@example.com", role="freelancer"
    )
    InvitationProject.objects.create(
        invitation=invitation,
        project=project_factory(company=company),
        role=get_default_role(company, "executor"),
    )
    return invitation


@pytest.fixture
def anonymous():
    return Client()


class TestInfo:
    def test_anyone_with_the_link_can_look(self, anonymous, invitation):
        response = anonymous.get(f"/api/v1/invite/{invitation.token}/")

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["email"] == "invitee@example.com"
        assert body["company_id"] == invitation.company_id
        assert body["company_name"] == invitation.company.name
        assert body["role_name"] == "Фрилансер"
        assert len(body["project_names"]) == 1
        assert body["status"] == "pending"
        assert body["account_exists"] is False

    def test_tells_when_the_email_already_has_an_account(
        self, anonymous, invitation, user_factory
    ):
        user_factory(email="INVITEE@example.com")

        body = anonymous.get(f"/api/v1/invite/{invitation.token}/").json()

        assert body["account_exists"] is True

    def test_tells_expired_and_accepted(self, anonymous, invitation_factory):
        expired = invitation_factory()
        Invitation.objects.filter(pk=expired.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        accepted = invitation_factory(accepted_at=timezone.now())

        assert (
            anonymous.get(f"/api/v1/invite/{expired.token}/").json()["status"]
            == "expired"
        )
        assert (
            anonymous.get(f"/api/v1/invite/{accepted.token}/").json()["status"]
            == "accepted"
        )

    def test_an_unknown_token_is_a_404(self, anonymous):
        assert anonymous.get("/api/v1/invite/nope/").status_code == HTTPStatus.NOT_FOUND


class TestRegister:
    def test_makes_the_account_and_joins_everything(self, anonymous, invitation):
        response = _register(anonymous, invitation.token)

        assert response.status_code == HTTPStatus.NO_CONTENT
        user = User.objects.get(email="invitee@example.com")
        assert (user.first_name, user.last_name) == ("Анна", "Иванова")
        assert user.check_password(PASSWORD)
        assert user.must_change_password is False
        membership = CompanyMembership.objects.get(
            user=user, company=invitation.company
        )
        assert membership.role.name == "Фрилансер"
        project_membership = ProjectMembership.objects.get(user=user)
        assert project_membership.role.name == "Исполнитель"
        invitation.refresh_from_db()
        assert invitation.accepted_at is not None

    def test_the_new_account_can_sign_in(self, anonymous, invitation):
        _register(anonymous, invitation.token)

        response = anonymous.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "invitee@example.com", "password": PASSWORD}),
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.OK

    def test_cannot_be_used_twice(self, anonymous, invitation):
        _register(anonymous, invitation.token)

        again = _register(anonymous, invitation.token)

        assert again.status_code == HTTPStatus.GONE

    def test_an_existing_account_is_a_409(self, anonymous, invitation, user_factory):
        user_factory(email="invitee@example.com")

        response = _register(anonymous, invitation.token)

        assert response.status_code == HTTPStatus.CONFLICT
        invitation.refresh_from_db()
        assert invitation.accepted_at is None

    def test_a_weak_password_is_a_400(self, anonymous, invitation):
        response = _register(anonymous, invitation.token, password="12345678")

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not User.objects.filter(email="invitee@example.com").exists()

    def test_an_expired_invitation_is_gone(self, anonymous, invitation):
        Invitation.objects.filter(pk=invitation.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        assert _register(anonymous, invitation.token).status_code == HTTPStatus.GONE

    def test_an_unknown_token_is_a_404(self, anonymous):
        assert _register(anonymous, "nope").status_code == HTTPStatus.NOT_FOUND


class TestAccept:
    @pytest.fixture
    def invitee(self, user_factory):
        return user_factory(email="Invitee@example.com", password=DEFAULT_PASSWORD)

    def _signed_in(self, user):
        client = Client()
        response = client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": user.email, "password": DEFAULT_PASSWORD}),
            content_type="application/json",
        )
        assert response.status_code == HTTPStatus.OK
        return client

    def test_the_account_with_that_email_joins(self, invitation, invitee):
        client = self._signed_in(invitee)

        response = client.post(f"/api/v1/invite/{invitation.token}/accept/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert CompanyMembership.objects.filter(
            user=invitee, company=invitation.company
        ).exists()
        assert ProjectMembership.objects.filter(user=invitee).exists()
        invitation.refresh_from_db()
        assert invitation.accepted_at is not None

    def test_another_email_is_a_403(self, invitation, user_factory):
        stranger = user_factory(password=DEFAULT_PASSWORD)
        client = self._signed_in(stranger)

        response = client.post(f"/api/v1/invite/{invitation.token}/accept/")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not CompanyMembership.objects.filter(user=stranger).exists()

    def test_needs_to_be_signed_in(self, anonymous, invitation):
        response = anonymous.post(f"/api/v1/invite/{invitation.token}/accept/")

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_an_expired_invitation_is_gone(self, invitation, invitee):
        Invitation.objects.filter(pk=invitation.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        client = self._signed_in(invitee)

        response = client.post(f"/api/v1/invite/{invitation.token}/accept/")

        assert response.status_code == HTTPStatus.GONE

    def test_someone_already_in_keeps_their_role(
        self, invitation, invitee, company_membership_factory
    ):
        company_membership_factory(
            user=invitee, company=invitation.company, role="admin"
        )
        client = self._signed_in(invitee)

        client.post(f"/api/v1/invite/{invitation.token}/accept/")

        membership = CompanyMembership.objects.get(
            user=invitee, company=invitation.company
        )
        assert membership.role.name == "Админ"

    @pytest.fixture
    def anonymous(self):
        return Client()
