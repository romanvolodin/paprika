from datetime import timedelta
import secrets

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


def new_token() -> str:
    return secrets.token_urlsafe(32)


def default_expiry():
    return timezone.now() + timedelta(days=settings.INVITATION_TTL_DAYS)


class Invitation(BaseModel):
    """An invitation to join a company, and optionally some of its projects.

    The invitee follows a link with the secret `token`: they either sign in
    to an account that has the invited email or make one, and accepting
    adds them to the company (with `role`) and to each of `projects`. The
    link is not emailed by the server yet, whoever invites passes it on.
    """

    company = models.ForeignKey(
        "companies.Company",
        verbose_name=_("company"),
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField(_("email"))
    role = models.ForeignKey(
        "access.Role",
        verbose_name=_("role in the company"),
        on_delete=models.RESTRICT,
        related_name="+",
    )
    token = models.CharField(_("token"), max_length=64, unique=True, default=new_token)
    expires_at = models.DateTimeField(_("expires at"), default=default_expiry)
    accepted_at = models.DateTimeField(_("accepted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("invitation")
        verbose_name_plural = _("invitations")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                "company",
                condition=models.Q(accepted_at__isnull=True),
                name="one_open_invitation_per_email_and_company",
            )
        ]

    def __str__(self):
        return f"{self.email} → {self.company}"

    def __repr__(self):
        return f"<Invitation id={self.id} company_id={self.company_id}>"

    @property
    def is_accepted(self) -> bool:
        return self.accepted_at is not None

    @property
    def is_expired(self) -> bool:
        return not self.is_accepted and self.expires_at <= timezone.now()

    def renew(self) -> None:
        """Give the invitation a new link and a fresh term."""
        self.token = new_token()
        self.expires_at = default_expiry()


class InvitationProject(models.Model):
    """A project the invitee joins, with the role they get in it."""

    invitation = models.ForeignKey(
        Invitation,
        verbose_name=_("invitation"),
        on_delete=models.CASCADE,
        related_name="projects",
    )
    project = models.ForeignKey(
        "projects.Project",
        verbose_name=_("project"),
        on_delete=models.CASCADE,
        related_name="+",
    )
    role = models.ForeignKey(
        "access.Role",
        verbose_name=_("role in the project"),
        on_delete=models.RESTRICT,
        related_name="+",
    )

    class Meta:
        verbose_name = _("invited project")
        verbose_name_plural = _("invited projects")
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["invitation", "project"], name="unique_project_per_invitation"
            )
        ]

    def __str__(self):
        return f"{self.invitation_id} → {self.project_id}"
