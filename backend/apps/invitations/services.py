from django.db import transaction
from django.utils import timezone

from apps.access.checks import (
    can_grant_company_role,
    can_grant_project_role,
    company_permissions,
    project_permissions,
)
from apps.access.permissions import P
from apps.companies.models import CompanyMembership
from apps.projects.models import ProjectMembership
from apps.users.models import User

from .models import Invitation


def inviter_can_still_give_access(invitation: Invitation) -> bool:
    """Whether the person who sent the invitation could send it right now."""
    inviter = invitation.created_by
    if inviter is None or not inviter.is_active:
        return False
    company = invitation.company
    if (
        not inviter.is_superuser
        and not CompanyMembership.objects.filter(user=inviter, company=company).exists()
    ):
        return False
    invited = list(invitation.projects.select_related("project", "role"))
    if not inviter.is_superuser:
        may_invite_to_company = P.COMPANY_MEMBERS in company_permissions(
            inviter, company
        )
        may_invite_to_projects = bool(invited) and all(
            P.PROJECT_MEMBERS in project_permissions(inviter, item.project)
            for item in invited
        )
        if not (may_invite_to_company or may_invite_to_projects):
            return False
    if not can_grant_company_role(inviter, company, invitation.role):
        return False
    return all(
        can_grant_project_role(inviter, item.project, item.role) for item in invited
    )


@transaction.atomic
def accept_invitation(invitation: Invitation, user: User) -> None:
    """Put `user` into the company and projects the invitation names.

    Someone who is already in the company or a project keeps the role they
    have there: an invitation never changes an existing role.
    """
    CompanyMembership.objects.get_or_create(
        user=user,
        company=invitation.company,
        defaults={
            "role": invitation.role,
            "created_by": invitation.created_by,
            "updated_by": invitation.created_by,
        },
    )
    for invited in invitation.projects.select_related("project"):
        ProjectMembership.objects.get_or_create(
            user=user,
            project=invited.project,
            defaults={
                "role": invited.role,
                "created_by": invitation.created_by,
                "updated_by": invitation.created_by,
            },
        )
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at", "updated_at"])
