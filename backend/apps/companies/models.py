from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.core.storage import TOKEN_LENGTH, make_token


class Company(BaseModel):
    """
    Top-level tenant. Provides data isolation between independent
    organizations within a single installation.
    """

    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255, unique=True, blank=True)
    storage_token = models.CharField(
        _("storage token"),
        max_length=TOKEN_LENGTH,
        unique=True,
        editable=False,
        default=make_token,
        help_text=_(
            "Name of the company's folder in the media storage. Random, "
            "set once at creation and never changed, so the company's real "
            "name doesn't show up in file URLs."
        ),
    )

    class Meta:
        verbose_name = _("company")
        verbose_name_plural = _("companies")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Company id={self.id} slug={self.slug}>"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class CompanyMembership(BaseModel):
    """
    A user's role within a company.

    The role decides what the person can do in the company itself (manage
    its members, roles and statuses, create projects). What they can do
    inside a project comes from their `ProjectMembership`; the company role
    only reaches into projects through `Role.sees_all_projects`.
    """

    user = models.ForeignKey(
        "users.User",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )
    company = models.ForeignKey(
        Company,
        verbose_name=_("company"),
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.ForeignKey(
        "access.Role",
        verbose_name=_("role"),
        on_delete=models.RESTRICT,
        related_name="company_memberships",
    )

    class Meta:
        verbose_name = _("company membership")
        verbose_name_plural = _("company memberships")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"], name="unique_company_membership"
            )
        ]
        ordering = ["company", "user"]

    def __str__(self):
        return f"{self.user} — {self.company} ({self.role})"

    def __repr__(self):
        return (
            f"<CompanyMembership id={self.id} user_id={self.user_id} "
            f"company_id={self.company_id} role_id={self.role_id}>"
        )
