import pytest

from apps.users.tests.factories import DEFAULT_PASSWORD


@pytest.fixture
def auth_user(user_factory):
    """The logged-in user is the server's superuser in these tests.

    Most user endpoints are exercised on *other* people's accounts, which
    only a superuser may change. `test_permissions.py` covers an ordinary
    user.
    """
    return user_factory(password=DEFAULT_PASSWORD, is_superuser=True)
