from http import HTTPStatus

import pytest


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
def freelancer(auth_user, project, mine, project_membership_factory):
    project_membership_factory(user=auth_user, project=project, role="freelancer")
    return auth_user


@pytest.fixture
def my_task(project, mine, other, auth_user, task_factory, shot_task_factory):
    task = task_factory(project=project, name="Замена неба")
    shot_task_factory(task=task, shot=mine, assignee=auth_user)
    shot_task_factory(task=task, shot=other)
    return task


@pytest.fixture
def foreign_task(project, other, task_factory, shot_task_factory):
    task = task_factory(project=project, name="Чужая")
    shot_task_factory(task=task, shot=other)
    return task


def _list(client, project, **query):
    return client.get(f"/api/v1/projects/{project.id}/tasks/", query)


class TestTaskList:
    def test_only_the_assigned_tasks_are_listed(
        self, auth_client, freelancer, project, my_task, foreign_task
    ):
        response = _list(auth_client, project)

        assert response.status_code == HTTPStatus.OK
        assert [t["id"] for t in response.json()["items"]] == [my_task.id]
        assert response.json()["total"] == 1

    def test_the_shots_of_a_task_are_limited_to_the_visible_ones(
        self, auth_client, freelancer, project, my_task, mine
    ):
        task = _list(auth_client, project).json()["items"][0]

        assert task["shot_ids"] == [mine.id]

    def test_search_does_not_find_a_hidden_task(
        self, auth_client, freelancer, project, my_task, foreign_task
    ):
        response = _list(auth_client, project, search="Чужая")

        assert response.json()["total"] == 0

    def test_a_standalone_task_is_not_listed(
        self, auth_client, freelancer, project, my_task, task_factory
    ):
        task_factory(project=project, name="Финальные титры")

        assert _list(auth_client, project).json()["total"] == 1

    def test_without_assignments_the_list_is_empty(
        self, auth_client, freelancer, project, foreign_task
    ):
        response = _list(auth_client, project)

        assert response.status_code == HTTPStatus.OK
        assert response.json()["items"] == []

    @pytest.mark.parametrize("role", ["admin", "producer", "coordinator", "executor"])
    def test_a_role_that_sees_everything_gets_every_task_and_shot(
        self,
        auth_client,
        auth_user,
        project,
        my_task,
        foreign_task,
        mine,
        other,
        project_membership_factory,
        role,
    ):
        project_membership_factory(user=auth_user, project=project, role=role)

        body = _list(auth_client, project).json()

        assert body["total"] == 2
        shown = {t["id"]: t["shot_ids"] for t in body["items"]}
        assert sorted(shown[my_task.id]) == sorted([mine.id, other.id])


class TestTaskDetail:
    def test_an_assigned_task_opens(self, auth_client, freelancer, my_task, mine):
        response = auth_client.get(f"/api/v1/tasks/{my_task.id}/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["shot_ids"] == [mine.id]

    def test_a_hidden_task_is_not_found(self, auth_client, freelancer, foreign_task):
        url = f"/api/v1/tasks/{foreign_task.id}/"

        assert auth_client.get(url).status_code == HTTPStatus.NOT_FOUND
        assert auth_client.delete(url).status_code == HTTPStatus.NOT_FOUND


class TestTasksOnTheShotPage:
    def test_the_shots_of_a_task_on_my_shot_are_limited_too(
        self, auth_client, freelancer, my_task, mine
    ):
        response = auth_client.get(f"/api/v1/shots/{mine.id}/tasks/")

        assert response.status_code == HTTPStatus.OK
        (item,) = response.json()["items"]
        assert item["task"]["shot_ids"] == [mine.id]
