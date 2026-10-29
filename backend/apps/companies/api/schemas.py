import datetime as dt

import pydantic

from apps.access.api.schemas import RoleRefOut


class CompanyOut(pydantic.BaseModel):
    """Public representation of a company."""

    id: int = pydantic.Field(description="Internal numeric company identifier.")
    name: str = pydantic.Field(description="Company name.")
    slug: str = pydantic.Field(description="URL-friendly identifier for the company.")
    my_permissions: list[str] = pydantic.Field(
        description="Codes of the company permissions the current user has."
    )
    created_at: dt.datetime
    updated_at: dt.datetime


class CompanyListQuery(pydantic.BaseModel):
    """Pagination and search params for `GET /api/v1/companies/`."""

    page: int = pydantic.Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = pydantic.Field(
        default=20,
        ge=1,
        le=100,
        description="Number of companies per page.",
    )
    search: str | None = pydantic.Field(
        default=None,
        description="Case-insensitive match against the company name.",
    )


class CompanyListOut(pydantic.BaseModel):
    """A page of companies the current user belongs to."""

    items: list[CompanyOut]
    total: int = pydantic.Field(
        description="Total number of companies matching filters."
    )
    page: int
    page_size: int


class CompanyPath(pydantic.BaseModel):
    """URL path parameters identifying a single company."""

    company_id: int = pydantic.Field(gt=0)


class CompanyCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/companies/`."""

    name: str = pydantic.Field(min_length=1, max_length=255)
    slug: str | None = pydantic.Field(
        default=None,
        max_length=255,
        description=(
            "URL-friendly identifier. If omitted, it's auto-derived from `name`."
        ),
    )


class CompanyUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/companies/<id>/`. All fields are optional."""

    name: str | None = pydantic.Field(default=None, min_length=1, max_length=255)
    slug: str | None = pydantic.Field(default=None, min_length=1, max_length=255)


class CompanyMemberOut(pydantic.BaseModel):
    """Public representation of a company membership."""

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


class CompanyMemberListOut(pydantic.BaseModel):
    """The full list of a company's members (not paginated)."""

    items: list[CompanyMemberOut]


class CompanyMemberPath(pydantic.BaseModel):
    """URL path parameters identifying a single company member."""

    company_id: int = pydantic.Field(gt=0)
    user_id: int = pydantic.Field(gt=0)


class CompanyMemberCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/companies/<id>/members/`."""

    email: pydantic.EmailStr = pydantic.Field(
        description="Email of the person to add; it identifies their account."
    )
    first_name: str = pydantic.Field(min_length=1, max_length=150)
    last_name: str = pydantic.Field(min_length=1, max_length=150)
    password: str = pydantic.Field(
        min_length=1,
        description=(
            "Temporary password for a new account; the person has to choose "
            "their own at the first sign-in. Ignored when an account with "
            "this email already exists."
        ),
    )
    role_id: int = pydantic.Field(gt=0, description="A role of this company.")


class CompanyMemberUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/companies/<id>/members/<user_id>/`."""

    role_id: int = pydantic.Field(gt=0, description="A role of this company.")
