import pytest


# The only API operations that may be called without being logged in.
PUBLIC_OPERATIONS = {
    "POST /api/v1/auth/login/",
    "POST /api/v1/auth/refresh/",
}


def test_only_login_and_refresh_are_public(client):
    """Every other operation must declare a security requirement.

    Authentication comes from `AuthenticatedController`; a controller that
    skips it (by inheriting from `Controller` directly) shows up here.
    """
    schema = client.get("/api/v1/docs/openapi.json").json()

    unprotected = {
        f"{method.upper()} {path}"
        for path, item in schema["paths"].items()
        for method, operation in item.items()
        if isinstance(operation, dict)
        and "operationId" in operation
        and not operation.get("security")
    }

    assert unprotected == PUBLIC_OPERATIONS


@pytest.mark.django_db
def test_a_protected_endpoint_rejects_anonymous_requests(client):
    response = client.get("/api/v1/companies/")

    assert response.status_code == 401
