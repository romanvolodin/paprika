from http import HTTPStatus

import pytest

from apps.versions.models import Version


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


class TestVersionOfAHiddenShot:
    def test_it_cannot_be_opened(self, auth_client, freelancer, other, version_factory):
        version = version_factory(shot=other)

        response = auth_client.get(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_it_cannot_be_deleted_even_by_its_author(
        self, auth_client, freelancer, other, version_factory
    ):
        version = version_factory(shot=other, created_by=freelancer)

        response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Version.objects.filter(pk=version.pk).exists()

    def test_it_is_found_again_once_a_task_is_assigned(
        self, auth_client, freelancer, other, version_factory, shot_task_factory
    ):
        version = version_factory(shot=other)
        shot_task_factory(shot=other, assignee=freelancer)

        response = auth_client.get(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.OK


class TestVersionOfAVisibleShot:
    def test_it_can_be_opened(self, auth_client, freelancer, mine, version_factory):
        version = version_factory(shot=mine)

        response = auth_client.get(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.OK

    def test_its_author_can_delete_it(
        self, auth_client, freelancer, mine, version_factory
    ):
        version = version_factory(shot=mine, created_by=freelancer)

        response = auth_client.delete(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Version.objects.filter(pk=version.pk).exists()


class TestRoleThatSeesEverything:
    def test_it_opens_the_version_of_any_shot(
        self,
        auth_client,
        auth_user,
        project,
        other,
        version_factory,
        project_membership_factory,
    ):
        project_membership_factory(user=auth_user, project=project, role="executor")
        version = version_factory(shot=other)

        response = auth_client.get(f"/api/v1/versions/{version.id}/")

        assert response.status_code == HTTPStatus.OK
