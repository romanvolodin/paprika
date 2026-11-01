from http import HTTPStatus
import json
from urllib.parse import urlencode

import pytest

from apps.chat.models import Attachment, Message, Reaction
from apps.chat.tests.api.conftest import put_json


pytestmark = pytest.mark.django_db


@pytest.fixture
def project(project_factory):
    return project_factory()


@pytest.fixture
def mine(project, shot_factory):
    return shot_factory(project=project)


@pytest.fixture
def other(project, shot_factory):
    return shot_factory(project=project)


@pytest.fixture
def freelancer(auth_user, project, mine, project_membership_factory, shot_task_factory):
    project_membership_factory(user=auth_user, project=project, role="freelancer")
    shot_task_factory(shot=mine, assignee=auth_user)
    return auth_user


def _message_url(message):
    return f"/api/v1/chat/{message.id}/"


def _reactions_url(message):
    return f"/api/v1/chat/{message.id}/reactions/"


def _attachment_url(attachment):
    return f"/api/v1/chat/attachments/{attachment.id}/"


class TestMessageOfAHiddenShot:
    def test_it_cannot_be_read_edited_or_deleted(
        self, auth_client, freelancer, other, message_factory
    ):
        message = message_factory(shot=other, created_by=freelancer, text="secret")

        responses = [
            auth_client.get(_message_url(message)),
            auth_client.patch(
                _message_url(message),
                data=json.dumps({"text": "changed"}),
                content_type="application/json",
            ),
            auth_client.delete(_message_url(message)),
        ]

        assert {r.status_code for r in responses} == {HTTPStatus.NOT_FOUND}
        message.refresh_from_db()
        assert message.text == "secret"
        assert message.deleted_at is None

    def test_no_reaction_can_be_put_or_removed(
        self, auth_client, freelancer, other, message_factory, reaction_factory
    ):
        message = message_factory(shot=other)
        reaction_factory(message=message, created_by=freelancer, emoji="👍")

        put = put_json(auth_client, _reactions_url(message), {"emoji": "🔥"})
        removed = auth_client.delete(
            f"{_reactions_url(message)}?{urlencode({'emoji': '👍'})}"
        )

        assert put.status_code == HTTPStatus.NOT_FOUND
        assert removed.status_code == HTTPStatus.NOT_FOUND
        assert list(Reaction.objects.values_list("emoji", flat=True)) == ["👍"]


class TestAttachmentOfAHiddenShot:
    def test_it_cannot_be_removed(
        self, auth_client, freelancer, other, attachment_factory
    ):
        attachment = attachment_factory(shot=other, created_by=freelancer)

        response = auth_client.delete(_attachment_url(attachment))

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Attachment.objects.filter(pk=attachment.pk).exists()


class TestVisibleShot:
    def test_the_message_can_be_read_and_reacted_to(
        self, auth_client, freelancer, mine, message_factory
    ):
        message = message_factory(shot=mine)

        read = auth_client.get(_message_url(message))
        put = put_json(auth_client, _reactions_url(message), {"emoji": "🔥"})

        assert read.status_code == HTTPStatus.OK
        assert put.status_code == HTTPStatus.OK

    def test_its_author_can_edit_and_delete_it(
        self, auth_client, freelancer, mine, message_factory
    ):
        message = message_factory(shot=mine, created_by=freelancer)

        edited = auth_client.patch(
            _message_url(message),
            data=json.dumps({"text": "changed"}),
            content_type="application/json",
        )
        deleted = auth_client.delete(_message_url(message))

        assert edited.status_code == HTTPStatus.OK
        assert deleted.status_code == HTTPStatus.NO_CONTENT
        assert Message.objects.get(pk=message.pk).deleted_at is not None

    def test_an_unsent_attachment_can_be_removed_by_its_uploader(
        self, auth_client, freelancer, mine, attachment_factory
    ):
        attachment = attachment_factory(shot=mine, created_by=freelancer)

        response = auth_client.delete(_attachment_url(attachment))

        assert response.status_code == HTTPStatus.NO_CONTENT

    def test_the_hidden_shot_opens_up_when_a_task_is_assigned(
        self, auth_client, freelancer, other, message_factory, shot_task_factory
    ):
        message = message_factory(shot=other)
        shot_task_factory(shot=other, assignee=freelancer)

        response = auth_client.get(_message_url(message))

        assert response.status_code == HTTPStatus.OK


class TestRoleThatSeesEverything:
    def test_it_reaches_the_message_of_any_shot(
        self,
        auth_client,
        auth_user,
        project,
        other,
        message_factory,
        project_membership_factory,
    ):
        project_membership_factory(user=auth_user, project=project, role="executor")
        message = message_factory(shot=other)

        response = auth_client.get(_message_url(message))

        assert response.status_code == HTTPStatus.OK
