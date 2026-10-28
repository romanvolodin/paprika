from http import HTTPStatus

from django.test import Client
import pytest

from apps.users.models import User
from apps.users.tests.factories import DEFAULT_PASSWORD


pytestmark = pytest.mark.django_db


@pytest.fixture
def ordinary_client(user_factory, log_in):
    """A client logged in as an ordinary user (no superuser flag)."""
    user = user_factory(password=DEFAULT_PASSWORD)
    client = Client()
    response = client.post(
        "/api/v1/auth/login/",
        data={"email": user.email, "password": DEFAULT_PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK, response.content
    client.user = user
    return client


class TestOrdinaryUser:
    def test_can_update_their_own_account(self, ordinary_client, multipart_patch):
        user = ordinary_client.user

        response = multipart_patch(
            ordinary_client, f"/api/v1/users/{user.id}/", {"first_name": "Mine"}
        )

        assert response.status_code == HTTPStatus.OK
        user.refresh_from_db()
        assert user.first_name == "Mine"

    def test_cannot_update_someone_else(
        self, ordinary_client, multipart_patch, user_factory
    ):
        target = user_factory(first_name="Keep")

        response = multipart_patch(
            ordinary_client, f"/api/v1/users/{target.id}/", {"first_name": "Hacked"}
        )

        assert response.status_code == HTTPStatus.FORBIDDEN
        target.refresh_from_db()
        assert target.first_name == "Keep"

    def test_cannot_deactivate_themselves(self, ordinary_client, multipart_patch):
        user = ordinary_client.user

        response = multipart_patch(
            ordinary_client, f"/api/v1/users/{user.id}/", {"is_active": "false"}
        )

        assert response.status_code == HTTPStatus.FORBIDDEN
        user.refresh_from_db()
        assert user.is_active

    def test_cannot_delete_someone_else(self, ordinary_client, user_factory):
        target = user_factory()

        response = ordinary_client.delete(f"/api/v1/users/{target.id}/")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert User.objects.filter(pk=target.pk).exists()

    def test_can_delete_their_own_account(self, ordinary_client):
        user = ordinary_client.user

        response = ordinary_client.delete(f"/api/v1/users/{user.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not User.objects.filter(pk=user.pk).exists()


class TestSuperuser:
    def test_can_update_and_delete_anyone(
        self, auth_client, multipart_patch, user_factory
    ):
        target = user_factory()

        updated = multipart_patch(
            auth_client, f"/api/v1/users/{target.id}/", {"first_name": "Changed"}
        )
        deleted = auth_client.delete(f"/api/v1/users/{target.id}/")

        assert updated.status_code == HTTPStatus.OK
        assert deleted.status_code == HTTPStatus.NO_CONTENT
