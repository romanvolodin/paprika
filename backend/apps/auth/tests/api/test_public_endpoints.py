import pytest


# The only API operations that may be called without being logged in: signing
# in, and the invitation link, which is how someone without an account gets
# one (the secret in the link is the credential).
PUBLIC_OPERATIONS = {
    "POST /api/v1/auth/login/",
    "POST /api/v1/auth/refresh/",
    "GET /api/v1/invite/{token}/",
    "POST /api/v1/invite/{token}/register/",
}


def test_only_the_known_operations_are_public(client):
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
