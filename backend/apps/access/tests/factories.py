import factory
from factory.django import DjangoModelFactory

from apps.access.defaults import get_default_role
from apps.access.models import Role


def resolve_role(role, company):
    """A `Role` as is; a starter role key (`"admin"`) looked up in the company."""
    if isinstance(role, str):
        return get_default_role(company, role)
    return role


class RoleFactory(DjangoModelFactory):
    """Builds `Role` instances for tests.

    Note a new `Company` already comes with the starter roles (see
    `apps.access.signals`); this factory adds one more.

    Usage:
        role_factory(company=company, name="Старший исполнитель")
        role_factory(company=company, permissions=["shot.create"])
    """

    class Meta:
        model = Role

    company = factory.SubFactory("apps.companies.tests.factories.CompanyFactory")
    name = factory.Sequence(lambda n: f"Role {n}")
    color = "#FF5733"
    permissions = factory.LazyFunction(list)
    sees_all_projects = False
