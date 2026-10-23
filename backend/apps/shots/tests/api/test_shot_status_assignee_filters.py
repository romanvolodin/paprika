from http import HTTPStatus

import pytest


pytestmark = pytest.mark.django_db


@pytest.fixture
def member_project(auth_user, project, project_membership_factory):
    project_membership_factory(user=auth_user, project=project)
    return project


def _list_url(project, query=""):
    return f"/api/v1/projects/{project.id}/shots/{query}"


def _ids(response):
    return {item["id"] for item in response.json()["items"]}


class TestFilterShotsByStatus:
    def test_returns_only_shots_with_one_of_the_statuses(
        self, auth_client, member_project, shot_factory, shot_status_factory
    ):
        company = member_project.company
        first = shot_status_factory(company=company)
        second = shot_status_factory(company=company)
        third = shot_status_factory(company=company)
        in_first = shot_factory(project=member_project, status=first)
        in_second = shot_factory(project=member_project, status=second)
        shot_factory(project=member_project, status=third)

        response = auth_client.get(
            _list_url(member_project, f"?status={first.id},{second.id}")
        )

        assert response.status_code == HTTPStatus.OK
        assert _ids(response) == {in_first.id, in_second.id}
        assert response.json()["total"] == 2

    def test_group_list_supports_the_filter_too(
        self,
        auth_client,
        member_project,
        shot_factory,
        shot_group_factory,
        shot_status_factory,
    ):
        wanted = shot_status_factory(company=member_project.company)
        other = shot_status_factory(company=member_project.company)
        group = shot_group_factory(project=member_project)
        match = shot_factory(project=member_project, status=wanted)
        miss = shot_factory(project=member_project, status=other)
        match.groups.add(group)
        miss.groups.add(group)

        response = auth_client.get(
            f"/api/v1/shot-groups/{group.id}/shots/?status={wanted.id}"
        )

        assert _ids(response) == {match.id}

    @pytest.mark.parametrize("raw", ["abc", "1,,x", "0", "-3", "1,none"])
    def test_a_malformed_value_is_rejected(self, auth_client, member_project, raw):
        response = auth_client.get(_list_url(member_project, f"?status={raw}"))

        assert response.status_code == HTTPStatus.BAD_REQUEST


