import datetime as dt
import re

import pydantic

from apps.users.validators import AVATAR_ALLOWED_EXTENSIONS, AVATAR_MAX_SIZE_MB


_AVATAR_EXTENSION_PATTERN = r"(?i)\.({})$".format(
    "|".join(re.escape(ext) for ext in AVATAR_ALLOWED_EXTENSIONS),
)


class AvatarFileMetadata(pydantic.BaseModel):
    """Validates an uploaded avatar's metadata before it touches the DB.

    Mirrors the constraints already enforced by `User.avatar`'s own
    validators (see `apps/users/validators.py`), just fails earlier with
    a structured, per-field error instead of one flat message.
    """

    name: str = pydantic.Field(
        pattern=_AVATAR_EXTENSION_PATTERN,
        description=f"Allowed extensions: {', '.join(AVATAR_ALLOWED_EXTENSIONS)}.",
    )
    size: int = pydantic.Field(
        le=AVATAR_MAX_SIZE_MB * 1024 * 1024,
        description=f"Max {AVATAR_MAX_SIZE_MB} MB.",
    )


class UserAvatarFiles(pydantic.BaseModel):
    """Files accepted alongside a user create/update payload.

    `avatar` is optional: omit the field entirely to leave it untouched
    (on update) or create the user without one (on create).
    """

    avatar: AvatarFileMetadata | None = None


class UserOut(pydantic.BaseModel):
    """Public representation of a user."""

    id: int = pydantic.Field(description="Internal numeric user identifier.")
    email: str = pydantic.Field(description="User's email address.")
    first_name: str = pydantic.Field(description="User's first name.")
    last_name: str = pydantic.Field(description="User's last name.")
    avatar: str | None = pydantic.Field(
        default=None,
        description="Absolute URL of the user's avatar image, or null if none.",
    )
    is_active: bool = pydantic.Field(
        description="Whether the user account is active.",
    )
    date_joined: dt.datetime = pydantic.Field(
        description="When the user account was created.",
    )


class MeOut(UserOut):
    """The signed-in user's own account: `UserOut` plus what only they see."""

    is_superuser: bool = pydantic.Field(
        description="Whether the user administers the whole server.",
    )
    must_change_password: bool = pydantic.Field(
        description=(
            "Whether the password was set by someone else and has to be "
            "changed before anything else can be done."
        ),
    )


class UserListQuery(pydantic.BaseModel):
    """Pagination and search params for `GET /api/v1/users/`."""

    page: int = pydantic.Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = pydantic.Field(
        default=20,
        ge=1,
        le=100,
        description="Number of users per page.",
    )
    search: str | None = pydantic.Field(
        default=None,
        description="Case-insensitive match against email, first or last name.",
    )


class UserListOut(pydantic.BaseModel):
    """A page of users."""

    items: list[UserOut]
    total: int = pydantic.Field(description="Total number of users matching filters.")
    page: int
    page_size: int


class UserPath(pydantic.BaseModel):
    """URL path parameters identifying a single user."""

    user_id: int = pydantic.Field(gt=0)


class UserCreateIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/users/`."""

    email: pydantic.EmailStr
    password: str | None = pydantic.Field(
        default=None,
        min_length=8,
        description=(
            "If omitted, the account is created with an unusable password "
            "(e.g. for an invite-based flow)."
        ),
    )
    first_name: str = pydantic.Field(min_length=1, max_length=150)
    last_name: str = pydantic.Field(min_length=1, max_length=150)


class UserUpdateIn(pydantic.BaseModel):
    """Payload for `PATCH /api/v1/users/<id>/`. All fields are optional."""

    first_name: str | None = pydantic.Field(default=None, min_length=1, max_length=150)
    last_name: str | None = pydantic.Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None
    remove_avatar: bool = pydantic.Field(
        default=False,
        description=(
            "Set to true to delete the current avatar. Ignored if a new "
            "`avatar` file is also sent in the same request."
        ),
    )
