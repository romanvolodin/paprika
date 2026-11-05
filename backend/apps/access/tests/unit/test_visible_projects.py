import pytest

from apps.access.checks import visible_projects
from apps.access.defaults import get_default_role
from apps.companies.models import CompanyMembership
from apps.projects.models import ProjectMembership


pytestmark = pytest.mark.django_db


class TestVisibleProjects:
    def test_each_project_appears_once_however_many_people_are_in_it(
        self, user_factory, company, project_factory
    ):
        me = user_factory()
        others = [user_factory() for _ in range(4)]
        role = get_default_role(company, "executor")
        project = project_factory(company=company)
        for user in [me, *others]:
            CompanyMembership.objects.create(user=user, company=company, role=role)
            ProjectMembership.objects.create(user=user, project=project, role=role)

        assert list(visible_projects(me)) == [project]

    def test_a_company_role_that_sees_everything_adds_the_other_projects(
        self, user_factory, company, project_factory
    ):
        me = user_factory()
        CompanyMembership.objects.create(
            user=me, company=company, role=get_default_role(company, "producer")
        )
        first = project_factory(company=company)
        second = project_factory(company=company)
        ProjectMembership.objects.create(
            user=me, project=first, role=get_default_role(company, "executor")
        )

        assert sorted(p.pk for p in visible_projects(me)) == sorted(
            [first.pk, second.pk]
        )

    def test_projects_of_other_companies_stay_hidden(
        self, user_factory, company, project_factory, company_factory
    ):
        me = user_factory()
        CompanyMembership.objects.create(
            user=me, company=company, role=get_default_role(company, "producer")
        )
        project_factory(company=company_factory())

        assert not visible_projects(me).exists()
