from http import HTTPStatus
import os

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
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
from dmr.plugins.pydantic import PydanticSerializer

from apps.access.checks import can_in_project, projects_q, require_project_perm
from apps.access.permissions import P
from apps.auth.api.controllers import AuthenticatedController
from apps.chat.models import Attachment, Message, Reaction
from apps.shots.api.views import _get_shot_or_404
from apps.users.api.views import _serialize_user
from apps.users.models import User
from apps.versions.api.views import _serialize_version
from apps.versions.models import Version

from .schemas import (
    AttachmentOut,
    AttachmentPath,
    ChatAttachmentFiles,
    ChatListOut,
    ChatListQuery,
    MessageCreateIn,
    MessageOut,
    MessagePath,
    MessageUpdateIn,
    ReactionIn,
    ReactionQuery,
    ReactionsOut,
    ReactionSummaryOut,
    ReplyToOut,
    ShotChatPath,
)


_QUOTE_LENGTH = 200


def _error(controller, message: str, loc: list[str], status: HTTPStatus) -> APIError:
    return APIError(
        controller.format_error(message, loc=loc, error_type=ErrorType.value_error),
        status_code=status,
    )


def _bad_request(controller, message: str, loc: list[str]) -> APIError:
    return _error(controller, message, loc, HTTPStatus.BAD_REQUEST)


def _file_url(request, field) -> str:
    return request.build_absolute_uri(field.url)


def _serialize_attachment(request, attachment: Attachment) -> AttachmentOut:
    return AttachmentOut(
        id=attachment.id,
        url=_file_url(request, attachment.file),
        filename=attachment.filename,
        size=attachment.size,
        content_type=attachment.content_type,
    )


def _summarize_reactions(reactions) -> list[ReactionSummaryOut]:
    """Collapse reactions by emoji, in the order each emoji first appeared.

    A reaction whose author has since been deleted (`created_by` is null)
    is left out, and so is an emoji that has no one left.
    """
    grouped: dict[str, list[int]] = {}
    for reaction in sorted(reactions, key=lambda r: r.id):
        if reaction.created_by_id is None:
            continue
        grouped.setdefault(reaction.emoji, []).append(reaction.created_by_id)
    return [
        ReactionSummaryOut(emoji=emoji, user_ids=user_ids)
        for emoji, user_ids in grouped.items()
    ]


