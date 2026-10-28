import factory
from factory.django import DjangoModelFactory

from apps.access.tests.factories import resolve_role
from apps.companies.models import Company, CompanyMembership


class CompanyFactory(DjangoModelFactory):
    """Builds `Company` instances for tests.

    Usage:
        company_factory()                  # saved company, random unique name
        company_factory(name="Acme")       # saved company, given name (slug
                                            # auto-derived unless given too)
        company_factory.build(...)         # unsaved instance (no DB hit)
    """

    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Company {n}")


class CompanyMembershipFactory(DjangoModelFactory):
    """Builds `CompanyMembership` instances for tests.

    Usage:
        company_membership_factory()                       # random user + company
        company_membership_factory(user=user, company=company, role="admin")

    `role` is a `Role` of the company or the key of one of its starter roles
    (`"admin"`, `"producer"`, `"coordinator"`, `"executor"`, `"freelancer"`,
    `"client"`); it defaults to `"admin"`, who can do anything in the company.
    """

    class Meta:
        model = CompanyMembership

    user = factory.SubFactory("apps.users.tests.factories.UserFactory")
    company = factory.SubFactory(CompanyFactory)
    role = "admin"

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        kwargs["role"] = resolve_role(kwargs["role"], kwargs["company"])
        return kwargs
