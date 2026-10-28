import datetime as dt

import pydantic

from apps.access.permissions import ALL_CODES, PERMISSIONS


_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


def _known_codes(codes: list[str]) -> list[str]:
    unknown = sorted(set(codes) - ALL_CODES)
    if unknown:
        raise ValueError(f"Unknown permissions: {', '.join(unknown)}.")
    return sorted(set(codes))


class PermissionOut(pydantic.BaseModel):
    """One of the permissions a role can be made of."""

    code: str = pydantic.Field(description="Stable code, e.g. `shot.create`.")
    label: str
    description: str
    group: str = pydantic.Field(description="Section the permission is shown in.")
    level: str = pydantic.Field(
        description=(
            "`company` permissions act through the role in the company, "
            "`project` ones through the role in the project."
        )
    )


class PermissionListOut(pydantic.BaseModel):
    """The fixed list of permissions, in display order."""

    items: list[PermissionOut]


def permission_list() -> PermissionListOut:
    return PermissionListOut(
        items=[
            PermissionOut(
                code=p.code,
                label=p.label,
                description=p.description,
                group=p.group,
                level=p.level,
            )
            for p in PERMISSIONS
        ]
    )


class RoleRefOut(pydantic.BaseModel):
    """A role as shown next to a member."""

    id: int
    name: str
    color: str = pydantic.Field(description="Hex color, e.g. `#FF5733`.")


class RoleOut(pydantic.BaseModel):
    """Public representation of a role."""

    id: int
    company_id: int
    name: str
    color: str = pydantic.Field(description="Hex color, e.g. `#FF5733`.")
    permissions: list[str] = pydantic.Field(
        description="Codes of the permissions the role gives."
    )
    sees_all_projects: bool = pydantic.Field(
        description=(
            "Whether a company member with this role sees every project of "
            "the company, not only those they were added to."
        )
    )
    company_members_count: int = pydantic.Field(
        description="How many people have this role in the company."
    )
    project_members_count: int = pydantic.Field(
        description="How many project memberships use this role."
    )
    created_at: dt.datetime
    updated_at: dt.datetime


class RoleListOut(pydantic.BaseModel):
    """All roles of a company (not paginated: the list is short)."""

    items: list[RoleOut]


class CompanyRolesPath(pydantic.BaseModel):
    company_id: int = pydantic.Field(gt=0)


class RolePath(pydantic.BaseModel):
    role_id: int = pydantic.Field(gt=0)


class RoleCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/companies/<company_id>/roles/`."""

    name: str = pydantic.Field(min_length=1, max_length=100)
    color: str = pydantic.Field(pattern=_COLOR_PATTERN)
    permissions: list[str] = pydantic.Field(default_factory=list)
    sees_all_projects: bool = False

    @pydantic.field_validator("permissions")
    @classmethod
    def _check_permissions(cls, value):
        return _known_codes(value)


class RoleUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/roles/<id>/`. All fields are optional."""

    name: str | None = pydantic.Field(default=None, min_length=1, max_length=100)
    color: str | None = pydantic.Field(default=None, pattern=_COLOR_PATTERN)
    permissions: list[str] | None = None
    sees_all_projects: bool | None = None

    @pydantic.field_validator("permissions")
    @classmethod
    def _check_permissions(cls, value):
        return None if value is None else _known_codes(value)
