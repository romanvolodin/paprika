import datetime as dt
import re

import pydantic

from apps.access.api.schemas import RoleRefOut
from apps.projects.validators import COVER_ALLOWED_EXTENSIONS, COVER_MAX_SIZE_MB
from apps.users.api.schemas import UserOut


CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

_COVER_EXTENSION_PATTERN = r"(?i)\.({})$".format(
    "|".join(re.escape(ext) for ext in COVER_ALLOWED_EXTENSIONS),
)


class CoverFileMetadata(pydantic.BaseModel):
    """Validates an uploaded cover's metadata before it touches the DB.

    Mirrors the constraints already enforced by `Project.cover`'s own
    validators (see `apps/projects/validators.py`) - see `AvatarFileMetadata`
    in `apps/users/api/schemas.py` for the same pattern applied to avatars.
    """

    name: str = pydantic.Field(
        pattern=_COVER_EXTENSION_PATTERN,
        description=f"Allowed extensions: {', '.join(COVER_ALLOWED_EXTENSIONS)}.",
    )
    size: int = pydantic.Field(
        le=COVER_MAX_SIZE_MB * 1024 * 1024,
        description=f"Max {COVER_MAX_SIZE_MB} MB.",
    )


class ProjectCoverFiles(pydantic.BaseModel):
    """Files accepted alongside a project create/update payload.

    `cover` is optional: omit the field entirely to leave it untouched
    (on update) or create the project without one (on create).
    """

    cover: CoverFileMetadata | None = None


class ProjectOut(pydantic.BaseModel):
    """Public representation of a project."""

    id: int = pydantic.Field(description="Internal numeric project identifier.")
    company_id: int
    name: str = pydantic.Field(description="Project name.")
    code: str = pydantic.Field(
        description="Short, URL-friendly project code (e.g. `PRJ`). Immutable."
    )
    description: str
    cover: str | None = pydantic.Field(
        default=None,
        description="Absolute URL of the project's cover image, or null if none.",
    )
    start_date: dt.date | None
    deadline: dt.date | None
    is_active: bool
    created_by: UserOut | None = pydantic.Field(
        description="The user who created the project, or null if that "
        "user has since been deleted."
    )
    updated_by: UserOut | None = pydantic.Field(
        description="The user who last updated the project, or null if "
        "that user has since been deleted."
    )
    my_permissions: list[str] = pydantic.Field(
        description="Codes of the project permissions the current user has."
    )
    created_at: dt.datetime
    updated_at: dt.datetime


class ProjectListQuery(pydantic.BaseModel):
    """Pagination and search params for `GET /api/v1/companies/<id>/projects/`."""

    page: int = pydantic.Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = pydantic.Field(
        default=20,
        ge=1,
        le=100,
        description="Number of projects per page.",
    )
    search: str | None = pydantic.Field(
        default=None,
        description="Case-insensitive match against the project name.",
    )
    code: str | None = pydantic.Field(
        default=None,
        description="Exact (case-sensitive) match against the project code.",
    )


class ProjectListOut(pydantic.BaseModel):
    """A page of projects the current user is a member of, within a company."""

    items: list[ProjectOut]
    total: int = pydantic.Field(
        description="Total number of projects matching filters."
    )
    page: int
    page_size: int


class CompanyProjectsPath(pydantic.BaseModel):
    """URL path parameters identifying a company's projects collection."""

    company_id: int = pydantic.Field(gt=0)


class ProjectPath(pydantic.BaseModel):
    """URL path parameters identifying a single project."""

    project_id: int = pydantic.Field(gt=0)


class ProjectCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/companies/<company_id>/projects/`."""

    name: str = pydantic.Field(min_length=1, max_length=255)
    code: str = pydantic.Field(
        min_length=1,
        max_length=50,
        description="Short, URL-friendly project code (e.g. `PRJ`). Set once - "
        "cannot be changed later.",
    )
    description: str = pydantic.Field(default="", max_length=10_000)
    start_date: dt.date | None = None
    deadline: dt.date | None = None

    @pydantic.field_validator("code")
    @classmethod
    def validate_code_charset(cls, value: str) -> str:
        if not CODE_PATTERN.match(value):
            raise ValueError(
                "Code may only contain letters, numbers, hyphens and underscores."
            )
        return value

    @pydantic.model_validator(mode="after")
    def validate_deadline_after_start(self) -> ProjectCreateIn:
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValueError("Deadline cannot be earlier than the start date.")
        return self


class ProjectUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/projects/<id>/`. All fields are optional.

    `code` is intentionally absent - it's immutable once the project is
    created.
    """

    name: str | None = pydantic.Field(default=None, min_length=1, max_length=255)
    description: str | None = pydantic.Field(default=None, max_length=10_000)
    start_date: dt.date | None = None
    deadline: dt.date | None = None
    is_active: bool | None = None
    remove_cover: bool = pydantic.Field(
        default=False,
        description=(
            "Set to true to delete the current cover. Ignored if a new "
            "`cover` file is also sent in the same request."
        ),
    )

    @pydantic.model_validator(mode="after")
    def validate_deadline_after_start(self) -> ProjectUpdateIn:
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValueError("Deadline cannot be earlier than the start date.")
        return self


class ProjectMemberOut(pydantic.BaseModel):
    """Public representation of a project membership."""

    id: int = pydantic.Field(description="Internal numeric membership identifier.")
    user_id: int
    email: str
    first_name: str
    last_name: str
    avatar: str | None = pydantic.Field(
        default=None,
        description="Absolute URL of the member's avatar image, or null if none.",
    )
    role: RoleRefOut
    created_at: dt.datetime


class ProjectMemberListOut(pydantic.BaseModel):
    """The full list of a project's members (not paginated)."""

    items: list[ProjectMemberOut]


class ProjectMemberPath(pydantic.BaseModel):
    """URL path parameters identifying a single project member."""

    project_id: int = pydantic.Field(gt=0)
    user_id: int = pydantic.Field(gt=0)


class ProjectMemberCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/projects/<id>/members/`.

    `user_id` must belong to a user who is already a `CompanyMembership`
    member of the project's company.
    """

    user_id: int = pydantic.Field(gt=0)
    role_id: int = pydantic.Field(gt=0, description="A role of the project's company.")


class ProjectMemberUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/projects/<id>/members/<user_id>/`."""

    role_id: int = pydantic.Field(gt=0, description="A role of the project's company.")
