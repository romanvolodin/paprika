import datetime as dt
from typing import Literal

import pydantic

from apps.access.api.schemas import RoleRefOut


class InvitationProjectOut(pydantic.BaseModel):
    """A project the invitation adds the person to."""

    project_id: int
    project_name: str
    role: RoleRefOut = pydantic.Field(description="The role in the project.")


class InvitationOut(pydantic.BaseModel):
    """Public representation of an invitation, as the people who send it see it."""

    id: int
    company_id: int
    email: str
    role: RoleRefOut = pydantic.Field(description="The role in the company.")
    projects: list[InvitationProjectOut]
    token: str = pydantic.Field(
        description=(
            "The secret of the invitation link: `/invite/<token>` in the "
            "interface. Whoever has it can accept the invitation."
        )
    )
    expires_at: dt.datetime
    is_expired: bool
    created_by_name: str | None = pydantic.Field(
        description="Who sent the invitation, if they are still around."
    )
    created_at: dt.datetime


class InvitationListOut(pydantic.BaseModel):
    """The company's invitations that have not been accepted (not paginated)."""

    items: list[InvitationOut]


class CompanyInvitationsPath(pydantic.BaseModel):
    company_id: int = pydantic.Field(gt=0)


class ProjectInvitationsPath(pydantic.BaseModel):
    project_id: int = pydantic.Field(gt=0)


class InvitationPath(pydantic.BaseModel):
    invitation_id: int = pydantic.Field(gt=0)


class TokenPath(pydantic.BaseModel):
    token: str = pydantic.Field(min_length=1, max_length=64)


class InvitedProjectIn(pydantic.BaseModel):
    project_id: int = pydantic.Field(gt=0)
    role_id: int = pydantic.Field(gt=0, description="A role of the company.")


class InvitationCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/companies/<id>/invitations/`."""

    email: pydantic.EmailStr
    role_id: int = pydantic.Field(gt=0, description="The role in the company.")
    projects: list[InvitedProjectIn] = pydantic.Field(
        default_factory=list,
        description="Projects of the company to add the person to as well.",
    )


class ProjectInvitationCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/projects/<id>/invitations/`."""

    email: pydantic.EmailStr
    role_id: int = pydantic.Field(
        gt=0,
        description=(
            "The role in the project. It becomes their role in the company "
            "too, so it must not carry company permissions."
        ),
    )


class InvitationInfoOut(pydantic.BaseModel):
    """What the person who got the link sees before they accept."""

    email: str
    company_id: int
    company_name: str
    role_name: str
    project_names: list[str]
    expires_at: dt.datetime
    status: Literal["pending", "expired", "accepted"]
    account_exists: bool = pydantic.Field(
        description="Whether the email already has an account to sign in to."
    )


class RegisterIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/invite/<token>/register/`."""

    first_name: str = pydantic.Field(min_length=1, max_length=150)
    last_name: str = pydantic.Field(min_length=1, max_length=150)
    password: str = pydantic.Field(min_length=1)
