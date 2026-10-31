from django.db import transaction
from django.utils import timezone

from apps.companies.models import CompanyMembership
from apps.projects.models import ProjectMembership
from apps.users.models import User

from .models import Invitation


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
