import pydantic


class PasswordChangeIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/auth/password/`."""

    current_password: str = pydantic.Field(
        description="The password the user signs in with now.",
    )
    new_password: str = pydantic.Field(
        min_length=1,
        description="The new password; it must pass the server's password rules.",
    )


class LoginPayload(pydantic.BaseModel):
    """Credentials used to obtain a new access/refresh token pair."""

    email: str = pydantic.Field(
        description="Registered user's email address.",
        examples=["user@example.com"],
    )
    password: str = pydantic.Field(
        description="User's password.",
        examples=["W5&faQ36$f6"],
    )