class TestFilterShotsByAssignee:
    def test_returns_shots_with_a_task_assigned_to_any_of_the_users(
        self,
        auth_client,
        member_project,
        user_factory,
        shot_factory,
        task_factory,
        shot_task_factory,
    ):
        anna, boris, clara = user_factory(), user_factory(), user_factory()
        task = task_factory(project=member_project)
        for_anna = shot_factory(project=member_project)
        for_boris = shot_factory(project=member_project)
        for_clara = shot_factory(project=member_project)
        shot_task_factory(shot=for_anna, task=task, assignee=anna)
        shot_task_factory(shot=for_boris, task=task, assignee=boris)
        shot_task_factory(shot=for_clara, task=task, assignee=clara)

        response = auth_client.get(
            _list_url(member_project, f"?assigned_to={anna.id},{boris.id}")
        )

        assert _ids(response) == {for_anna.id, for_boris.id}
        assert response.json()["total"] == 2

    def test_a_shot_with_several_matching_tasks_is_listed_once(
        self,
        auth_client,
        member_project,
        user_factory,
        shot_factory,
        task_factory,
        shot_task_factory,
    ):
        anna = user_factory()
        shot = shot_factory(project=member_project)
        for _ in range(3):
            shot_task_factory(
                shot=shot, task=task_factory(project=member_project), assignee=anna
            )

        body = auth_client.get(
            _list_url(member_project, f"?assigned_to={anna.id}")
        ).json()

        assert [item["id"] for item in body["items"]] == [shot.id]
        assert body["total"] == 1

    def test_none_selects_shots_with_an_unassigned_task(
        self,
        auth_client,
        member_project,
        user_factory,
        shot_factory,
        task_factory,
        shot_task_factory,
    ):
        anna = user_factory()
        task = task_factory(project=member_project)
        unassigned = shot_factory(project=member_project)
        assigned = shot_factory(project=member_project)
        shot_factory(project=member_project)  # no tasks at all
        shot_task_factory(shot=unassigned, task=task, assignee=None)
        shot_task_factory(shot=assigned, task=task, assignee=anna)

        response = auth_client.get(_list_url(member_project, "?assigned_to=none"))

        assert _ids(response) == {unassigned.id}

    def test_none_can_be_mixed_with_users(
        self,
        auth_client,
        member_project,
        user_factory,
        shot_factory,
        task_factory,
        shot_task_factory,
    ):
        anna, boris = user_factory(), user_factory()
        task = task_factory(project=member_project)
        unassigned = shot_factory(project=member_project)
        for_anna = shot_factory(project=member_project)
        for_boris = shot_factory(project=member_project)
        shot_task_factory(shot=unassigned, task=task, assignee=None)
        shot_task_factory(shot=for_anna, task=task, assignee=anna)
        shot_task_factory(shot=for_boris, task=task, assignee=boris)

        response = auth_client.get(
            _list_url(member_project, f"?assigned_to={anna.id},none")
        )

        assert _ids(response) == {unassigned.id, for_anna.id}

    def test_combines_with_the_status_filter(
        self,
        auth_client,
        member_project,
        user_factory,
        shot_factory,
        shot_status_factory,
        task_factory,
        shot_task_factory,
    ):
        anna = user_factory()
        wanted = shot_status_factory(company=member_project.company)
        other = shot_status_factory(company=member_project.company)
        task = task_factory(project=member_project)
        match = shot_factory(project=member_project, status=wanted)
        wrong_status = shot_factory(project=member_project, status=other)
        shot_task_factory(shot=match, task=task, assignee=anna)
        shot_task_factory(shot=wrong_status, task=task, assignee=anna)

        response = auth_client.get(
            _list_url(member_project, f"?status={wanted.id}&assigned_to={anna.id}")
        )

        assert _ids(response) == {match.id}

    def test_group_list_supports_the_filter_too(
        self,
        auth_client,
        member_project,
        user_factory,
        shot_factory,
        shot_group_factory,
        task_factory,
        shot_task_factory,
    ):
        anna = user_factory()
        group = shot_group_factory(project=member_project)
        task = task_factory(project=member_project)
        match = shot_factory(project=member_project)
        miss = shot_factory(project=member_project)
        match.groups.add(group)
        miss.groups.add(group)
        shot_task_factory(shot=match, task=task, assignee=anna)

        response = auth_client.get(
            f"/api/v1/shot-groups/{group.id}/shots/?assigned_to={anna.id}"
        )

        assert _ids(response) == {match.id}

    @pytest.mark.parametrize("raw", ["abc", "1,,x", "0", "-3", "me"])
    def test_a_malformed_value_is_rejected(self, auth_client, member_project, raw):
        response = auth_client.get(_list_url(member_project, f"?assigned_to={raw}"))

        assert response.status_code == HTTPStatus.BAD_REQUEST


class TestShotFilterOptions:
    def _url(self, project):
        return f"/api/v1/projects/{project.id}/shot-filters/"

    def test_lists_only_the_values_that_occur(
        self,
        auth_client,
        member_project,
        user_factory,
        shot_factory,
        shot_status_factory,
        task_factory,
        shot_task_factory,
    ):
        company = member_project.company
        used, also_used = (
            shot_status_factory(company=company),
            shot_status_factory(company=company),
        )
        shot_status_factory(company=company)  # nobody uses it
        anna = user_factory()
        user_factory()  # has no tasks
        task = task_factory(project=member_project)
        first = shot_factory(project=member_project, status=used)
        second = shot_factory(project=member_project, status=also_used)
        shot_factory(project=member_project, status=used)
        shot_task_factory(shot=first, task=task, assignee=anna)
        shot_task_factory(shot=second, task=task, assignee=anna)

        body = auth_client.get(self._url(member_project)).json()

        assert body["status_ids"] == sorted([used.id, also_used.id])
        assert body["assignee_ids"] == [anna.id]
        assert body["has_unassigned"] is False

    def test_reports_an_unassigned_task(
        self,
        auth_client,
        member_project,
        shot_factory,
        task_factory,
        shot_task_factory,
    ):
        shot = shot_factory(project=member_project)
        shot_task_factory(
            shot=shot, task=task_factory(project=member_project), assignee=None
        )

        body = auth_client.get(self._url(member_project)).json()

        assert body["has_unassigned"] is True
        assert body["assignee_ids"] == []

    def test_other_projects_do_not_leak_in(
        self, auth_client, member_project, project_factory, shot_factory
    ):
        shot_factory(project=project_factory())

        body = auth_client.get(self._url(member_project)).json()

        assert body == {"status_ids": [], "assignee_ids": [], "has_unassigned": False}

    def test_not_a_member_gets_404(self, auth_client, project):
        response = auth_client.get(self._url(project))

        assert response.status_code == HTTPStatus.NOT_FOUND
