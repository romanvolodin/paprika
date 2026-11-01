from http import HTTPStatus

import pytest


pytestmark = pytest.mark.django_db


@pytest.fixture
def project(project_factory):
    return project_factory()


@pytest.fixture
def group(project, shot_group_factory):
    return shot_group_factory(project=project)


@pytest.fixture
def mine(project, group, shot_factory):
    return shot_factory(project=project, name="MINE", groups=[group])


@pytest.fixture
def other(project, group, shot_factory):
    return shot_factory(project=project, name="OTHER", groups=[group])


@pytest.fixture
def freelancer(
    auth_user, project, mine, other, project_membership_factory, shot_task_factory
):
    project_membership_factory(user=auth_user, project=project, role="freelancer")
    shot_task_factory(shot=mine, assignee=auth_user)
    return auth_user


def _names(response):
    return [item["name"] for item in response.json()["items"]]


class TestProjectShotList:
    def test_only_the_assigned_shots_are_listed(self, auth_client, freelancer, project):
        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert response.status_code == HTTPStatus.OK
        assert _names(response) == ["MINE"]
        assert response.json()["total"] == 1

    def test_without_assignments_the_list_is_empty_not_missing(
        self, auth_client, auth_user, project, other, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="freelancer")

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    def test_a_search_does_not_find_a_hidden_shot(
        self, auth_client, freelancer, project
    ):
        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shots/", {"search": "OTHER"}
        )

        assert response.json()["total"] == 0

    def test_an_exact_name_does_not_find_a_hidden_shot(
        self, auth_client, freelancer, project
    ):
        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shots/", {"name": "OTHER"}
        )

        assert response.json()["total"] == 0

    def test_filters_do_not_bring_hidden_shots_back(
        self, auth_client, freelancer, project, other, shot_task_factory, user_factory
    ):
        colleague = user_factory()
        shot_task_factory(shot=other, assignee=colleague)

        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shots/",
            {"assigned_to": str(colleague.id)},
        )

        assert response.json()["total"] == 0

    def test_a_shot_with_several_tasks_is_listed_once(
        self, auth_client, freelancer, project, mine, shot_task_factory
    ):
        shot_task_factory(shot=mine, assignee=freelancer)

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert _names(response) == ["MINE"]
        assert response.json()["total"] == 1

    def test_pages_count_only_visible_shots(
        self, auth_client, freelancer, project, shot_factory, shot_task_factory
    ):
        for index in range(3):
            shot = shot_factory(project=project, name=f"EXTRA{index}")
            shot_task_factory(shot=shot, assignee=freelancer)

        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shots/", {"page_size": 2}
        )

        assert response.json()["total"] == 4
        assert len(response.json()["items"]) == 2

    @pytest.mark.parametrize("role", ["admin", "producer", "coordinator", "executor"])
    def test_a_role_that_sees_everything_gets_every_shot(
        self,
        auth_client,
        auth_user,
        project,
        mine,
        other,
        project_membership_factory,
        role,
    ):
        project_membership_factory(user=auth_user, project=project, role=role)

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert sorted(_names(response)) == ["MINE", "OTHER"]


class TestGroupShotList:
    def test_only_the_assigned_shots_of_the_group_are_listed(
        self, auth_client, freelancer, group
    ):
        response = auth_client.get(f"/api/v1/shot-groups/{group.id}/shots/")

        assert response.status_code == HTTPStatus.OK
        assert _names(response) == ["MINE"]
        assert response.json()["total"] == 1

    def test_a_role_that_sees_everything_gets_the_whole_group(
        self,
        auth_client,
        auth_user,
        project,
        group,
        mine,
        other,
        project_membership_factory,
    ):
        project_membership_factory(user=auth_user, project=project, role="executor")

        response = auth_client.get(f"/api/v1/shot-groups/{group.id}/shots/")

        assert sorted(_names(response)) == ["MINE", "OTHER"]


class TestShotFilterOptions:
    def _url(self, project):
        return f"/api/v1/projects/{project.id}/shot-filters/"

    def test_statuses_come_only_from_visible_shots(
        self, auth_client, freelancer, project, mine, other, shot_status_factory
    ):
        hidden_status = shot_status_factory(company=project.company)
        other.status = hidden_status
        other.save()

        body = auth_client.get(self._url(project)).json()

        assert body["status_ids"] == [mine.status_id]

    def test_assignees_come_only_from_visible_shots(
        self,
        auth_client,
        freelancer,
        project,
        mine,
        other,
        user_factory,
        shot_task_factory,
    ):
        beside_me, elsewhere = user_factory(), user_factory()
        shot_task_factory(shot=mine, assignee=beside_me)
        shot_task_factory(shot=other, assignee=elsewhere)

        body = auth_client.get(self._url(project)).json()

        assert body["assignee_ids"] == sorted([freelancer.id, beside_me.id])

    def test_an_unassigned_task_on_a_hidden_shot_is_not_reported(
        self, auth_client, freelancer, project, other, shot_task_factory
    ):
        shot_task_factory(shot=other, assignee=None)

        body = auth_client.get(self._url(project)).json()

        assert body["has_unassigned"] is False

    def test_an_unassigned_task_on_a_visible_shot_is_reported(
        self, auth_client, freelancer, project, mine, shot_task_factory
    ):
        shot_task_factory(shot=mine, assignee=None)

        body = auth_client.get(self._url(project)).json()

        assert body["has_unassigned"] is True

    def test_without_assignments_nothing_is_offered(
        self, auth_client, auth_user, project, other, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="freelancer")

        body = auth_client.get(self._url(project)).json()

        assert body == {"status_ids": [], "assignee_ids": [], "has_unassigned": False}

    def test_a_role_that_sees_everything_gets_every_value(
        self,
        auth_client,
        auth_user,
        project,
        mine,
        other,
        user_factory,
        shot_task_factory,
        project_membership_factory,
    ):
        project_membership_factory(user=auth_user, project=project, role="executor")
        elsewhere = user_factory()
        shot_task_factory(shot=other, assignee=elsewhere)

        body = auth_client.get(self._url(project)).json()

        assert body["assignee_ids"] == [elsewhere.id]
