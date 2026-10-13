from http import HTTPStatus

from dmr import APIError

from apps.companies.models import Company, CompanyMembership
from apps.users.models import User


def require_company_admin(user: User, company: Company) -> None:
    """Reject company members who are not company admins with a 403.

    Callers have already established that `user` is a member of
    `company` (the `_get_*_or_404` helpers answer 404 to non-members),
    so this only has to look at the role.
    """
    is_admin = CompanyMembership.objects.filter(
        company=company, user=user, role=CompanyMembership.Role.ADMIN
    ).exists()
    if not is_admin:
        raise APIError(
            {"detail": "Only company admins can do this."},
            status_code=HTTPStatus.FORBIDDEN,
        )
