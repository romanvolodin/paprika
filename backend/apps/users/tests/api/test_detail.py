from http import HTTPStatus

import pytest

from apps.users.models import User


pytestmark = pytest.mark.django_db


class TestGetUser:
    def test_returns_the_requested_user(self, auth_client, user_factory):
        target = user_factory(email="target@example.com")

        response = auth_client.get(f"/api/v1/users/{target.id}/")

        assert response.status_code == 200
        assert response.json()["email"] == "target@example.com"

    def test_unknown_id_returns_404_with_a_message(self, auth_client):
        response = auth_client.get("/api/v1/users/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "999999" in response.json()["detail"]

    def test_zero_id_is_a_validation_error_not_404(self, auth_client):
        # `UserPath.user_id` has `gt=0`, so 0 fails schema validation
        # before ever reaching the database lookup.
        response = auth_client.get("/api/v1/users/0/")

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_negative_id_returns_a_plain_404_via_url_routing(self, auth_client):
        # By design there's no custom path converter for negative ints:
        # `<int:user_id>` in urls.py simply doesn't match a leading `-`,
        # so Django's router 404s before the view (and thus dmr) ever runs.
        response = auth_client.get("/api/v1/users/-1/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response["Content-Type"].startswith("text/html")

    def test_requires_authentication(self, client, user_factory):
        target = user_factory()

        response = client.get(f"/api/v1/users/{target.id}/")

        assert response.status_code == 401


class TestUpdateUser:
    def test_updates_first_and_last_name(
        self, auth_client, multipart_patch, user_factory
    ):
        target = user_factory(first_name="Old", last_name="Name")

        response = multipart_patch(
            auth_client,
            f"/api/v1/users/{target.id}/",
            {"first_name": "New", "last_name": "Surname"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["first_name"] == "New"
        assert body["last_name"] == "Surname"

    def test_partial_update_leaves_other_fields_untouched(
        self,
        auth_client,
        multipart_patch,
        user_factory,
    ):
        target = user_factory(first_name="Keep", last_name="Me")

        response = multipart_patch(
            auth_client,
            f"/api/v1/users/{target.id}/",
            {"last_name": "Changed"},
        )

        body = response.json()
        assert body["first_name"] == "Keep"
        assert body["last_name"] == "Changed"

    def test_can_deactivate_a_user(self, auth_client, multipart_patch, user_factory):
        target = user_factory(is_active=True)

        response = multipart_patch(
            auth_client,
            f"/api/v1/users/{target.id}/",
            {"is_active": "false"},
        )

        assert response.json()["is_active"] is False
        target.refresh_from_db()
        assert target.is_active is False

    def test_empty_body_changes_nothing(
        self, auth_client, multipart_patch, user_factory
    ):
        target = user_factory(first_name="Untouched")

        response = multipart_patch(auth_client, f"/api/v1/users/{target.id}/", {})

        assert response.status_code == 200
        assert response.json()["first_name"] == "Untouched"

    def test_unknown_id_returns_404(self, auth_client, multipart_patch):
        response = multipart_patch(
            auth_client,
            "/api/v1/users/999999/",
            {"first_name": "Ghost"},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_rejects_blank_first_name(self, auth_client, multipart_patch, user_factory):
        target = user_factory()

        response = multipart_patch(
            auth_client,
            f"/api/v1/users/{target.id}/",
            {"first_name": ""},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_requires_authentication(self, client, multipart_patch, user_factory):
        target = user_factory()

        response = multipart_patch(
            client,
            f"/api/v1/users/{target.id}/",
            {"first_name": "Hacked"},
        )

        assert response.status_code == 401


class TestDeleteUser:
    """`UserDetailController.delete()` is documented as a permanent, hard
    delete (see its `@modify(description=...)`), not a soft-delete/deactivation
    - these tests lock in that intentional behavior."""

    def test_deletes_the_user(self, auth_client, user_factory):
        target = user_factory()

        response = auth_client.delete(f"/api/v1/users/{target.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not User.objects.filter(id=target.id).exists()

    def test_deleted_user_then_404s_on_get(self, auth_client, user_factory):
        target = user_factory()
        auth_client.delete(f"/api/v1/users/{target.id}/")

        response = auth_client.get(f"/api/v1/users/{target.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unknown_id_returns_404(self, auth_client):
        response = auth_client.delete("/api/v1/users/999999/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, user_factory):
        target = user_factory()

        response = client.delete(f"/api/v1/users/{target.id}/")

        assert response.status_code == 401
        assert User.objects.filter(id=target.id).exists()


class TestDeleteLastRoleManager:
    def test_rejects_deleting_the_only_person_who_can_edit_roles(
        self, auth_client, user_factory, company, company_membership_factory
    ):
        target = user_factory()
        company_membership_factory(user=target, company=company, role="admin")

        response = auth_client.delete(f"/api/v1/users/{target.id}/")

        assert response.status_code == HTTPStatus.CONFLICT
        assert company.name in response.json()["detail"]
        assert User.objects.filter(id=target.id).exists()

    def test_allows_it_when_someone_else_can_edit_roles(
        self, auth_client, user_factory, company, company_membership_factory
    ):
        target = user_factory()
        company_membership_factory(user=target, company=company, role="admin")
        company_membership_factory(user=user_factory(), company=company, role="admin")

        response = auth_client.delete(f"/api/v1/users/{target.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
