"""Shared fixtures for the whole backend test suite.

Lives at the repo root (rather than inside a single app) so both
`apps/users/tests/` and `apps/auth/tests/` can use it, per the project's
test layout: unit/api tests live inside each app, but fixtures shared
across apps belong here.
"""

import json
import shutil
import tempfile

from django.test.client import BOUNDARY, encode_multipart
import pytest

from apps.access.tests.factories import RoleFactory
from apps.chat.tests.factories import (
    AttachmentFactory,
    MessageFactory,
    ReactionFactory,
)
from apps.companies.tests.factories import CompanyFactory, CompanyMembershipFactory
from apps.invitations.tests.factories import InvitationFactory
from apps.projects.tests.factories import ProjectFactory, ProjectMembershipFactory
from apps.shots.tests.factories import ShotFactory, ShotGroupFactory, ShotStatusFactory
from apps.tasks.tests.factories import (
    ShotTaskFactory,
    TaskFactory,
    TaskStatusFactory,
    TaskTypeFactory,
)
from apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory
from apps.versions.tests.factories import VersionFactory


@pytest.fixture(autouse=True)
def _tmp_media_root(settings):
    """Redirect MEDIA_ROOT to a throwaway directory for every test.

    Without this, avatar uploads in tests would land in the real
    `media/` folder used by local dev.
    """
    tmp_dir = tempfile.mkdtemp(prefix="paprika-test-media-")
    settings.MEDIA_ROOT = tmp_dir
    yield
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(autouse=True, scope="session")
def _fast_password_hasher():
    """Use a fast, insecure password hasher for the whole test session.

    Tests hash a password on nearly every `UserFactory()` call - real
    deployment settings use a deliberately slow hasher, which adds up
    fast across a full test run. This is a one-line, visible override of
    a single setting for this process only - it doesn't fork the settings
    module the way a separate `settings/test.py` would, so `manage.py`
    and `pytest` still resolve every other setting identically.
    """
    from django.conf import settings as django_settings

    django_settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]


@pytest.fixture
def user_factory():
    """The `UserFactory` class itself, e.g. `user_factory(email=...)`."""
    return UserFactory


@pytest.fixture
def user(user_factory):
    """A single saved user with default field values."""
    return user_factory()


@pytest.fixture
def log_in(client):
    """Log in via the real `/api/v1/auth/login/` endpoint.

    Returns a callable so tests can log in as whichever email/password
    pair they need, e.g. after registering a second user. Tokens are
    never handled directly - a successful login sets them as cookies on
    `client`, which Django's test `Client` then resends automatically on
    every later request from the same fixture instance.
    """

    def _log_in(email: str, password: str) -> dict:
        response = client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return response.json()

    return _log_in


@pytest.fixture
def company_factory():
    """The `CompanyFactory` class itself, e.g. `company_factory(name=...)`."""
    return CompanyFactory


@pytest.fixture
def company(company_factory):
    """A single saved company with default field values."""
    return company_factory()


@pytest.fixture
def company_membership_factory():
    """The `CompanyMembershipFactory` class itself."""
    return CompanyMembershipFactory


@pytest.fixture
def invitation_factory():
    """The `InvitationFactory` class itself, e.g. `invitation_factory(company=...)`."""
    return InvitationFactory


@pytest.fixture
def role_factory():
    """The `RoleFactory` class itself, e.g. `role_factory(company=...)`."""
    return RoleFactory


@pytest.fixture
def project_factory():
    """The `ProjectFactory` class itself, e.g. `project_factory(name=...)`."""
    return ProjectFactory


@pytest.fixture
def project(project_factory):
    """A single saved project with default field values."""
    return project_factory()


@pytest.fixture
def project_membership_factory():
    """The `ProjectMembershipFactory` class itself."""
    return ProjectMembershipFactory


@pytest.fixture
def shot_group_factory():
    """The `ShotGroupFactory` class itself, e.g. `shot_group_factory(name=...)`."""
    return ShotGroupFactory


