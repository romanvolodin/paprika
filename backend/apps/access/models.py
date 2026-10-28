from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message=_("Color must be a hex value like #RRGGBB."),
)


class Role(BaseModel):
    """A named set of permissions that a company hands out to its people.

    Roles belong to a company and are shared by all of its projects: the
    role of a `CompanyMembership` decides what the person can do in the
    company, the role of a `ProjectMembership` what they can do in the
    project. A new company gets a starter set (see `permissions.DEFAULT_ROLES`).
    """

    company = models.ForeignKey(
        "companies.Company",
        verbose_name=_("company"),
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(_("name"), max_length=100)
    color = models.CharField(_("color"), max_length=7, validators=[color_validator])
    permissions = models.JSONField(
        _("permissions"),
        default=list,
        blank=True,
        help_text=_("Codes from `apps.access.permissions.PERMISSIONS`."),
    )
    sees_all_projects = models.BooleanField(
        _("sees all projects"),
        default=False,
        help_text=_(
            "Whether a member of the company with this role sees every project "
            "of the company, not only the ones they were added to."
        ),
    )

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["company", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="unique_role_name_per_company"
            )
        ]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Role id={self.id} company_id={self.company_id} name={self.name}>"
