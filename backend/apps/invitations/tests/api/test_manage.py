from datetime import timedelta
from http import HTTPStatus
import json

from django.utils import timezone
import pytest

from apps.access.defaults import get_default_role
from apps.invitations.models import Invitation


pytestmark = pytest.mark.django_db


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _url(company):
    return f"/api/v1/companies/{company.id}/invitations/"


@pytest.fixture
def producer_company(auth_user, company, company_membership_factory):
    company_membership_factory(user=auth_user, company=company, role="producer")
    return company


class TestCreateCompanyInvitation:
    def test_invites_to_the_company_and_projects(
        self, auth_client, producer_company, project_factory
    ):
        project = project_factory(company=producer_company)
        executor = get_default_role(producer_company, "executor")
        freelancer = get_default_role(producer_company, "freelancer")

        response = _post(
            auth_client,
            _url(producer_company),
            {
                "email": "Newbie@Example.com",
                "role_id": freelancer.id,
                "projects": [{"project_id": project.id, "role_id": executor.id}],
            },
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["email"] == "Newbie@example.com"
        assert body["role"]["name"] == "Фрилансер"
        assert body["projects"][0]["project_name"] == project.name
        assert body["projects"][0]["role"]["name"] == "Исполнитель"
        assert body["is_expired"] is False
        assert len(body["token"]) >= 32
        invitation = Invitation.objects.get(pk=body["id"])
        assert invitation.created_by is not None

    def test_the_link_lasts_the_configured_term(
        self, auth_client, producer_company, settings
    ):
        settings.INVITATION_TTL_DAYS = 3

        response = _post(
            auth_client,
            _url(producer_company),
            {
                "email": "a@example.com",
                "role_id": get_default_role(producer_company, "client").id,
            },
        )

        invitation = Invitation.objects.get(pk=response.json()["id"])
        left = invitation.expires_at - timezone.now()
        assert timedelta(days=2, hours=23) < left <= timedelta(days=3)

    def test_inviting_twice_is_a_409_until_the_first_one_expires(
        self, auth_client, producer_company
    ):
        role_id = get_default_role(producer_company, "client").id
        payload = {"email": "twice@example.com", "role_id": role_id}
        _post(auth_client, _url(producer_company), payload)

        again = _post(
            auth_client,
            _url(producer_company),
            {**payload, "email": "TWICE@example.com"},
        )
        Invitation.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        later = _post(auth_client, _url(producer_company), payload)

        assert again.status_code == HTTPStatus.CONFLICT
        assert later.status_code == HTTPStatus.CREATED
        assert Invitation.objects.filter(company=producer_company).count() == 1

    def test_a_person_who_is_already_a_member_is_a_400(
        self, auth_client, producer_company, company_membership_factory
    ):
        member = company_membership_factory(company=producer_company)

        response = _post(
            auth_client,
            _url(producer_company),
            {
                "email": member.user.email,
                "role_id": get_default_role(producer_company, "client").id,
            },
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_roles_and_projects_must_belong_to_the_company(
        self, auth_client, producer_company, company_factory, project_factory
    ):
        other = company_factory()
        mine = get_default_role(producer_company, "client").id

        foreign_role = _post(
            auth_client,
            _url(producer_company),
            {"email": "a@example.com", "role_id": get_default_role(other, "client").id},
        )
        foreign_project = _post(
            auth_client,
            _url(producer_company),
            {
                "email": "b@example.com",
                "role_id": mine,
                "projects": [
                    {"project_id": project_factory(company=other).id, "role_id": mine}
                ],
            },
        )

        assert foreign_role.status_code == HTTPStatus.BAD_REQUEST
        assert foreign_project.status_code == HTTPStatus.NOT_FOUND

    def test_a_project_listed_twice_is_a_400(
        self, auth_client, producer_company, project_factory
    ):
        project = project_factory(company=producer_company)
        role_id = get_default_role(producer_company, "client").id

        response = _post(
            auth_client,
            _url(producer_company),
            {
                "email": "a@example.com",
                "role_id": role_id,
                "projects": [
                    {"project_id": project.id, "role_id": role_id},
                    {"project_id": project.id, "role_id": role_id},
                ],
            },
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_a_producer_cannot_invite_an_admin(self, auth_client, producer_company):
        response = _post(
            auth_client,
            _url(producer_company),
            {
                "email": "a@example.com",
                "role_id": get_default_role(producer_company, "admin").id,
            },
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_a_role_without_the_permission_gets_a_403(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")

        response = _post(
            auth_client,
            _url(company),
            {
                "email": "a@example.com",
                "role_id": get_default_role(company, "client").id,
            },
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_another_company_is_a_404(self, auth_client, company):
        response = _post(
            auth_client,
            _url(company),
            {
                "email": "a@example.com",
                "role_id": get_default_role(company, "client").id,
            },
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestListInvitations:
    def test_lists_the_open_ones_expired_included(
        self, auth_client, producer_company, invitation_factory
    ):
        open_one = invitation_factory(company=producer_company)
        expired = invitation_factory(company=producer_company)
        Invitation.objects.filter(pk=expired.pk).update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        invitation_factory(company=producer_company, accepted_at=timezone.now())
        invitation_factory()  # another company

        response = auth_client.get(_url(producer_company))

        assert response.status_code == HTTPStatus.OK
        by_id = {item["id"]: item for item in response.json()["items"]}
        assert set(by_id) == {open_one.id, expired.id}
        assert by_id[expired.id]["is_expired"] is True
        assert by_id[open_one.id]["is_expired"] is False

    def test_needs_the_permission(
        self, auth_client, auth_user, company, company_membership_factory
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")

        assert auth_client.get(_url(company)).status_code == HTTPStatus.FORBIDDEN


class TestProjectInvitation:
    @pytest.fixture
    def coordinator_project(
        self,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project, role="coordinator")
        return project

    def _url(self, project):
        return f"/api/v1/projects/{project.id}/invitations/"

    def test_invites_to_one_project_with_the_same_role_in_the_company(
        self, auth_client, coordinator_project
    ):
        role = get_default_role(coordinator_project.company, "freelancer")

        response = _post(
            auth_client,
            self._url(coordinator_project),
            {"email": "free@example.com", "role_id": role.id},
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["role"]["id"] == role.id
        assert [p["project_id"] for p in body["projects"]] == [coordinator_project.id]
        assert body["projects"][0]["role"]["id"] == role.id

    @pytest.mark.parametrize("key", ["producer", "admin"])
    def test_a_role_with_company_rights_is_a_400(
        self, auth_client, coordinator_project, key
    ):
        role = get_default_role(coordinator_project.company, key)

        response = _post(
            auth_client,
            self._url(coordinator_project),
            {"email": "x@example.com", "role_id": role.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_a_role_that_sees_all_projects_is_a_400(
        self, auth_client, coordinator_project, role_factory
    ):
        wide = role_factory(
            company=coordinator_project.company, permissions=[], sees_all_projects=True
        )

        response = _post(
            auth_client,
            self._url(coordinator_project),
            {"email": "x@example.com", "role_id": wide.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_needs_the_project_members_permission(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        project_factory,
        project_membership_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="executor")
        project = project_factory(company=company)
        project_membership_factory(user=auth_user, project=project, role="executor")

        response = _post(
            auth_client,
            self._url(project),
            {
                "email": "x@example.com",
                "role_id": get_default_role(company, "client").id,
            },
        )

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestRenewAndRevoke:
    def test_renewing_gives_a_new_link_and_a_fresh_term(
        self, auth_client, producer_company, invitation_factory
    ):
        invitation = invitation_factory(company=producer_company)
        Invitation.objects.filter(pk=invitation.pk).update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        old_token = invitation.token

        response = auth_client.post(f"/api/v1/invitations/{invitation.id}/renew/")

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["token"] != old_token
        assert body["is_expired"] is False
        assert (
            auth_client.get(f"/api/v1/invite/{old_token}/").status_code
            == HTTPStatus.NOT_FOUND
        )

    def test_revoking_deletes_the_invitation(
        self, auth_client, producer_company, invitation_factory
    ):
        invitation = invitation_factory(company=producer_company)

        response = auth_client.delete(f"/api/v1/invitations/{invitation.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Invitation.objects.filter(pk=invitation.pk).exists()

    def test_the_sender_may_manage_their_own_without_company_rights(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        invitation_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")
        invitation = invitation_factory(company=company, created_by=auth_user)

        response = auth_client.delete(f"/api/v1/invitations/{invitation.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT

    def test_someone_else_s_invitation_needs_the_permission(
        self,
        auth_client,
        auth_user,
        company,
        company_membership_factory,
        invitation_factory,
    ):
        company_membership_factory(user=auth_user, company=company, role="coordinator")
        invitation = invitation_factory(company=company)

        deleted = auth_client.delete(f"/api/v1/invitations/{invitation.id}/")
        renewed = auth_client.post(f"/api/v1/invitations/{invitation.id}/renew/")

        assert deleted.status_code == HTTPStatus.FORBIDDEN
        assert renewed.status_code == HTTPStatus.FORBIDDEN

    def test_an_accepted_invitation_is_gone(
        self, auth_client, producer_company, invitation_factory
    ):
        invitation = invitation_factory(
            company=producer_company, accepted_at=timezone.now()
        )

        assert (
            auth_client.delete(f"/api/v1/invitations/{invitation.id}/").status_code
            == HTTPStatus.NOT_FOUND
        )

    def test_another_company_s_invitation_is_a_404(
        self, auth_client, invitation_factory
    ):
        invitation = invitation_factory()

        assert (
            auth_client.delete(f"/api/v1/invitations/{invitation.id}/").status_code
            == HTTPStatus.NOT_FOUND
        )
