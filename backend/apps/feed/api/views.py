from datetime import timedelta
from http import HTTPStatus

from django.db.models import Exists, Max, OuterRef, QuerySet
from dmr import APIError, Path, Query, ResponseSpec, modify
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer

from apps.access.checks import require_project_perm
from apps.access.permissions import P
from apps.auth.api.controllers import AuthenticatedController
from apps.chat.api.views import _serialize_attachment
from apps.chat.models import Message
from apps.projects.api.views import _get_project_or_404
from apps.tasks.models import ShotTask
from apps.users.api.views import _serialize_user
from apps.versions.api.views import _file_url
from apps.versions.models import Version

from .schemas import (
    FeedItemOut,
    FeedOut,
    FeedQuery,
    FeedShotOut,
    FeedVersionOut,
    ProjectFeedPath,
)


FEED_WINDOW = timedelta(days=5)

_TYPES = ("chat", "task", "version")
_TASK_EVENTS = [
    Message.Event.TASK_ADDED,
    Message.Event.STATUS_CHANGED,
    Message.Event.ASSIGNEE_CHANGED,
]
# Only breaks ties between events created at the very same moment.
_TYPE_RANK = {"chat": 0, "task": 1, "version": 2}


def _parse_types(controller, raw: str | None) -> set[str]:
    if raw is None:
        return set(_TYPES)
    types = {part.strip() for part in raw.split(",") if part.strip()}
    unknown = types - set(_TYPES)
    if unknown or not types:
        raise APIError(
            controller.format_error(
                f"`type` must be a comma-separated list of: {', '.join(_TYPES)}.",
                loc=["type"],
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return types


def _sources(project, user, types: set[str], mine: bool) -> dict[str, QuerySet]:
    """One queryset per requested event type, already filtered."""
    sources: dict[str, QuerySet] = {}
    if "chat" in types:
        sources["chat"] = Message.objects.filter(
            shot__project=project,
            type=Message.Type.USER,
            deleted_at__isnull=True,
        )
    if "task" in types:
        # The task events are the shot chat's system messages. Version
        # uploads are left out of them: the versions themselves are the
        # source of those events.
        sources["task"] = Message.objects.filter(
            shot__project=project,
            type=Message.Type.SYSTEM,
            event__in=_TASK_EVENTS,
        )
    if "version" in types:
        sources["version"] = Version.objects.filter(project=project)

    if mine:
        assigned = Exists(
            ShotTask.objects.filter(assignee=user, shot=OuterRef("shot_id"))
        )
        sources = {key: queryset.filter(assigned) for key, queryset in sources.items()}
    return sources


def _serialize_feed_version(request, version: Version) -> FeedVersionOut:
    return FeedVersionOut(
        id=version.id,
        name=version.name,
        type=version.type,
        source=_file_url(request, version.source),
        converted=_file_url(request, version.converted),
        thumb=_file_url(request, version.thumb),
    )


def _serialize_item(request, kind: str, row: Message | Version) -> FeedItemOut:
    item = FeedItemOut(
        key=f"{kind}-{row.id}",
        type=kind,
        created_at=row.created_at,
        created_by=_serialize_user(request, row.created_by) if row.created_by else None,
        shot=FeedShotOut(id=row.shot_id, name=row.shot.name),
        text=None,
        attachments=[],
        versions=[],
        version=None,
        event=None,
        payload={},
    )
    if kind == "chat":
        item.text = row.text
        item.attachments = [
            _serialize_attachment(request, a) for a in row.attachments.all()
        ]
        item.versions = [
            _serialize_feed_version(request, v) for v in row.versions.all()
        ]
    elif kind == "task":
        item.event = row.event
        item.payload = row.payload
    else:
        item.version = _serialize_feed_version(request, row)
    return item


class ProjectFeedController(AuthenticatedController[PydanticSerializer]):
    """`GET /api/v1/projects/<project_id>/feed/` - what happened in the project."""

    @modify(
        summary="List the project's events",
        description=(
            "Chat messages, uploaded versions and task events (a task added "
            "to a shot, its status or assignee changed) of all the shots of "
            "the project, newest first. The events are collected on the fly "
            "from the chat and version tables. One response covers a window "
            "of 5 days, counted back from the newest event found (so a quiet "
            "week doesn't give an empty page). To load earlier events pass "
            "the `next_before_date` of the response as `before_date`."
        ),
        response_description="A slice of the feed.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Feed"],
    )
    def get(
        self,
        parsed_path: Path[ProjectFeedPath],
        parsed_query: Query[FeedQuery],
    ) -> FeedOut:
        user = self.request.user
        project = _get_project_or_404(user, parsed_path.project_id)
        require_project_perm(user, project, P.FEED_VIEW)
        types = _parse_types(self, parsed_query.type)
        sources = _sources(project, user, types, parsed_query.mine)

        if parsed_query.before_date is not None:
            sources = {
                key: queryset.filter(created_at__lt=parsed_query.before_date)
                for key, queryset in sources.items()
            }

        newest_dates = [
            queryset.aggregate(newest=Max("created_at"))["newest"]
            for queryset in sources.values()
        ]
        newest = max((date for date in newest_dates if date is not None), default=None)
        if newest is None:
            return FeedOut(items=[], next_before_date=None)

        start = newest - FEED_WINDOW
        rows: list[tuple[str, Message | Version]] = []
        for kind, queryset in sources.items():
            queryset = queryset.filter(created_at__gte=start).select_related(
                "created_by"
            )
            if kind == "version":
                queryset = queryset.select_related("shot")
            else:
                queryset = queryset.select_related("shot").prefetch_related(
                    "attachments", "versions"
                )
            rows.extend((kind, row) for row in queryset)
        rows.sort(
            key=lambda r: (r[1].created_at, _TYPE_RANK[r[0]], r[1].id), reverse=True
        )

        has_more = any(
            queryset.filter(created_at__lt=start).exists()
            for queryset in sources.values()
        )
        return FeedOut(
            items=[_serialize_item(self.request, kind, row) for kind, row in rows],
            next_before_date=start if has_more else None,
        )
