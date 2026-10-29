from http import HTTPStatus
import json

import pytest

from apps.users.tests.factories import DEFAULT_PASSWORD


pytestmark = pytest.mark.django_db

NEW_PASSWORD = "a-much-better-passphrase-42"


def _change(client, current, new):
    return client.post(
        "/api/v1/auth/password/",
        data=json.dumps({"current_password": current, "new_password": new}),
        content_type="application/json",
    )


class TestChangePassword:
    def test_changes_the_password(self, auth_client, auth_user):
        response = _change(auth_client, DEFAULT_PASSWORD, NEW_PASSWORD)

        assert response.status_code == HTTPStatus.NO_CONTENT
        auth_user.refresh_from_db()
        assert auth_user.check_password(NEW_PASSWORD)
        assert not auth_user.check_password(DEFAULT_PASSWORD)

    def test_the_new_password_signs_in(self, auth_client, auth_user, client):
        _change(auth_client, DEFAULT_PASSWORD, NEW_PASSWORD)
        client.cookies.clear()

        response = client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": auth_user.email, "password": NEW_PASSWORD}),
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.OK

    def test_a_wrong_current_password_is_rejected(self, auth_client, auth_user):
        response = _change(auth_client, "not-my-password", NEW_PASSWORD)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        auth_user.refresh_from_db()
        assert auth_user.check_password(DEFAULT_PASSWORD)

    def test_a_weak_new_password_is_rejected(self, auth_client, auth_user):
        response = _change(auth_client, DEFAULT_PASSWORD, "12345678")

        assert response.status_code == HTTPStatus.BAD_REQUEST
        auth_user.refresh_from_db()
        assert auth_user.check_password(DEFAULT_PASSWORD)

    def test_requires_authentication(self, client):
        response = _change(client, DEFAULT_PASSWORD, NEW_PASSWORD)

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestTemporaryPassword:
    @pytest.fixture
    def pending_client(self, auth_user, auth_client):
        auth_user.must_change_password = True
        auth_user.save(update_fields=["must_change_password"])
        return auth_client

    def test_login_tells_about_it(self, auth_user, client):
        auth_user.must_change_password = True
        auth_user.save(update_fields=["must_change_password"])

        response = client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": auth_user.email, "password": DEFAULT_PASSWORD}),
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["must_change_password"] is True

    def test_nothing_else_works_until_it_is_changed(self, pending_client):
        response = pending_client.get("/api/v1/companies/")

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_the_user_can_still_be_read_and_signed_out(self, pending_client):
        me = pending_client.get("/api/v1/users/me/")
        logout = pending_client.post("/api/v1/auth/logout/")

        assert me.status_code == HTTPStatus.OK
        assert me.json()["must_change_password"] is True
        assert logout.status_code == HTTPStatus.NO_CONTENT

    def test_changing_the_password_lifts_the_block(self, pending_client, auth_user):
        changed = _change(pending_client, DEFAULT_PASSWORD, NEW_PASSWORD)
        listed = pending_client.get("/api/v1/companies/")

        assert changed.status_code == HTTPStatus.NO_CONTENT
        auth_user.refresh_from_db()
        assert auth_user.must_change_password is False
        assert listed.status_code == HTTPStatus.OK


class TestMe:
    def test_the_signed_in_user_sees_their_flags(self, auth_client, auth_user):
        body = auth_client.get("/api/v1/users/me/").json()

        assert body["is_superuser"] is False
        assert body["must_change_password"] is False
