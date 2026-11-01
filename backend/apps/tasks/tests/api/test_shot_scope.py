from http import HTTPStatus
import json

import pytest

from apps.tasks.models import ShotTask


pytestmark = pytest.mark.django_db


@pytest.fixture
def project(project_factory):
    return project_factory()


@pytest.fixture
def mine(project, shot_factory):
    return shot_factory(project=project)


@pytest.fixture
def other(project, shot_factory):
    return shot_factory(project=project)


@pytest.fixture
def freelancer(auth_user, project, mine, project_membership_factory, shot_task_factory):
    project_membership_factory(user=auth_user, project=project, role="freelancer")
    shot_task_factory(shot=mine, assignee=auth_user)
    return auth_user


def _url(shot_task):
    return f"/api/v1/shot-tasks/{shot_task.id}/"


def _patch(client, shot_task, payload):
    return client.patch(
        _url(shot_task), data=json.dumps(payload), content_type="application/json"
    )


class TestShotTaskOfAHiddenShot:
    def test_it_cannot_be_read_changed_or_removed(
        self, auth_client, freelancer, other, shot_task_factory, task_status_factory
    ):
        shot_task = shot_task_factory(shot=other)
        status = task_status_factory(company=other.project.company)

        responses = [
            auth_client.get(_url(shot_task)),
            _patch(auth_client, shot_task, {"status_id": status.id}),
            auth_client.delete(_url(shot_task)),
        ]

        assert {r.status_code for r in responses} == {HTTPStatus.NOT_FOUND}
        assert ShotTask.objects.filter(pk=shot_task.pk).exists()

    def test_it_is_found_once_assigned_to_the_user(
        self, auth_client, freelancer, other, shot_task_factory
    ):
        shot_task = shot_task_factory(shot=other, assignee=freelancer)

        response = auth_client.get(_url(shot_task))

        assert response.status_code == HTTPStatus.OK


class TestShotTaskOfAVisibleShot:
    def test_it_can_be_read(self, auth_client, freelancer, mine, shot_task_factory):
        shot_task = shot_task_factory(shot=mine)

        response = auth_client.get(_url(shot_task))

        assert response.status_code == HTTPStatus.OK

    def test_the_assignee_can_change_its_status(
        self, auth_client, freelancer, mine, shot_task_factory, task_status_factory
    ):
        shot_task = shot_task_factory(shot=mine, assignee=freelancer)
        status = task_status_factory(company=mine.project.company)

        response = _patch(auth_client, shot_task, {"status_id": status.id})

        assert response.status_code == HTTPStatus.OK
        shot_task.refresh_from_db()
        assert shot_task.status_id == status.id


class TestRoleThatSeesEverything:
    def test_it_reaches_the_task_of_any_shot(
        self,
        auth_client,
        auth_user,
        project,
        other,
        shot_task_factory,
        project_membership_factory,
    ):
        project_membership_factory(user=auth_user, project=project, role="executor")
        shot_task = shot_task_factory(shot=other)

        response = auth_client.get(_url(shot_task))

        assert response.status_code == HTTPStatus.OK
