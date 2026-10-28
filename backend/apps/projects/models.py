from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company
from apps.core.models import BaseModel
from apps.core.storage import file_with_token, project_dir

from .validators import COVER_ALLOWED_EXTENSIONS, validate_cover_size


code_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_-]+$",
    message=_("Code may only contain letters, numbers, hyphens and underscores."),
)


def project_cover_upload_to(instance, filename: str) -> str:
    """`<company token>/<PROJECT>/<name>-<token>.<ext>`.

    The uploaded file's name is kept, with a random token before the
    extension. The token also makes a new cover's URL differ from the old
    one, so browsers don't keep showing the replaced image from their cache.
    """
    return f"{project_dir(instance)}/{file_with_token(filename)}"


class Project(BaseModel):
    """
    A production within a company.

    `code` doubles as the project's public, URL-friendly identifier
    (e.g. `PRJ`). It's set once at creation time and never changes
    afterwards - shots, tasks and versions will derive their own
    public ids from it, so a later rename would break those ids and
    any links built from them.
    """

    company = models.ForeignKey(
        Company,
        verbose_name=_("company"),
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(_("name"), max_length=255)
    code = models.CharField(_("code"), max_length=50, validators=[code_validator])
    description = models.TextField(_("description"), blank=True)
    cover = models.ImageField(
        _("cover"),
        upload_to=project_cover_upload_to,
        max_length=255,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=COVER_ALLOWED_EXTENSIONS),
            validate_cover_size,
        ],
    )
    start_date = models.DateField(_("start date"), null=True, blank=True)
    deadline = models.DateField(_("deadline"), null=True, blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("project")
        verbose_name_plural = _("projects")
        ordering = ["company", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"], name="unique_project_code_per_company"
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def __repr__(self):
        return f"<Project id={self.id} code={self.code} company_id={self.company_id}>"


class ProjectMembership(BaseModel):
    """
    A user's role within a project.

    Access to a project is granted through this model. Belonging to the
    project's company (`CompanyMembership`) is a prerequisite for being
    added here, but does not by itself grant visibility into the project:
    a company member who isn't also a project member can't see it, unless
    their company role has `sees_all_projects`.
    """

    user = models.ForeignKey(
        "users.User",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    project = models.ForeignKey(
        Project,
        verbose_name=_("project"),
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.ForeignKey(
        "access.Role",
        verbose_name=_("role"),
        on_delete=models.RESTRICT,
        related_name="project_memberships",
    )

    class Meta:
        verbose_name = _("project membership")
        verbose_name_plural = _("project memberships")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"], name="unique_project_membership"
            )
        ]
        ordering = ["project", "user"]

    def __str__(self):
        return f"{self.user} — {self.project} ({self.role})"

    def __repr__(self):
        return (
            f"<ProjectMembership id={self.id} user_id={self.user_id} "
            f"project_id={self.project_id} role_id={self.role_id}>"
        )
