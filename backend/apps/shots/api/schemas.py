import datetime as dt
import re

import pydantic

from apps.users.api.schemas import UserOut


SHOT_NAME_PATTERN = re.compile(r"\A[^/\s]+\Z")


class ShotGroupOut(pydantic.BaseModel):
    """Public representation of a shot group."""

    id: int = pydantic.Field(description="Internal numeric shot group identifier.")
    project_id: int
    name: str = pydantic.Field(description="Shot group name.")
    created_by: UserOut | None = pydantic.Field(
        description="The user who created the shot group, or null if that "
        "user has since been deleted."
    )
    updated_by: UserOut | None = pydantic.Field(
        description="The user who last updated the shot group, or null if "
        "that user has since been deleted."
    )
    created_at: dt.datetime
    updated_at: dt.datetime


class ShotGroupListQuery(pydantic.BaseModel):
    """Pagination and search params for `GET /api/v1/projects/<id>/shot-groups/`."""

    page: int = pydantic.Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = pydantic.Field(
        default=20,
        ge=1,
        le=100,
        description="Number of shot groups per page.",
    )
    search: str | None = pydantic.Field(
        default=None,
        description="Case-insensitive match against the shot group name.",
    )


class ShotGroupListOut(pydantic.BaseModel):
    """A page of shot groups within a project."""

    items: list[ShotGroupOut]
    total: int = pydantic.Field(
        description="Total number of shot groups matching filters."
    )
    page: int
    page_size: int


class ProjectShotGroupsPath(pydantic.BaseModel):
    """URL path parameters identifying a project's shot groups collection."""

    project_id: int = pydantic.Field(gt=0)


class ShotGroupPath(pydantic.BaseModel):
    """URL path parameters identifying a single shot group."""

    shot_group_id: int = pydantic.Field(gt=0)


class ShotGroupCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/projects/<project_id>/shot-groups/`."""

    name: str = pydantic.Field(min_length=1, max_length=255)


class ShotGroupUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/shot-groups/<id>/`.

    `name` is the only field there is, so unlike `ProjectUpdateIn` this
    isn't a partial-update schema - it's always required.
    """

    name: str = pydantic.Field(min_length=1, max_length=255)


class ShotStatusOut(pydantic.BaseModel):
    """Public representation of a shot status."""

    id: int = pydantic.Field(description="Internal numeric shot status identifier.")
    company_id: int
    name: str = pydantic.Field(description="Shot status name.")
    color: str = pydantic.Field(description="6-digit hex color, e.g. #FF5733.")
    order: int | None = pydantic.Field(
        description=(
            "Sort position among the primary workflow statuses, or null "
            "for an exception/side status (e.g. cancelled, on hold)."
        )
    )
    is_default: bool = pydantic.Field(
        description="Whether new shots get this status when none is specified."
    )
    created_by: UserOut | None = pydantic.Field(
        description="The user who created the status, or null if that user "
        "has since been deleted."
    )
    updated_by: UserOut | None = pydantic.Field(
        description="The user who last updated the status, or null if that "
        "user has since been deleted."
    )
    created_at: dt.datetime
    updated_at: dt.datetime


class ShotStatusListQuery(pydantic.BaseModel):
    """Query params for `GET /api/v1/companies/<id>/shot-statuses/`.

    No pagination - a company's shot statuses are a short, bounded
    list, same reasoning as `TaskType`.
    """

    search: str | None = pydantic.Field(
        default=None,
        description="Case-insensitive match against the status name.",
    )


class ShotStatusListOut(pydantic.BaseModel):
    """The full list of a company's shot statuses (not paginated)."""

    items: list[ShotStatusOut]


class CompanyShotStatusesPath(pydantic.BaseModel):
    """URL path parameters identifying a company's shot statuses collection."""

    company_id: int = pydantic.Field(gt=0)


class ShotStatusPath(pydantic.BaseModel):
    """URL path parameters identifying a single shot status."""

    shot_status_id: int = pydantic.Field(gt=0)


class ShotStatusCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/companies/<company_id>/shot-statuses/`.

    `order` left unset means this status is an exception/side state,
    not part of the primary ordered workflow - see `ShotStatus.order`.
    Setting `is_default=True` automatically unsets the company's
    previous default (there's always at most one).
    """

    name: str = pydantic.Field(min_length=1, max_length=255)
    color: str = pydantic.Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    order: int | None = None
    is_default: bool = False


class ShotStatusUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/shot-statuses/<id>/`. All fields optional."""

    name: str | None = pydantic.Field(default=None, min_length=1, max_length=255)
    color: str | None = pydantic.Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    order: int | None = None
    is_default: bool | None = None


class ShotOut(pydantic.BaseModel):
    """Public representation of a shot."""

    id: int = pydantic.Field(description="Internal numeric shot identifier.")
    project_id: int
    group_ids: list[int] = pydantic.Field(
        description="Ids of the shot groups this shot belongs to. May be empty."
    )
    status_id: int = pydantic.Field(description="Id of the shot's current status.")
    name: str = pydantic.Field(description="Shot name. Immutable once set.")
    rec_timecode: int | None = pydantic.Field(
        description="Start position of the shot in the edit, in frames."
    )
    duration: int | None = pydantic.Field(description="Length of the shot, in frames.")
    thumb: str | None = pydantic.Field(
        default=None,
        description="Absolute URL of the thumbnail of the shot's latest version, "
        "or null if the shot has no versions.",
    )
    created_by: UserOut | None = pydantic.Field(
        description="The user who created the shot, or null if that user "
        "has since been deleted."
    )
    updated_by: UserOut | None = pydantic.Field(
        description="The user who last updated the shot, or null if that "
        "user has since been deleted."
    )
    created_at: dt.datetime
    updated_at: dt.datetime


class ShotListQuery(pydantic.BaseModel):
    """Pagination and search params shared by both shot list endpoints
    (project- and group-scoped).
    """

    page: int = pydantic.Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = pydantic.Field(
        default=20,
        ge=1,
        le=500,
        description="Number of shots per page.",
    )
    search: str | None = pydantic.Field(
        default=None,
        description="Case-insensitive match against the shot name.",
    )
    name: str | None = pydantic.Field(
        default=None,
        description="Exact (case-sensitive) match against the shot name.",
    )
    task_type: int | None = pydantic.Field(
        default=None,
        description="Only shots that have at least one task of the task "
        "type with this id.",
    )
    status: str | None = pydantic.Field(
        default=None,
        description="Comma-separated shot status ids, e.g. `3,5`: only shots "
        "whose status is one of them.",
    )
    assigned_to: str | None = pydantic.Field(
        default=None,
        description="Comma-separated user ids, e.g. `4,9`: only shots that have "
        "at least one task assigned to one of those users. The value `none` "
        "stands for a task with no assignee and can be mixed in (`4,none`).",
    )


class ShotListOut(pydantic.BaseModel):
    """A page of shots."""

    items: list[ShotOut]
    total: int = pydantic.Field(description="Total number of shots matching filters.")
    page: int
    page_size: int


class ShotFiltersOut(pydantic.BaseModel):
    """Filter values that at least one shot of the project actually has."""

    status_ids: list[int] = pydantic.Field(
        description="Ids of the shot statuses used by at least one shot."
    )
    assignee_ids: list[int] = pydantic.Field(
        description="Ids of the users who have at least one task on a shot."
    )
    has_unassigned: bool = pydantic.Field(
        description="Whether at least one shot has a task with no assignee."
    )


class ProjectShotsPath(pydantic.BaseModel):
    """URL path parameters identifying a project's shots collection."""

    project_id: int = pydantic.Field(gt=0)


class ShotGroupShotsPath(pydantic.BaseModel):
    """URL path parameters identifying a shot group's shots collection."""

    shot_group_id: int = pydantic.Field(gt=0)


class ShotPath(pydantic.BaseModel):
    """URL path parameters identifying a single shot."""

    shot_id: int = pydantic.Field(gt=0)


class ShotCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/projects/<project_id>/shots/`.

    This is the only place a shot is created - there's no corresponding
    create on the shot-group-scoped collection, to avoid two routes with
    subtly different creation semantics.
    """

    name: str = pydantic.Field(min_length=1, max_length=255)
    group_ids: list[int] = pydantic.Field(
        default_factory=list,
        description=(
            "Ids of shot groups (within the same project) to add this shot "
            "to. Optional - a shot may belong to none; there is no default "
            "or fallback group."
        ),
    )
    status_id: int | None = pydantic.Field(
        default=None,
        description=(
            "Id of the shot's initial status, from the project's company. "
            "Optional - defaults to the company's ShotStatus.is_default. "
            "An error if omitted and the company has no default status."
        ),
    )
    rec_timecode: int | None = pydantic.Field(
        default=None,
        ge=0,
        description="Start position of the shot in the edit, in frames.",
    )
    duration: int | None = pydantic.Field(
        default=None,
        ge=1,
        description="Length of the shot, in frames.",
    )

    @pydantic.field_validator("name")
    @classmethod
    def validate_name_charset(cls, value: str) -> str:
        if not SHOT_NAME_PATTERN.match(value):
            raise ValueError("Shot name may not contain slashes or whitespace.")
        return value


class ShotUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/shots/<id>/`. All fields are optional.

    `name` is intentionally absent - like `Project.code`, it's immutable
    once the shot is created. `group_ids`, when present, *replaces* the
    full set of group memberships (it's not a merge/add) - send the
    complete desired list.
    """

    group_ids: list[int] | None = None
    status_id: int | None = pydantic.Field(
        default=None,
        description=(
            "Id of a status from the project's company. Since `status` "
            "can't be null on a shot, sending this as null is rejected - "
            "omit the field entirely to leave the status unchanged."
        ),
    )
    rec_timecode: int | None = pydantic.Field(default=None, ge=0)
    duration: int | None = pydantic.Field(default=None, ge=1)
