from http import HTTPStatus
import os

import pytest

from apps.chat.models import Attachment, Message
from apps.chat.tests.api.conftest import patch_json, post_json


pytestmark = pytest.mark.django_db


def _list_url(shot):
    return f"/api/v1/shots/{shot.id}/chat/"


def _detail_url(message):
    return f"/api/v1/chat/{message.id}/"


class TestCreateMessage:
    def test_creates_a_text_message(self, auth_client, auth_user, member_shot):
        response = post_json(auth_client, _list_url(member_shot), {"text": "Привет"})

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert body["type"] == "user"
        assert body["text"] == "Привет"
        assert body["shot_id"] == member_shot.id
        assert body["created_by"]["id"] == auth_user.id
        message = Message.objects.get(pk=body["id"])
        assert message.created_by == auth_user
        assert message.updated_by == auth_user

    def test_trims_the_text(self, auth_client, member_shot):
        response = post_json(auth_client, _list_url(member_shot), {"text": "  hi \n"})

        assert response.json()["text"] == "hi"

    def test_rejects_a_message_with_nothing_in_it(self, auth_client, member_shot):
        for payload in ({}, {"text": ""}, {"text": "  \n "}):
            response = post_json(auth_client, _list_url(member_shot), payload)

            assert response.status_code == HTTPStatus.BAD_REQUEST, payload
        assert not Message.objects.exists()

    def test_rejects_a_too_long_text(self, auth_client, member_shot, settings):
        settings.CHAT_MESSAGE_MAX_LENGTH = 10

        response = post_json(auth_client, _list_url(member_shot), {"text": "x" * 11})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        ok = post_json(auth_client, _list_url(member_shot), {"text": "x" * 10})
        assert ok.status_code == HTTPStatus.CREATED

    def test_default_text_limit_is_2000(self, auth_client, member_shot):
        too_long = post_json(auth_client, _list_url(member_shot), {"text": "x" * 2001})
        fits = post_json(auth_client, _list_url(member_shot), {"text": "x" * 2000})

        assert too_long.status_code == HTTPStatus.BAD_REQUEST
        assert fits.status_code == HTTPStatus.CREATED

    def test_role_without_permission_cannot_write(self, auth_client, readonly_shot):
        response = post_json(auth_client, _list_url(readonly_shot), {"text": "hi"})

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_non_member_gets_a_404(self, auth_client, shot, project_membership_factory):
        project_membership_factory(project=shot.project)  # some other user

        response = post_json(auth_client, _list_url(shot), {"text": "hi"})

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot):
        response = post_json(client, _list_url(shot), {"text": "hi"})

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestReply:
    def test_replies_to_a_message_of_the_same_shot(
        self, auth_client, member_shot, message_factory
    ):
        quoted = message_factory(shot=member_shot, text="вопрос")

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "ответ", "reply_to_id": quoted.id},
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["reply_to"]["id"] == quoted.id
        assert response.json()["reply_to"]["text"] == "вопрос"

    def test_cannot_reply_to_a_message_of_another_shot(
        self, auth_client, member_shot, message_factory
    ):
        other = message_factory()

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "hi", "reply_to_id": other.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_cannot_reply_to_a_deleted_message(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        quoted = message_factory(shot=member_shot)
        quoted.mark_deleted(auth_user)

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "hi", "reply_to_id": quoted.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_cannot_reply_to_a_system_message(
        self, auth_client, auth_user, member_shot
    ):
        system = Message.objects.create(
            shot=member_shot,
            type=Message.Type.SYSTEM,
            event=Message.Event.TASK_ADDED,
            created_by=auth_user,
        )

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "hi", "reply_to_id": system.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


class TestLinkedVersions:
    def test_links_versions_of_the_same_shot(
        self, auth_client, member_shot, version_factory
    ):
        first = version_factory(shot=member_shot)
        second = version_factory(shot=member_shot)

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "три версии", "version_ids": [first.id, second.id]},
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        names = {v["name"] for v in response.json()["versions"]}
        assert names == {first.name, second.name}

    def test_a_message_may_consist_of_versions_only(
        self, auth_client, member_shot, version_factory
    ):
        version = version_factory(shot=member_shot)

        response = post_json(
            auth_client, _list_url(member_shot), {"version_ids": [version.id]}
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["text"] == ""

    def test_cannot_link_a_version_of_another_shot(
        self, auth_client, member_shot, version_factory
    ):
        foreign = version_factory()

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "hi", "version_ids": [foreign.id]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Message.objects.exists()

    def test_deleting_a_version_keeps_the_message(
        self, auth_client, member_shot, version_factory
    ):
        version = version_factory(shot=member_shot)
        message_id = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "смотрите", "version_ids": [version.id]},
        ).json()["id"]

        version.delete()

        body = auth_client.get(_detail_url(Message(id=message_id))).json()
        assert body["text"] == "смотрите"
        assert body["versions"] == []


