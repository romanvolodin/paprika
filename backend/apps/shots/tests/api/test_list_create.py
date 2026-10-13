from http import HTTPStatus
import json

import pytest

from apps.shots.models import ShotGroup


pytestmark = pytest.mark.django_db


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


class TestListShotGroups:
    def test_returns_shot_groups_for_a_project_the_user_is_a_member_of(
        self,
        auth_client,
        auth_user,
        project_factory,
        project_membership_factory,
        shot_group_factory,
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)
        shot_group_factory(project=project, name="Int. Office")

        response = auth_client.get(f"/api/v1/projects/{project.id}/shot-groups/")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Int. Office"

    def test_search_filters_by_name(
        self,
        auth_client,
        auth_user,
        project_factory,
        project_membership_factory,
        shot_group_factory,
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project)
        shot_group_factory(project=project, name="Findable Group")
        shot_group_factory(project=project, name="Other Group")

        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shot-groups/?search=findable"
        )

        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Findable Group"

    def test_non_member_of_project_gets_404(
        self, auth_client, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(project=project)  # some other user

        response = auth_client.get(f"/api/v1/projects/{project.id}/shot-groups/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project):
        response = client.get(f"/api/v1/projects/{project.id}/shot-groups/")

        assert response.status_code == 401


class TestCreateShotGroup:
    def test_creates_a_shot_group(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shot-groups/",
            {"name": "Int. Office"},
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["name"] == "Int. Office"
        assert body["project_id"] == project.id
        assert ShotGroup.objects.filter(project=project, name="Int. Office").exists()

    def test_response_includes_created_by_and_updated_by(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shot-groups/",
            {"name": "Int. Office"},
        )

        body = response.json()
        assert body["created_by"]["id"] == auth_user.id
        assert body["updated_by"]["id"] == auth_user.id

    def test_rejects_duplicate_name_within_project(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_group_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot_group_factory(project=project, name="Int. Office")

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shot-groups/",
            {"name": "Int. Office"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_same_name_allowed_in_a_different_project(
        self,
        auth_client,
        auth_user,
        project_factory,
        project_membership_factory,
        shot_group_factory,
    ):
        other_project = project_factory()
        shot_group_factory(project=other_project, name="Int. Office")
        my_project = project_factory()
        project_membership_factory(user=auth_user, project=my_project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{my_project.id}/shot-groups/",
            {"name": "Int. Office"},
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_rejects_blank_name(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shot-groups/",
            {"name": ""},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_of_project_gets_404(
        self, auth_client, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(project=project)  # some other user

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shot-groups/",
            {"name": "Int. Office"},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project):
        response = _post_json(
            client,
            f"/api/v1/projects/{project.id}/shot-groups/",
            {"name": "Int. Office"},
        )

        assert response.status_code == 401


class TestClientRoleCannotCreateShotGroups:
    def test_client_can_list_but_not_create(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="client")

        listed = auth_client.get(f"/api/v1/projects/{project.id}/shot-groups/")
        created = _post_json(
            auth_client, f"/api/v1/projects/{project.id}/shot-groups/", {"name": "Int"}
        )

        assert listed.status_code == HTTPStatus.OK
        assert created.status_code == HTTPStatus.FORBIDDEN
        assert not ShotGroup.objects.filter(project=project).exists()
