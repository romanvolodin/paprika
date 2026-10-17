from http import HTTPStatus

from django.core.paginator import Paginator
from django.db.models import Q
from dmr import (
    APIError,
    Body,
    FileMetadata,
    Path,
    Query,
    ResponseSpec,
    modify,
)
from dmr.errors import ErrorType
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer

from apps.auth.api.controllers import AuthenticatedController
from apps.core.storage import delete_stored_file
from apps.users.models import User

from .schemas import (
    UserAvatarFiles,
    UserCreateIn,
    UserListOut,
    UserListQuery,
    UserOut,
    UserPath,
    UserUpdateIn,
)


def _serialize_user(request, user: User) -> UserOut:
    avatar_url = request.build_absolute_uri(user.avatar.url) if user.avatar else None
    return UserOut(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar=avatar_url,
        is_active=user.is_active,
        date_joined=user.date_joined,
    )


def _get_user_or_404(user_id: int) -> User:
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise APIError(
            {"detail": f"User with id={user_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _apply_avatar(user: User, files: UserAvatarFiles, request) -> None:
    """Replace the user's avatar with the uploaded file, if any was sent.

    `FileMetadata` (see `UserAvatarFiles`) already validated the file's
    name/size before we get here, so this only has to move the already
    validated `UploadedFile` from `request.FILES` onto the model and
    clean up whatever avatar it's replacing.

    Note: we intentionally don't call `old_avatar.delete()` here. Despite
    being a separate Python object, `FieldFile.delete()` unconditionally
    does `setattr(self.instance, self.field.attname, None)` - it resets
    the field on the *model instance* regardless of which `FieldFile`
    wrapper you call it on, even with `save=False`. Since `old_avatar`
    and `user.avatar` share the same `instance`, calling delete on the
    old one would silently wipe out the new avatar we just assigned. We
    remove the old file straight from storage instead, which never
    touches the instance.
    """
    if files.avatar is None:
        return

    old_name = user.avatar.name if user.avatar else None
    old_storage = user.avatar.storage if user.avatar else None

    user.avatar = request.FILES["avatar"]
    user.save(update_fields=["avatar"])

    if old_name:
        delete_stored_file(old_storage, old_name)


def _clear_avatar(user: User) -> None:
    """Remove the user's current avatar, if any."""
    old_name = user.avatar.name if user.avatar else None
    old_storage = user.avatar.storage if user.avatar else None

    user.avatar = ""
    user.save(update_fields=["avatar"])

    if old_name:
        delete_stored_file(old_storage, old_name)


class MeController(AuthenticatedController[PydanticFastSerializer]):
    """`GET /api/v1/users/me/` - return the currently authenticated user."""

    @modify(
        summary="Get current user",
        description="Return the profile of the user identified by the "
        "provided access token.",
        response_description="The currently authenticated user.",
        tags=["Users"],
    )
    def get(self) -> UserOut:
        return _serialize_user(self.request, self.request.user)


class UserListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/users/` - list and create users.

    Any authenticated user may list or create users; finer-grained
    permissions are deferred until they're actually needed.
    """

    @modify(
        summary="List users",
        description=(
            "Return a paginated list of users, optionally filtered by "
            "`search` against email, first and last name."
        ),
        response_description="A page of users.",
        tags=["Users"],
    )
    def get(self, parsed_query: Query[UserListQuery]) -> UserListOut:
        queryset = User.objects.all()

        if parsed_query.search:
            queryset = queryset.filter(
                Q(email__icontains=parsed_query.search)
                | Q(first_name__icontains=parsed_query.search)
                | Q(last_name__icontains=parsed_query.search),
            )

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        return UserListOut(
            items=[_serialize_user(self.request, user) for user in page.object_list],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )

    @modify(
        parsers=[MultiPartParser()],
        status_code=HTTPStatus.CREATED,
        summary="Create a user",
        description=(
            "Create a new user account, optionally with an avatar. Send "
            "as `multipart/form-data`: regular fields for `email`, "
            "`password`, `first_name`, `last_name`, plus an optional "
            "`avatar` file field. If `password` is omitted, the account "
            "is created with an unusable password."
        ),
        response_description="The created user.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
        ],
        tags=["Users"],
    )
    def post(
        self,
        parsed_body: Body[UserCreateIn],
        parsed_file_metadata: FileMetadata[UserAvatarFiles],
    ) -> UserOut:
        if User.objects.filter(email__iexact=parsed_body.email).exists():
            raise APIError(
                self.format_error(
                    "A user with this email already exists.",
                    loc=["email"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        user = User.objects.create_user(
            email=parsed_body.email,
            password=parsed_body.password,
            first_name=parsed_body.first_name,
            last_name=parsed_body.last_name,
        )
        _apply_avatar(user, parsed_file_metadata, self.request)
        return _serialize_user(self.request, user)


class UserDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/users/<id>/` - manage a single user."""

    @modify(
        summary="Get a user",
        description="Return a single user by id.",
        response_description="The requested user.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Users"],
    )
    def get(self, parsed_path: Path[UserPath]) -> UserOut:
        user = _get_user_or_404(parsed_path.user_id)
        return _serialize_user(self.request, user)

    @modify(
        parsers=[MultiPartParser()],
        summary="Update a user",
        description=(
            "Partially update a user, optionally replacing or removing "
            "their avatar in the same request. Send as "
            "`multipart/form-data`: any of `first_name`, `last_name`, "
            "`is_active`, `remove_avatar`, plus an optional `avatar` "
            "file field. Only fields actually present are changed."
        ),
        response_description="The updated user.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Users"],
    )
    def patch(
        self,
        parsed_path: Path[UserPath],
        parsed_body: Body[UserUpdateIn],
        parsed_file_metadata: FileMetadata[UserAvatarFiles],
    ) -> UserOut:
        user = _get_user_or_404(parsed_path.user_id)

        update_fields = parsed_body.model_dump(
            exclude={"remove_avatar"},
            exclude_unset=True,
        )
        for field, value in update_fields.items():
            setattr(user, field, value)
        if update_fields:
            user.save(update_fields=list(update_fields))

        if parsed_file_metadata.avatar is not None:
            _apply_avatar(user, parsed_file_metadata, self.request)
        elif parsed_body.remove_avatar and user.avatar:
            _clear_avatar(user)

        return _serialize_user(self.request, user)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a user",
        description="Permanently delete a user account.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Users"],
    )
    def delete(self, parsed_path: Path[UserPath]) -> None:
        user = _get_user_or_404(parsed_path.user_id)
        user.delete()
        return None