class TestAttachToMessage:
    def test_attaches_uploaded_files(
        self, auth_client, auth_user, member_shot, attachment_factory
    ):
        first = attachment_factory(shot=member_shot, created_by=auth_user)
        second = attachment_factory(shot=member_shot, created_by=auth_user)

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "файлы", "attachment_ids": [first.id, second.id]},
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert [a["id"] for a in response.json()["attachments"]] == [
            first.id,
            second.id,
        ]
        first.refresh_from_db()
        assert first.message_id == response.json()["id"]

    def test_a_message_may_consist_of_a_file_only(
        self, auth_client, auth_user, member_shot, attachment_factory
    ):
        attachment = attachment_factory(shot=member_shot, created_by=auth_user)

        response = post_json(
            auth_client, _list_url(member_shot), {"attachment_ids": [attachment.id]}
        )

        assert response.status_code == HTTPStatus.CREATED, response.content

    def test_cannot_attach_someone_elses_file(
        self, auth_client, member_shot, attachment_factory
    ):
        foreign = attachment_factory(shot=member_shot)  # another uploader

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "hi", "attachment_ids": [foreign.id]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Message.objects.exists()

    def test_cannot_attach_a_file_of_another_shot(
        self, auth_client, auth_user, member_shot, attachment_factory
    ):
        foreign = attachment_factory(created_by=auth_user)  # on another shot

        response = post_json(
            auth_client,
            _list_url(member_shot),
            {"text": "hi", "attachment_ids": [foreign.id]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_cannot_attach_the_same_file_twice(
        self, auth_client, auth_user, member_shot, attachment_factory
    ):
        attachment = attachment_factory(shot=member_shot, created_by=auth_user)
        payload = {"attachment_ids": [attachment.id]}
        post_json(auth_client, _list_url(member_shot), payload)

        response = post_json(auth_client, _list_url(member_shot), payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert Message.objects.count() == 1

    def test_at_most_10_attachments(
        self, auth_client, auth_user, member_shot, attachment_factory
    ):
        ids = [
            attachment_factory(shot=member_shot, created_by=auth_user).id
            for _ in range(11)
        ]

        too_many = post_json(
            auth_client, _list_url(member_shot), {"attachment_ids": ids}
        )
        ten = post_json(
            auth_client, _list_url(member_shot), {"attachment_ids": ids[:10]}
        )

        assert too_many.status_code == HTTPStatus.BAD_REQUEST
        assert ten.status_code == HTTPStatus.CREATED


class TestGetMessage:
    def test_returns_the_message(self, auth_client, member_shot, message_factory):
        message = message_factory(shot=member_shot, text="hi")

        response = auth_client.get(_detail_url(message))

        assert response.status_code == HTTPStatus.OK
        assert response.json()["text"] == "hi"

    def test_a_deleted_message_is_a_404(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot)
        message.mark_deleted(auth_user)

        response = auth_client.get(_detail_url(message))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_non_member_gets_a_404(
        self, auth_client, message_factory, project_membership_factory
    ):
        message = message_factory()
        project_membership_factory(project=message.shot.project)

        response = auth_client.get(_detail_url(message))

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestEditMessage:
    def test_changes_the_text_and_marks_it_edited(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot, created_by=auth_user, text="old")

        response = patch_json(auth_client, _detail_url(message), {"text": " new "})

        assert response.status_code == HTTPStatus.OK, response.content
        assert response.json()["text"] == "new"
        assert response.json()["edited_at"] is not None
        message.refresh_from_db()
        assert message.text == "new"
        assert message.updated_by == auth_user

    def test_an_unchanged_text_is_not_marked_edited(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot, created_by=auth_user, text="same")

        response = patch_json(auth_client, _detail_url(message), {"text": "same"})

        assert response.status_code == HTTPStatus.OK
        assert response.json()["edited_at"] is None

    def test_cannot_edit_to_an_empty_text(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot, created_by=auth_user, text="old")

        response = patch_json(auth_client, _detail_url(message), {"text": "  "})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        message.refresh_from_db()
        assert message.text == "old"

    def test_the_text_may_be_emptied_if_there_is_an_attachment(
        self, auth_client, auth_user, member_shot, message_factory, attachment_factory
    ):
        message = message_factory(shot=member_shot, created_by=auth_user, text="old")
        attachment_factory(shot=member_shot, message=message)

        response = patch_json(auth_client, _detail_url(message), {"text": ""})

        assert response.status_code == HTTPStatus.OK, response.content
        assert response.json()["text"] == ""

    def test_the_text_may_be_emptied_if_there_is_a_version(
        self, auth_client, auth_user, member_shot, message_factory, version_factory
    ):
        message = message_factory(shot=member_shot, created_by=auth_user, text="old")
        message.versions.add(version_factory(shot=member_shot))

        response = patch_json(auth_client, _detail_url(message), {"text": ""})

        assert response.status_code == HTTPStatus.OK, response.content

    def test_cannot_edit_the_text_to_be_too_long(
        self, auth_client, auth_user, member_shot, message_factory, settings
    ):
        settings.CHAT_MESSAGE_MAX_LENGTH = 5
        message = message_factory(shot=member_shot, created_by=auth_user, text="old")

        response = patch_json(auth_client, _detail_url(message), {"text": "x" * 6})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_only_the_text_is_editable(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        quoted = message_factory(shot=member_shot)
        message = message_factory(
            shot=member_shot, created_by=auth_user, text="old", reply_to=quoted
        )

        patch_json(
            auth_client,
            _detail_url(message),
            {"text": "new", "reply_to_id": None, "version_ids": [1]},
        )

        message.refresh_from_db()
        assert message.reply_to == quoted
        assert not message.versions.exists()

    def test_cannot_edit_someone_elses_message(
        self, auth_client, executor_shot, message_factory
    ):
        message = message_factory(shot=executor_shot, text="old")  # another author

        response = patch_json(auth_client, _detail_url(message), {"text": "new"})

        assert response.status_code == HTTPStatus.FORBIDDEN
        message.refresh_from_db()
        assert message.text == "old"

    def test_moderator_can_edit_someone_elses_message(
        self, auth_client, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot, text="old")  # another author

        response = patch_json(auth_client, _detail_url(message), {"text": "new"})

        assert response.status_code == HTTPStatus.OK
        message.refresh_from_db()
        assert message.text == "new"
        assert message.edited_at is not None

    def test_cannot_edit_a_system_message(self, auth_client, auth_user, member_shot):
        system = Message.objects.create(
            shot=member_shot,
            type=Message.Type.SYSTEM,
            event=Message.Event.TASK_ADDED,
            created_by=auth_user,
        )

        response = patch_json(auth_client, _detail_url(system), {"text": "new"})

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_role_without_permission_cannot_edit(
        self, auth_client, auth_user, readonly_shot, message_factory
    ):
        message = message_factory(shot=readonly_shot, created_by=auth_user)

        response = patch_json(auth_client, _detail_url(message), {"text": "new"})

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestDeleteMessage:
    def test_soft_deletes_the_message_and_its_content(
        self,
        auth_client,
        auth_user,
        member_shot,
        message_factory,
        attachment_factory,
        reaction_factory,
        version_factory,
        django_capture_on_commit_callbacks,
        settings,
    ):
        message = message_factory(shot=member_shot, created_by=auth_user, text="secret")
        attachment = attachment_factory(shot=member_shot, message=message)
        stored = attachment.file.path
        reaction_factory(message=message)
        version = version_factory(shot=member_shot)
        message.versions.add(version)
        assert os.path.exists(stored)

        with django_capture_on_commit_callbacks(execute=True):
            response = auth_client.delete(_detail_url(message))

        assert response.status_code == HTTPStatus.NO_CONTENT
        message.refresh_from_db()
        assert message.text == ""
        assert message.deleted_at is not None
        assert not message.attachments.exists()
        assert not message.reactions.exists()
        assert not message.versions.exists()
        assert not Attachment.objects.filter(pk=attachment.pk).exists()
        assert not os.path.exists(stored)
        version.refresh_from_db()  # the version itself is untouched

    def test_replies_keep_working(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot, created_by=auth_user)
        reply = message_factory(shot=member_shot, reply_to=message)

        auth_client.delete(_detail_url(message))

        reply.refresh_from_db()
        assert reply.reply_to_id == message.id

    def test_cannot_delete_someone_elses_message(
        self, auth_client, executor_shot, message_factory
    ):
        message = message_factory(shot=executor_shot)

        response = auth_client.delete(_detail_url(message))

        assert response.status_code == HTTPStatus.FORBIDDEN
        message.refresh_from_db()
        assert message.deleted_at is None

    def test_moderator_can_delete_someone_elses_message(
        self, auth_client, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot)

        response = auth_client.delete(_detail_url(message))

        assert response.status_code == HTTPStatus.NO_CONTENT
        message.refresh_from_db()
        assert message.deleted_at is not None

    def test_cannot_delete_a_system_message(self, auth_client, auth_user, member_shot):
        system = Message.objects.create(
            shot=member_shot,
            type=Message.Type.SYSTEM,
            event=Message.Event.TASK_ADDED,
            created_by=auth_user,
        )

        response = auth_client.delete(_detail_url(system))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_deleting_twice_is_a_404(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot, created_by=auth_user)
        auth_client.delete(_detail_url(message))

        response = auth_client.delete(_detail_url(message))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_role_without_permission_cannot_delete(
        self, auth_client, auth_user, readonly_shot, message_factory
    ):
        message = message_factory(shot=readonly_shot, created_by=auth_user)

        response = auth_client.delete(_detail_url(message))

        assert response.status_code == HTTPStatus.FORBIDDEN
