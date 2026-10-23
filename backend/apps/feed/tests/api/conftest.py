import datetime as dt

import pytest


@pytest.fixture
def project(auth_user, project_factory, project_membership_factory):
    """A project the logged-in user belongs to (default role)."""
    project = project_factory()
    project_membership_factory(user=auth_user, project=project)
    return project


@pytest.fixture
def at():
    """Moves a saved event to a given time (`created_at` is automatic)."""

    def _at(row, when: dt.datetime):
        type(row).objects.filter(pk=row.pk).update(created_at=when)
        row.created_at = when
        return row

    return _at
