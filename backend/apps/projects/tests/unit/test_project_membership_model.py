from django.db import IntegrityError
from django.db.models import RestrictedError
import pytest

from apps.projects.models import ProjectMembership


pytestmark = pytest.mark.django_db


class TestProjectMembershipModel:
    def test_str_contains_user_project_and_role(
        self, project_membership_factory, user_factory, project_factory
    ):
        user = user_factory(email="someone@example.com")
        project = project_factory(name="Acme Feature")
        membership = project_membership_factory(
            user=user, project=project, role="admin"
        )

        text = str(membership)

        assert "someone@example.com" in text
        assert "Acme Feature" in text
        assert "Админ" in text

    def test_repr_contains_id_user_id_project_id_and_role(
        self, project_membership_factory
    ):
        membership = project_membership_factory()

        text = repr(membership)

        assert f"id={membership.id}" in text
        assert f"user_id={membership.user_id}" in text
        assert f"project_id={membership.project_id}" in text
        assert f"role_id={membership.role_id}" in text

    def test_role_is_a_role_of_the_projects_company(self, project_membership_factory):
        membership = project_membership_factory(role="executor")

        assert membership.role.company_id == membership.project.company_id
        assert membership.role.name == "Исполнитель"

    def test_a_role_that_is_in_use_cannot_be_deleted(self, project_membership_factory):
        membership = project_membership_factory()

        with pytest.raises(RestrictedError):
            membership.role.delete()

    def test_user_and_project_pair_must_be_unique(
        self, project_membership_factory, user_factory, project_factory
    ):
        user = user_factory()
        project = project_factory()
        project_membership_factory(user=user, project=project)

        with pytest.raises(IntegrityError):
            project_membership_factory(user=user, project=project)

    def test_same_user_can_belong_to_multiple_projects(
        self, project_membership_factory, user_factory, project_factory
    ):
        user = user_factory()
        first_project = project_factory()
        second_project = project_factory()

        project_membership_factory(user=user, project=first_project)
        project_membership_factory(user=user, project=second_project)

        assert user.project_memberships.count() == 2

    def test_project_can_have_multiple_members(
        self, project_membership_factory, project_factory, user_factory
    ):
        project = project_factory()
        first_user = user_factory()
        second_user = user_factory()

        project_membership_factory(user=first_user, project=project)
        project_membership_factory(user=second_user, project=project)

        assert project.memberships.count() == 2

    def test_membership_is_deleted_when_project_is_deleted(
        self, project_membership_factory
    ):
        membership = project_membership_factory()
        membership_id = membership.id
        project = membership.project

        project.delete()

        assert not ProjectMembership.objects.filter(id=membership_id).exists()

    def test_membership_is_deleted_when_user_is_deleted(
        self, project_membership_factory
    ):
        membership = project_membership_factory()
        membership_id = membership.id
        user = membership.user

        user.delete()

        assert not ProjectMembership.objects.filter(id=membership_id).exists()