@pytest.fixture
def shot_group(shot_group_factory):
    """A single saved shot group with default field values."""
    return shot_group_factory()


@pytest.fixture
def shot_status_factory():
    """The `ShotStatusFactory` class itself, e.g. `shot_status_factory(name=...)`."""
    return ShotStatusFactory


@pytest.fixture
def shot_status(shot_status_factory):
    """A single saved shot status with default field values."""
    return shot_status_factory()


@pytest.fixture
def shot_factory():
    """The `ShotFactory` class itself, e.g. `shot_factory(name=...)`."""
    return ShotFactory


@pytest.fixture
def shot(shot_factory):
    """A single saved shot with default field values, no groups."""
    return shot_factory()


@pytest.fixture
def task_type_factory():
    """The `TaskTypeFactory` class itself, e.g. `task_type_factory(name=...)`."""
    return TaskTypeFactory


@pytest.fixture
def task_type(task_type_factory):
    """A single saved task type with default field values."""
    return task_type_factory()


@pytest.fixture
def task_status_factory():
    """The `TaskStatusFactory` class itself, e.g. `task_status_factory(name=...)`."""
    return TaskStatusFactory


@pytest.fixture
def task_status(task_status_factory):
    """A single saved task status with default field values."""
    return task_status_factory()


@pytest.fixture
def task_factory():
    """The `TaskFactory` class itself, e.g. `task_factory(name=...)`."""
    return TaskFactory


@pytest.fixture
def task(task_factory):
    """A single saved standalone task with default field values."""
    return task_factory()


@pytest.fixture
def shot_task_factory():
    """The `ShotTaskFactory` class itself, e.g. `shot_task_factory(shot=...)`."""
    return ShotTaskFactory


@pytest.fixture
def shot_task(shot_task_factory):
    """A single saved task placed on a shot, with default field values."""
    return shot_task_factory()


@pytest.fixture
def version_factory():
    """The `VersionFactory` class itself, e.g. `version_factory(name=...)`."""
    return VersionFactory


@pytest.fixture
def version(version_factory):
    """A single saved image version with default field values."""
    return version_factory()


@pytest.fixture
def message_factory():
    """The `MessageFactory` class itself, e.g. `message_factory(shot=...)`."""
    return MessageFactory


@pytest.fixture
def attachment_factory():
    """The `AttachmentFactory` class itself, e.g. `attachment_factory(shot=...)`."""
    return AttachmentFactory


@pytest.fixture
def reaction_factory():
    """The `ReactionFactory` class itself, e.g. `reaction_factory(message=...)`."""
    return ReactionFactory


@pytest.fixture
def auth_user(user_factory):
    """A user whose raw password is known (`DEFAULT_PASSWORD`), so it can log in."""
    return user_factory(password=DEFAULT_PASSWORD)


@pytest.fixture
def auth_client(auth_user, log_in, client):
    """A Django test client authenticated as `auth_user` via real cookies.

    Obtained through an actual `POST /api/v1/auth/login/` call (not minted
    by hand), so these tests exercise the exact same code path a real
    client would use. The returned client is the same object `log_in`
    used, so the access/refresh cookies set by that call are already
    attached and are resent automatically on every further request.
    """
    log_in(auth_user.email, DEFAULT_PASSWORD)
    return client


@pytest.fixture
def multipart_patch():
    """PATCH helper that reliably sends `multipart/form-data`.

    `Client.patch(path, data={...}, content_type=MULTIPART_CONTENT)` looks
    like it should work but silently drops every field under this stack
    (200 OK, nothing actually changes) - use this instead any time a test
    PATCHes `/users/<id>/`, since that endpoint always expects multipart.
    """

    def _patch(client, path, data):
        body = encode_multipart(BOUNDARY, data)
        return client.generic(
            "PATCH",
            path,
            data=body,
            content_type=f"multipart/form-data; boundary={BOUNDARY}",
        )

    return _patch
