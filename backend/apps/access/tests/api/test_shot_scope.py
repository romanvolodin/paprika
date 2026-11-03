from http import HTTPStatus
import json

import pytest

from apps.access.defaults import get_default_role
from apps.shots.models import Shot


pytestmark = pytest.mark.django_db


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


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
def freelancer(auth_user, project, project_membership_factory):
    project_membership_factory(user=auth_user, project=project, role="freelancer")
    return auth_user


@pytest.fixture
def assigned(freelancer, mine, shot_task_factory):
    return shot_task_factory(shot=mine, assignee=freelancer)


def _every_address(shot):
    return [
        ("get", f"/api/v1/shots/{shot.id}/"),
        ("get", f"/api/v1/shots/{shot.id}/versions/"),
        ("get", f"/api/v1/shots/{shot.id}/chat/"),
        ("get", f"/api/v1/shots/{shot.id}/tasks/"),
    ]


class TestShotsOfARoleLimitedToAssigned:
    def test_a_shot_without_an_assigned_task_is_not_found(
        self, auth_client, freelancer, other
    ):
        for method, url in _every_address(other):
            assert (
                getattr(auth_client, method)(url).status_code == HTTPStatus.NOT_FOUND
            ), url

    def test_a_shot_with_an_assigned_task_is_shown(self, auth_client, assigned, mine):
        for method, url in _every_address(mine):
            assert getattr(auth_client, method)(url).status_code == HTTPStatus.OK, url

    def test_the_shot_stays_hidden_while_only_someone_else_is_assigned(
        self, auth_client, freelancer, other, shot_task_factory, user_factory
    ):
        shot_task_factory(shot=other, assignee=user_factory())

        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_taking_the_task_off_hides_the_shot_again(
        self, auth_client, assigned, mine
    ):
        assigned.assignee = None
        assigned.save()

        response = auth_client.get(f"/api/v1/shots/{mine.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_a_hidden_shot_cannot_be_changed_or_deleted(
        self, auth_client, auth_user, project, other, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="freelancer")

        patched = auth_client.patch(
            f"/api/v1/shots/{other.id}/",
            data=json.dumps({"description": "x"}),
            content_type="application/json",
        )
        deleted = auth_client.delete(f"/api/v1/shots/{other.id}/")

        assert patched.status_code == HTTPStatus.NOT_FOUND
        assert deleted.status_code == HTTPStatus.NOT_FOUND
        assert Shot.objects.filter(pk=other.pk).exists()

    def test_a_hidden_shot_takes_no_task_version_or_message(
        self, auth_client, freelancer, other, task_factory, project
    ):
        task = task_factory(project=project)

        placed = _post(
            auth_client, f"/api/v1/shots/{other.id}/tasks/", {"task_id": task.id}
        )
        written = _post(auth_client, f"/api/v1/shots/{other.id}/chat/", {"text": "hi"})

        assert placed.status_code == HTTPStatus.NOT_FOUND
        assert written.status_code == HTTPStatus.NOT_FOUND

    def test_a_custom_role_can_be_limited_too(
        self,
        auth_client,
        auth_user,
        project,
        other,
        role_factory,
        project_membership_factory,
    ):
        role = role_factory(company=project.company, sees_all_shots=False)
        project_membership_factory(user=auth_user, project=project, role=role)

        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestShotsOfARoleThatSeesAll:
    @pytest.mark.parametrize(
        "role", ["admin", "producer", "coordinator", "executor", "client"]
    )
    def test_the_starter_roles_see_every_shot(
        self, auth_client, auth_user, project, other, project_membership_factory, role
    ):
        project_membership_factory(user=auth_user, project=project, role=role)

        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_a_custom_role_can_be_widened(
        self,
        auth_client,
        auth_user,
        project,
        other,
        role_factory,
        project_membership_factory,
    ):
        role = role_factory(company=project.company, sees_all_shots=True)
        project_membership_factory(user=auth_user, project=project, role=role)

        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_a_superuser_sees_every_shot(self, auth_client, auth_user, other):
        auth_user.is_superuser = True
        auth_user.save()

        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_a_stranger_still_gets_a_404(self, auth_client, other):
        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCompanyRoleAndProjectRole:
    def test_the_company_role_that_sees_everything_reaches_every_shot(
        self, auth_client, auth_user, project, other, company_membership_factory
    ):
        company_membership_factory(
            user=auth_user, company=project.company, role="producer"
        )

        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_a_wide_company_role_limited_to_assigned_shots_sees_only_those(
        self,
        auth_client,
        auth_user,
        project,
        mine,
        other,
        role_factory,
        company_membership_factory,
        shot_task_factory,
    ):
        role = role_factory(
            company=project.company, sees_all_projects=True, sees_all_shots=False
        )
        company_membership_factory(user=auth_user, company=project.company, role=role)
        shot_task_factory(shot=mine, assignee=auth_user)

        assert auth_client.get(f"/api/v1/shots/{mine.id}/").status_code == HTTPStatus.OK
        assert (
            auth_client.get(f"/api/v1/shots/{other.id}/").status_code
            == HTTPStatus.NOT_FOUND
        )

    def test_a_company_role_that_sees_everything_still_counts_in_a_project(
        self,
        auth_client,
        auth_user,
        project,
        other,
        company_membership_factory,
        project_membership_factory,
    ):
        company_membership_factory(
            user=auth_user, company=project.company, role="admin"
        )
        project_membership_factory(user=auth_user, project=project, role="freelancer")

        response = auth_client.get(f"/api/v1/shots/{other.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_an_assignment_without_membership_shows_nothing(
        self, auth_client, auth_user, mine, shot_task_factory
    ):
        shot_task_factory(shot=mine, assignee=auth_user)

        response = auth_client.get(f"/api/v1/shots/{mine.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestMySeesAllShots:
    def test_a_limited_role_is_told_so(
        self, auth_client, auth_user, freelancer, project, company_membership_factory
    ):
        company_membership_factory(
            user=auth_user, company=project.company, role="freelancer"
        )
        detail = auth_client.get(f"/api/v1/projects/{project.id}/")
        listed = auth_client.get(f"/api/v1/companies/{project.company_id}/projects/")

        assert detail.json()["my_sees_all_shots"] is False
        assert listed.json()["items"][0]["my_sees_all_shots"] is False

    def test_a_wide_role_is_told_so(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        company_membership_factory,
    ):
        company_membership_factory(
            user=auth_user, company=project.company, role="executor"
        )
        project_membership_factory(user=auth_user, project=project, role="executor")

        detail = auth_client.get(f"/api/v1/projects/{project.id}/")
        listed = auth_client.get(f"/api/v1/companies/{project.company_id}/projects/")

        assert detail.json()["my_sees_all_shots"] is True
        assert listed.json()["items"][0]["my_sees_all_shots"] is True


class TestGrantingTheScope:
    @pytest.fixture
    def limited_manager(
        self, auth_user, project, role_factory, project_membership_factory
    ):
        role = role_factory(
            company=project.company,
            permissions=[
                "project.members",
                "feed.view",
                "task.update_own",
                "version.upload",
                "version.delete_own",
                "chat.write",
            ],
            sees_all_shots=False,
        )
        project_membership_factory(user=auth_user, project=project, role=role)
        return auth_user

    def test_a_limited_manager_cannot_give_a_role_that_sees_all_shots(
        self, auth_client, limited_manager, project, company_membership_factory
    ):
        member = company_membership_factory(company=project.company)
        executor_id = get_default_role(project.company, "executor").id

        response = _post(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": member.user_id, "role_id": executor_id},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_a_limited_manager_can_give_a_limited_role(
        self, auth_client, limited_manager, project, company_membership_factory
    ):
        member = company_membership_factory(company=project.company)
        freelancer_id = get_default_role(project.company, "freelancer").id

        response = _post(
            auth_client,
            f"/api/v1/projects/{project.id}/members/",
            {"user_id": member.user_id, "role_id": freelancer_id},
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_a_company_role_limited_in_shots_cannot_give_a_wide_one(
        self, auth_client, auth_user, company, role_factory, company_membership_factory
    ):
        role = role_factory(
            company=company,
            permissions=["company.members"],
            sees_all_projects=True,
            sees_all_shots=False,
        )
        company_membership_factory(user=auth_user, company=company, role=role)
        wide = role_factory(company=company, sees_all_projects=True)
        narrow = role_factory(
            company=company, sees_all_projects=True, sees_all_shots=False
        )
        path = f"/api/v1/companies/{company.id}/invitations/"

        refused = _post(auth_client, path, _new_person("a@example.com", wide.id))
        allowed = _post(auth_client, path, _new_person("b@example.com", narrow.id))

        assert refused.status_code == HTTPStatus.FORBIDDEN
        assert allowed.status_code == HTTPStatus.CREATED


def _new_person(email, role_id):
    return {"email": email, "role_id": role_id}


class TestProjectMemberList:
    @pytest.fixture
    def crew(self, project, user_factory, project_membership_factory):
        people = {name: user_factory() for name in ("beside_me", "elsewhere", "idle")}
        for person in people.values():
            project_membership_factory(user=person, project=project, role="executor")
        return people

    def _ids(self, client, project):
        response = client.get(f"/api/v1/projects/{project.id}/members/")
        assert response.status_code == HTTPStatus.OK
        return {item["user_id"] for item in response.json()["items"]}

    def test_a_limited_role_sees_itself_and_the_colleagues_on_its_shots(
        self, auth_client, assigned, project, mine, other, crew, shot_task_factory
    ):
        shot_task_factory(shot=mine, assignee=crew["beside_me"])
        shot_task_factory(shot=other, assignee=crew["elsewhere"])

        ids = self._ids(auth_client, project)

        assert ids == {assigned.assignee_id, crew["beside_me"].id}

    def test_without_assignments_only_the_user_themselves_is_listed(
        self, auth_client, auth_user, project, crew, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="freelancer")

        assert self._ids(auth_client, project) == {auth_user.id}

    def test_a_role_that_sees_everything_gets_every_member(
        self, auth_client, auth_user, project, crew, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="executor")

        ids = self._ids(auth_client, project)

        assert ids == {auth_user.id, *(person.id for person in crew.values())}
