from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company
from apps.core.models import BaseModel
from apps.projects.models import Project


color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message=_("Color must be a 6-digit hex code, e.g. #FF5733."),
)

shot_name_validator = RegexValidator(
    regex=r"\A[^/\s]+\Z",
    message=_("Shot name may not contain slashes or whitespace."),
)


class ShotGroup(BaseModel):
    """
    An arbitrary grouping of shots within a project.

    The grouping criterion is up to the team (sequence, location, asset,
    anything else) - deliberately named "group" rather than "sequence"
    so the name itself doesn't imply order or chronology. Visibility
    follows the parent project's `ProjectMembership`, same as `Project`
    itself - there's no separate membership model for groups.
    """

    project = models.ForeignKey(
        Project,
        verbose_name=_("project"),
        on_delete=models.CASCADE,
        related_name="shot_groups",
    )
    name = models.CharField(_("name"), max_length=255)

    class Meta:
        verbose_name = _("shot group")
        verbose_name_plural = _("shot groups")
        ordering = ["project", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"], name="unique_shot_group_name_per_project"
            )
        ]

    def __str__(self):
        return f"{self.project} — {self.name}"

    def __repr__(self):
        return f"<ShotGroup id={self.id} name={self.name} project_id={self.project_id}>"


class ShotStatus(BaseModel):
    """
    A company-defined status a shot can be in (e.g. "Не начат", "В работе").

    Lives at the company level, not the project level - mirrors the
    plan already agreed for `TaskType` ("lives at the company level...
    so a project template can be created with a predefined set"). A
    studio's vocabulary for shot status is typically stable across its
    projects, and starting simpler here leaves room to add a
    project-level override layer later without reshaping this model.

    `order` is nullable and deliberately *not* unique - it's a sort key
    for the primary, ordered part of a studio's workflow (e.g. "Не
    начат" -> "Отдан"). Statuses with `order=None` are exception/side
    states (e.g. "Отмена", "На паузе") that the frontend renders after a
    separator, sorted some other way (name) rather than by workflow
    position - they deliberately don't participate in the main sequence.

    Exactly one status per company has `is_default=True` at a time -
    enforced in the API layer (setting a new default auto-unsets the
    old one), not a DB constraint, since nothing here is concurrent
    enough to need one. The default status can be deleted like any
    other - see `apps.shots.signals` for how a company starts out with
    a seeded set that includes one.
    """

    company = models.ForeignKey(
        Company,
        verbose_name=_("company"),
        on_delete=models.CASCADE,
        related_name="shot_statuses",
    )
    name = models.CharField(_("name"), max_length=255)
    color = models.CharField(_("color"), max_length=7, validators=[color_validator])
    order = models.IntegerField(
        _("order"),
        null=True,
        blank=True,
        help_text=_(
            "Sort position among the primary workflow statuses. Leave "
            "blank for an exception/side status (e.g. cancelled, on "
            "hold) that isn't part of the main sequence."
        ),
    )
    is_default = models.BooleanField(_("default"), default=False)

    class Meta:
        verbose_name = _("shot status")
        verbose_name_plural = _("shot statuses")
        ordering = ["company", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="unique_shot_status_name_per_company"
            )
        ]

    def __str__(self):
        return f"{self.company} — {self.name}"

    def __repr__(self):
        return (
            f"<ShotStatus id={self.id} name={self.name} "
            f"company_id={self.company_id} is_default={self.is_default}>"
        )


class Shot(BaseModel):
    """
    A single shot within a project.

    Belongs directly to a `Project` (not just transitively through its
    groups) because its name is unique at the project level, not the
    group level - a shot's identity doesn't depend on which group(s) it
    happens to be filed under.

    `groups` is a separate, optional, many-to-many concern: a shot can
    belong to zero, one, or several `ShotGroup`s of the same project
    simultaneously (membership in several groups is a deliberate, real
    use case, not an edge case to guard against). There's no "default"
    or "all" group auto-created for ungrouped shots - ungrouped is
    simply an empty `groups` set, and "every shot in this project" is
    already answered by filtering on `project` directly.

    Like `Project.code`, `name` is set once and never renamed - see
    spec-decisions on the public id scheme (`{project.code}_{shot.name}`).

    `status` is required - every shot always has one, defaulting to its
    company's `ShotStatus.is_default` at creation time if not specified
    explicitly (resolved in the API layer; see `apps.shots.api.views`).
    It uses `on_delete=PROTECT` rather than `SET_NULL`, since null isn't
    a valid state for this field - a status can't be deleted while any
    shot still uses it.
    """

    project = models.ForeignKey(
        Project,
        verbose_name=_("project"),
        on_delete=models.CASCADE,
        related_name="shots",
    )
    groups = models.ManyToManyField(
        ShotGroup,
        verbose_name=_("groups"),
        blank=True,
        related_name="shots",
    )
    status = models.ForeignKey(
        ShotStatus,
        verbose_name=_("status"),
        on_delete=models.PROTECT,
        related_name="shots",
    )
    name = models.CharField(_("name"), max_length=255, validators=[shot_name_validator])
    rec_timecode = models.IntegerField(
        _("record timecode"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Start position of the shot in the edit, in frames."),
    )
    duration = models.IntegerField(
        _("duration"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text=_("Length of the shot, in frames."),
    )

    class Meta:
        verbose_name = _("shot")
        verbose_name_plural = _("shots")
        ordering = ["project", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"], name="unique_shot_name_per_project"
            )
        ]

    def __str__(self):
        return f"{self.project} — {self.name}"

    def __repr__(self):
        return f"<Shot id={self.id} name={self.name} project_id={self.project_id}>"
