import datetime as dt
from typing import Literal

import pydantic

from apps.chat.api.schemas import AttachmentOut
from apps.users.api.schemas import UserOut


class ProjectFeedPath(pydantic.BaseModel):
    """URL path parameters identifying a project's feed."""

    project_id: int = pydantic.Field(gt=0)


class FeedQuery(pydantic.BaseModel):
    """Filters and the cursor of `GET /api/v1/projects/<id>/feed/`."""

    type: str | None = pydantic.Field(
        default=None,
        description="Comma-separated event types to return: `chat`, `task`, "
        "`version`. All of them if omitted.",
    )
    mine: bool = pydantic.Field(
        default=False,
        description="Only events on shots that have a task assigned to the "
        "current user.",
    )
    before_date: dt.datetime | None = pydantic.Field(
        default=None,
        description="Return events created before this moment (exclusive). "
        "Pass the `next_before_date` of the previous response to load "
        "earlier events. Without it the feed starts from the newest events.",
    )


class FeedShotOut(pydantic.BaseModel):
    id: int
    name: str


class FeedVersionOut(pydantic.BaseModel):
    """A version, as much of it as the feed needs to show and open it."""

    id: int
    name: str
    type: str = pydantic.Field(description="`video` or `image`.")
    source: str = pydantic.Field(description="Absolute URL of the original file.")
    converted: str | None = pydantic.Field(
        description="Absolute URL of the browser-friendly rendition, or null."
    )
    thumb: str | None = pydantic.Field(
        description="Absolute URL of a small JPG thumbnail, or null."
    )


class FeedItemOut(pydantic.BaseModel):
    """One event of the feed.

    `type` says which of the optional fields are filled:

    - `chat` - a user message: `text`, `attachments` and `versions` (the
      versions the message links to).
    - `version` - a version was uploaded: `version`.
    - `task` - something happened to a task on a shot: `event`
      (`task_added`, `status_changed` or `assignee_changed`) and
      `payload` with the details, exactly as in the shot's chat.
    """

    key: str = pydantic.Field(
        description="Identifies the event within the feed, e.g. `chat-12`."
    )
    type: Literal["chat", "task", "version"]
    created_at: dt.datetime
    created_by: UserOut | None = pydantic.Field(
        description="Who did it, or null if that user has since been deleted."
    )
    shot: FeedShotOut
    text: str | None = pydantic.Field(description="Only for `chat`.")
    attachments: list[AttachmentOut] = pydantic.Field(description="Only for `chat`.")
    versions: list[FeedVersionOut] = pydantic.Field(description="Only for `chat`.")
    version: FeedVersionOut | None = pydantic.Field(description="Only for `version`.")
    event: str | None = pydantic.Field(description="Only for `task`.")
    payload: dict = pydantic.Field(description="Only for `task`; empty otherwise.")


class FeedOut(pydantic.BaseModel):
    """A slice of the feed, newest events first."""

    items: list[FeedItemOut]
    next_before_date: dt.datetime | None = pydantic.Field(
        description="Pass as `before_date` to load the next, older slice. "
        "Null when there is nothing older."
    )
