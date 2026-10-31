import factory
from factory.django import DjangoModelFactory

from apps.access.tests.factories import resolve_role
from apps.invitations.models import Invitation


class InvitationFactory(DjangoModelFactory):
    """Builds `Invitation` instances for tests.

    `role` is a `Role` of the company or the key of a starter role
    (`"executor"` by default). The token and the term come from the model.

    Usage:
        invitation_factory(company=company, email="new@example.com")
        invitation_factory(company=company, role="freelancer")
    """

    class Meta:
        model = Invitation

    company = factory.SubFactory("apps.companies.tests.factories.CompanyFactory")
    email = factory.Sequence(lambda n: f"invited{n}@example.com")
    role = "executor"

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        kwargs["role"] = resolve_role(kwargs["role"], kwargs["company"])
        return kwargs