def _serialize_message(request, message: Message) -> MessageOut:
    """Needs `_message_queryset()` relations loaded (it avoids N+1 queries)."""
    reply_to = None
    if message.reply_to is not None:
        quoted = message.reply_to
        reply_to = ReplyToOut(
            id=quoted.id,
            author=_serialize_user(request, quoted.created_by)
            if quoted.created_by
            else None,
            text=quoted.text[:_QUOTE_LENGTH],
            deleted=quoted.is_deleted,
        )
    is_system = message.type == Message.Type.SYSTEM
    return MessageOut(
        id=message.id,
        shot_id=message.shot_id,
        type=message.type,
        text=message.text,
        event=message.event if is_system else None,
        payload=message.payload if is_system else {},
        reply_to=reply_to,
        versions=[_serialize_version(request, v) for v in message.versions.all()],
        attachments=[
            _serialize_attachment(request, a) for a in message.attachments.all()
        ],
        reactions=_summarize_reactions(message.reactions.all()),
        edited_at=message.edited_at,
        created_by=_serialize_user(request, message.created_by)
        if message.created_by
        else None,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _message_queryset():
    return Message.objects.select_related(
        "created_by", "reply_to", "reply_to__created_by"
    ).prefetch_related(
        Prefetch(
            "versions",
            queryset=Version.objects.select_related("created_by", "updated_by"),
        ),
        "attachments",
        "reactions",
    )


def _get_message_or_404(user: User, message_id: int) -> Message:
    """Look up a (not deleted) message, scoped to projects the user is in.

    Mirrors `_get_shot_or_404`: visibility follows the parent project's
    `ProjectMembership`. A deleted message is answered with 404 like a
    missing one - it only survives as a quote inside replies.
    """
    try:
        return (
            _message_queryset()
            .filter(projects_q(user, "shot__project"), deleted_at__isnull=True)
            .get(pk=message_id)
        )
    except Message.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Message with id={message_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _clean_text(controller, text: str) -> str:
    text = text.strip()
    max_length = settings.CHAT_MESSAGE_MAX_LENGTH
    if len(text) > max_length:
        raise _bad_request(
            controller,
            f"The text is too long. Max length is {max_length} characters.",
            ["text"],
        )
    return text


def _require_can_change_message(message: Message, user: User) -> None:
    """403 unless the user may edit or delete this message.

    Your own messages need the chat permission; other people's need the
    moderation one. System messages can't be changed by anyone.
    """
    if message.type == Message.Type.SYSTEM:
        raise APIError(
            {"detail": "System messages can't be changed."},
            status_code=HTTPStatus.FORBIDDEN,
        )
    project = message.shot.project
    if message.created_by_id == user.id:
        require_project_perm(user, project, P.CHAT_WRITE)
    elif not can_in_project(user, project, P.CHAT_EDIT_ANY):
        raise APIError(
            {"detail": "You can only change your own messages."},
            status_code=HTTPStatus.FORBIDDEN,
        )


class ChatListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/shots/<shot_id>/chat/` - read and write the chat."""

    @modify(
        summary="List a shot's chat messages",
        description=(
            "Cursor pagination, messages come in chronological order. "
            "Without `before`/`around` the last `limit` messages are "
            "returned. `before=<id>` loads the `limit` messages older than "
            "that message. `around=<id>` returns a window around the "
            "message (to jump to a quote). Deleted messages are not "
            "listed. System messages (events on the shot) are in the "
            "same list."
        ),
        response_description="A slice of the chat.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
        ],
        tags=["Chat"],
    )
    def get(
        self,
        parsed_path: Path[ShotChatPath],
        parsed_query: Query[ChatListQuery],
    ) -> ChatListOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        limit = parsed_query.limit
        before, around = parsed_query.before, parsed_query.around
        if before is not None and around is not None:
            raise _bad_request(
                self, "`before` and `around` can't be used together.", ["around"]
            )

        visible = Message.objects.filter(shot=shot, deleted_at__isnull=True)

        if around is not None:
            if not visible.filter(pk=around).exists():
                raise APIError(
                    {"detail": f"Message with id={around} was not found."},
                    status_code=HTTPStatus.NOT_FOUND,
                )
            newer_ids = list(
                visible.filter(id__gt=around)
                .order_by("id")
                .values_list("id", flat=True)[: limit // 2]
            )
            older_ids = list(
                visible.filter(id__lte=around)
                .order_by("-id")
                .values_list("id", flat=True)[: limit - len(newer_ids)]
            )
            ids = older_ids + newer_ids
        else:
            window = visible
            if before is not None:
                window = window.filter(id__lt=before)
            ids = list(window.order_by("-id").values_list("id", flat=True)[:limit])

        messages = list(_message_queryset().filter(pk__in=ids).order_by("id"))
        has_older = bool(messages) and visible.filter(id__lt=messages[0].id).exists()
        has_newer = bool(messages) and visible.filter(id__gt=messages[-1].id).exists()
        return ChatListOut(
            items=[_serialize_message(self.request, m) for m in messages],
            has_older=has_older,
            has_newer=has_newer,
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Send a chat message",
        description=(
            "Create a user message. It needs text, at least one "
            "attachment or at least one version (or several). Files are "
            "uploaded beforehand via `POST /shots/<id>/chat/attachments/` "
            "and passed by id. `reply_to_id` must be a user message of the "
            "same shot. `version_ids` must be versions of the same shot. "
            "Needs the `chat.write` permission."
        ),
        response_description="The created message.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Chat"],
    )
    def post(
        self,
        parsed_path: Path[ShotChatPath],
        parsed_body: Body[MessageCreateIn],
    ) -> MessageOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        require_project_perm(self.request.user, shot.project, P.CHAT_WRITE)
        user = self.request.user

        text = _clean_text(self, parsed_body.text)

        reply_to = None
        if parsed_body.reply_to_id is not None:
            reply_to = Message.objects.filter(
                shot=shot,
                pk=parsed_body.reply_to_id,
                type=Message.Type.USER,
                deleted_at__isnull=True,
            ).first()
            if reply_to is None:
                raise _bad_request(
                    self,
                    f"Message with id={parsed_body.reply_to_id} can't be replied "
                    "to: it doesn't exist in this chat, is deleted or is a "
                    "system message.",
                    ["reply_to_id"],
                )

        version_ids = list(dict.fromkeys(parsed_body.version_ids))
        versions = list(Version.objects.filter(shot=shot, pk__in=version_ids))
        if len(versions) != len(version_ids):
            raise _bad_request(
                self,
                "Some versions were not found among this shot's versions.",
                ["version_ids"],
            )

        attachment_ids = list(dict.fromkeys(parsed_body.attachment_ids))
        if len(attachment_ids) > settings.CHAT_MESSAGE_MAX_ATTACHMENTS:
            raise _bad_request(
                self,
                "Too many attachments. Max is "
                f"{settings.CHAT_MESSAGE_MAX_ATTACHMENTS} per message.",
                ["attachment_ids"],
            )

        if not (text or versions or attachment_ids):
            raise _bad_request(
                self,
                "A message needs text, an attachment or a version.",
                ["text"],
            )

        with transaction.atomic():
            # Lock the rows so two requests can't attach the same file.
            attachments = list(
                Attachment.objects.select_for_update().filter(
                    shot=shot,
                    pk__in=attachment_ids,
                    message__isnull=True,
                    created_by=user,
                )
            )
            if len(attachments) != len(attachment_ids):
                raise _bad_request(
                    self,
                    "Some attachments were not found, are already attached "
                    "to a message or were uploaded by someone else.",
                    ["attachment_ids"],
                )
            message = Message.objects.create(
                shot=shot,
                type=Message.Type.USER,
                text=text,
                reply_to=reply_to,
                created_by=user,
                updated_by=user,
            )
            message.versions.set(versions)
            Attachment.objects.filter(pk__in=attachment_ids).update(message=message)

        return _serialize_message(self.request, _get_message_or_404(user, message.pk))


class ChatAttachmentUploadController(AuthenticatedController[PydanticSerializer]):
    """`POST /api/v1/shots/<shot_id>/chat/attachments/` - upload a file."""

    @modify(
        parsers=[MultiPartParser()],
        status_code=HTTPStatus.CREATED,
        summary="Upload a chat attachment",
        description=(
            "Upload a file as `multipart/form-data` with a single required "
            "file field `file`. Any file type is accepted; the size limit "
            "is configurable (`PAPRIKA_CHAT_ATTACHMENT_MAX_FILE_SIZE_MB`, "
            "100 by default, 413 otherwise). The returned `id` goes into "
            "`attachment_ids` of a new message. Until then the file can "
            "be removed with `DELETE /chat/attachments/<id>/`. Needs the "
            "`chat.write` permission."
        ),
        response_description="The uploaded attachment.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
            ResponseSpec(dict, status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE),
        ],
        tags=["Chat"],
    )
    def post(
        self,
        parsed_path: Path[ShotChatPath],
        parsed_file_metadata: FileMetadata[ChatAttachmentFiles],
    ) -> AttachmentOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        require_project_perm(self.request.user, shot.project, P.CHAT_WRITE)

        upload = self.request.FILES["file"]

        max_size_mb = settings.CHAT_ATTACHMENT_MAX_FILE_SIZE_MB
        if upload.size > max_size_mb * 1024 * 1024:
            raise _error(
                self,
                f"The file is too large. Max size is {max_size_mb} MB.",
                ["file"],
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )

        attachment = Attachment.objects.create(
            shot=shot,
            file=upload,
            filename=os.path.basename(upload.name)[:255],
            size=upload.size,
            content_type=(upload.content_type or "")[:255],
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_attachment(self.request, attachment)


class ChatAttachmentDetailController(AuthenticatedController[PydanticSerializer]):
    """`DELETE /api/v1/chat/attachments/<id>/` - remove an unsent file."""

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Remove an uploaded chat attachment",
        description=(
            "Remove a file that was uploaded but not yet sent. Only its "
            "uploader can do it. A file that is already part of a message "
            "can't be removed this way (409) - delete the message instead."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
        ],
        tags=["Chat"],
    )
    def delete(self, parsed_path: Path[AttachmentPath]) -> None:
        user = self.request.user
        try:
            attachment = (
                Attachment.objects.filter(projects_q(user, "shot__project"))
                .select_related("shot__project")
                .distinct()
                .get(pk=parsed_path.attachment_id)
            )
        except Attachment.DoesNotExist as exc:
            raise APIError(
                {
                    "detail": f"Attachment with id={parsed_path.attachment_id} "
                    "was not found."
                },
                status_code=HTTPStatus.NOT_FOUND,
            ) from exc

        require_project_perm(user, attachment.shot.project, P.CHAT_WRITE)
        if attachment.created_by_id != user.id:
            raise APIError(
                {"detail": "You can only remove files you uploaded."},
                status_code=HTTPStatus.FORBIDDEN,
            )
        if attachment.message_id is not None:
            raise APIError(
                {
                    "detail": "The file is already part of a message. Delete "
                    "the message instead."
                },
                status_code=HTTPStatus.CONFLICT,
            )
        attachment.delete()
        return None


class ChatMessageDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/chat/<id>/` - a single message."""

    @modify(
        summary="Get a chat message",
        description="Return a single message by id. Deleted messages are 404.",
        response_description="The requested message.",
        extra_responses=[ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND)],
        tags=["Chat"],
    )
    def get(self, parsed_path: Path[MessagePath]) -> MessageOut:
        message = _get_message_or_404(self.request.user, parsed_path.message_id)
        return _serialize_message(self.request, message)

    @modify(
        summary="Edit a chat message",
        description=(
            "Change the text of your own user message. Attachments, "
            "versions and the quoted message can't be changed. The text "
            "can only become empty if the message has an attachment or a "
            "version. `edited_at` is set when the text actually changed. "
            "System messages can't be edited. Your own messages need "
            "`chat.write`, other people's `chat.edit_any`."
        ),
        response_description="The updated message.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Chat"],
    )
    def patch(
        self,
        parsed_path: Path[MessagePath],
        parsed_body: Body[MessageUpdateIn],
    ) -> MessageOut:
        user = self.request.user
        message = _get_message_or_404(user, parsed_path.message_id)
        _require_can_change_message(message, user)

        text = _clean_text(self, parsed_body.text)
        if not (text or message.attachments.all() or message.versions.all()):
            raise _bad_request(
                self,
                "A message needs text, an attachment or a version.",
                ["text"],
            )

        if text != message.text:
            message.text = text
            message.edited_at = timezone.now()
            message.updated_by = user
            message.save(
                update_fields=["text", "edited_at", "updated_by", "updated_at"]
            )

        return _serialize_message(self.request, message)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a chat message",
        description=(
            "Delete a user message: your own, or anyone's with the "
            "`chat.edit_any` permission. The message disappears from "
            "the chat; its text, files, version links and reactions are "
            "removed. Replies to it stay and show it as deleted. System "
            "messages can't be deleted."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Chat"],
    )
    def delete(self, parsed_path: Path[MessagePath]) -> None:
        user = self.request.user
        message = _get_message_or_404(user, parsed_path.message_id)
        _require_can_change_message(message, user)
        with transaction.atomic():
            message.mark_deleted(user)
        return None


class ChatReactionController(AuthenticatedController[PydanticSerializer]):
    """`PUT/DELETE /api/v1/chat/<id>/reactions/` - put or remove your emoji."""

    @modify(
        summary="Put a reaction on a message",
        description=(
            "Put an emoji on a message (a user or a system one, not a "
            "deleted one). Putting the same emoji again changes nothing. "
            "Needs the `chat.write` permission."
        ),
        response_description="All reactions of the message.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Chat"],
    )
    def put(
        self,
        parsed_path: Path[MessagePath],
        parsed_body: Body[ReactionIn],
    ) -> ReactionsOut:
        user = self.request.user
        message = _get_message_or_404(user, parsed_path.message_id)
        require_project_perm(user, message.shot.project, P.CHAT_WRITE)
        Reaction.objects.get_or_create(
            message=message,
            created_by=user,
            emoji=parsed_body.emoji,
            defaults={"updated_by": user},
        )
        return self._reactions(message)

    @modify(
        summary="Remove your reaction from a message",
        description=(
            "Remove your own emoji from a message; the emoji goes in the "
            "`emoji` query param (a DELETE request has no body). Removing "
            "a reaction "
            "that isn't there changes nothing. Needs the `chat.write` "
            "permission."
        ),
        response_description="All reactions of the message.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Chat"],
    )
    def delete(
        self,
        parsed_path: Path[MessagePath],
        parsed_query: Query[ReactionQuery],
    ) -> ReactionsOut:
        user = self.request.user
        message = _get_message_or_404(user, parsed_path.message_id)
        require_project_perm(user, message.shot.project, P.CHAT_WRITE)
        Reaction.objects.filter(
            message=message, created_by=user, emoji=parsed_query.emoji
        ).delete()
        return self._reactions(message)

    @staticmethod
    def _reactions(message: Message) -> ReactionsOut:
        return ReactionsOut(
            reactions=_summarize_reactions(Reaction.objects.filter(message=message))
        )
