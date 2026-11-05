from django.core.exceptions import ValidationError
import pytest

from apps.access.defaults import get_default_role
from apps.companies.models import CompanyMembership
from apps.projects.models import ProjectMembership


pytestmark = pytest.mark.django_db


class TestRoleBelongsToTheSameCompany:
    def test_company_membership_rejects_a_role_of_another_company(
        self, user_factory, company, company_factory
    ):
        foreign_role = get_default_role(company_factory(), "admin")

        with pytest.raises(ValidationError):
            CompanyMembership.objects.create(
                user=user_factory(), company=company, role=foreign_role
            )

        assert not CompanyMembership.objects.exists()

    def test_company_membership_accepts_a_role_of_its_company(
        self, user_factory, company
    ):
        membership = CompanyMembership.objects.create(
            user=user_factory(),
            company=company,
            role=get_default_role(company, "admin"),
        )

        assert membership.pk is not None

    def test_project_membership_rejects_a_role_of_another_company(
        self, user_factory, project_factory, company, company_factory
    ):
        project = project_factory(company=company)
        foreign_role = get_default_role(company_factory(), "executor")

        with pytest.raises(ValidationError):
            ProjectMembership.objects.create(
                user=user_factory(), project=project, role=foreign_role
            )

        assert not ProjectMembership.objects.exists()

    def test_project_membership_accepts_a_role_of_the_projects_company(
        self, user_factory, project_factory, company
    ):
        project = project_factory(company=company)

        membership = ProjectMembership.objects.create(
            user=user_factory(),
            project=project,
            role=get_default_role(company, "executor"),
        )

        assert membership.pk is not None
