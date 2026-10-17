from http import HTTPStatus

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from dmr import (
    APIError,
    FileMetadata,
    Path,
    Query,
    ResponseSpec,
    modify,
)
from dmr.errors import ErrorType
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer

from apps.auth.api.controllers import AuthenticatedController
from apps.chat.events import record_version_uploaded
from apps.core.storage import delete_stored_file
from apps.projects.models import Project
from apps.projects.permissions import require_can_write
from apps.shots.api.views import _get_shot_or_404
from apps.users.api.views import _serialize_user
from apps.users.models import User
from apps.versions.media import MediaError, process_upload
from apps.versions.models import Version

from .schemas import (
    ShotVersionsPath,
    VersionFiles,
    VersionListOut,
    VersionListQuery,
    VersionOut,
    VersionPath,
)


_UNIQUE_NAME_CONSTRAINT = "unique_version_name_per_project"


def _file_url(request, field) -> str | None:
    return request.build_absolute_uri(field.url) if field else None


def _serialize_version(request, version: Version) -> VersionOut:
    return VersionOut(
        id=version.id,
        project_id=version.project_id,
        shot_id=version.shot_id,
        name=version.name,
        type=version.type,
        source=_file_url(request, version.source),
        converted=_file_url(request, version.converted),
        thumb=_file_url(request, version.thumb),
        width=version.width,
        height=version.height,
        duration=version.duration,
        fps=version.fps,
        codec=version.codec,
        file_size=version.file_size,
        created_by=_serialize_user(request, version.created_by)
        if version.created_by
        else None,
        updated_by=_serialize_user(request, version.updated_by)
        if version.updated_by
        else None,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def _get_version_or_404(user: User, version_id: int) -> Version:
    """Look up a version, scoped to projects the user is a member of.

    Mirrors `apps.shots.api.views._get_shot_or_404` - visibility follows
    the parent project's `ProjectMembership`.
    """
    try:
        return (
            Version.objects.filter(project__memberships__user=user)
            .select_related("created_by", "updated_by")
            .distinct()
            .get(pk=version_id)
        )
    except Version.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Version with id={version_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _discard_files(version: Version) -> None:
    """Delete a never-committed version's files from storage."""
    for field in (version.source, version.converted, version.thumb):
        if field and field.name:
            delete_stored_file(field.storage, field.name)


class VersionListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/shots/<shot_id>/versions/` - list a shot's versions
    and upload a new one.
    """

    @modify(
        summary="List a shot's versions",
        description=("Return a paginated list of the shot's versions, newest first."),
        response_description="A page of versions.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Versions"],
    )
    def get(
        self,
        parsed_path: Path[ShotVersionsPath],
        parsed_query: Query[VersionListQuery],
    ) -> VersionListOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)

        queryset = Version.objects.filter(shot=shot).select_related(
            "created_by", "updated_by"
        )
        if parsed_query.search:
            queryset = queryset.filter(name__icontains=parsed_query.search)

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        return VersionListOut(
            items=[_serialize_version(self.request, v) for v in page.object_list],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )

    @modify(
        parsers=[MultiPartParser()],
        status_code=HTTPStatus.CREATED,
        summary="Upload a version",
        description=(
            "Upload a new version of the shot as `multipart/form-data` with "
            "a single required file field `source` (`.mp4` with h264 video, "
            "`.jpg` or `.png`). The version's `name` is the file name "
            "without its extension and must be unique within the project "
            "(409 otherwise). Its metadata and thumbnail are produced while "
            "the request is being handled, so the response arrives only "
            "after the file has been processed. Not available to members "
            "with the read-only `client` role."
        ),
        response_description="The created version.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE),
        ],
        tags=["Versions"],
    )
    def post(
        self,
        parsed_path: Path[ShotVersionsPath],
        parsed_file_metadata: FileMetadata[VersionFiles],
    ) -> VersionOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        require_can_write(self.request.user, shot.project)

        upload = self.request.FILES["source"]

        max_size_mb = settings.VERSION_MAX_FILE_SIZE_MB
        if upload.size > max_size_mb * 1024 * 1024:
            raise APIError(
                self.format_error(
                    f"The file is too large. Max size is {max_size_mb} MB.",
                    loc=["source"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )

        base_name, _, extension = upload.name.rpartition(".")
        extension = extension.lower()

        # Cheap check first so a duplicate doesn't cost a full file
        # inspection. The DB constraint below is the real guarantee.
        if self._name_taken(shot.project, base_name):
            raise self._duplicate_name_error(base_name)

        try:
            processed = process_upload(
                upload,
                extension,
                thumb_position=settings.VERSION_THUMB_FRAME_POSITION,
                thumb_max_size=settings.VERSION_THUMB_MAX_SIZE,
            )
        except MediaError as exc:
            raise APIError(
                self.format_error(
                    str(exc), loc=["source"], error_type=ErrorType.value_error
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            ) from exc

        info = processed.info
        version = Version(
            project=shot.project,
            shot=shot,
            name=base_name,
            type=info.type,
            source=upload,
            thumb=ContentFile(processed.thumb, name=f"{upload.name}_thumb.jpg"),
            width=info.width,
            height=info.height,
            duration=info.duration,
            fps=info.fps,
            codec=info.codec,
            file_size=upload.size,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        try:
            with transaction.atomic():
                version.save(force_insert=True)
                record_version_uploaded(version, self.request.user)
        except IntegrityError as exc:
            # Lost a race with a concurrent upload of the same name: the
            # files were already written, so clean them up.
            _discard_files(version)
            if _UNIQUE_NAME_CONSTRAINT not in str(exc):
                raise
            raise self._duplicate_name_error(base_name) from exc

        return _serialize_version(self.request, version)

    @staticmethod
    def _name_taken(project: Project, name: str) -> bool:
        return Version.objects.filter(project=project, name=name).exists()

    def _duplicate_name_error(self, name: str) -> APIError:
        return APIError(
            self.format_error(
                f"A version named '{name}' already exists in this project.",
                loc=["source"],
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.CONFLICT,
        )


class VersionDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/DELETE /api/v1/versions/<id>/` - read or delete a single version.

    There is no `PATCH`: a version can't be edited or renamed. To fix a
    mistake, delete it and upload again.
    """

    @modify(
        summary="Get a version",
        description="Return a single version by id.",
        response_description="The requested version.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Versions"],
    )
    def get(self, parsed_path: Path[VersionPath]) -> VersionOut:
        version = _get_version_or_404(self.request.user, parsed_path.version_id)
        return _serialize_version(self.request, version)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a version",
        description=(
            "Permanently delete a version and its files. Its name is "
            "freed up for a new upload. Not available to members with the "
            "read-only `client` role."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Versions"],
    )
    def delete(self, parsed_path: Path[VersionPath]) -> None:
        version = _get_version_or_404(self.request.user, parsed_path.version_id)
        require_can_write(self.request.user, version.project)
        version.delete()
        return None
