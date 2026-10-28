from http import HTTPStatus
from urllib.parse import urlencode

import pytest

from apps.chat.models import Message, Reaction
from apps.chat.tests.api.conftest import put_json


pytestmark = pytest.mark.django_db


def _url(message):
    return f"/api/v1/chat/{message.id}/reactions/"


def _remove_url(message, emoji):
    return f"{_url(message)}?{urlencode({'emoji': emoji})}"


class TestPutReaction:
    def test_puts_a_reaction(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot)

        response = put_json(auth_client, _url(message), {"emoji": "👍"})

        assert response.status_code == HTTPStatus.OK, response.content
        assert response.json() == {
            "reactions": [{"emoji": "👍", "user_ids": [auth_user.id]}]
        }
        reaction = Reaction.objects.get()
        assert reaction.created_by == auth_user
        assert reaction.created_at is not None

    def test_putting_the_same_emoji_again_changes_nothing(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot)
        put_json(auth_client, _url(message), {"emoji": "👍"})

        response = put_json(auth_client, _url(message), {"emoji": "👍"})

        assert response.status_code == HTTPStatus.OK
        assert response.json()["reactions"] == [
            {"emoji": "👍", "user_ids": [auth_user.id]}
        ]
        assert Reaction.objects.count() == 1

    def test_one_user_may_put_several_different_emoji(
        self, auth_client, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot)
        put_json(auth_client, _url(message), {"emoji": "👍"})

        response = put_json(auth_client, _url(message), {"emoji": "🔥"})

        assert [r["emoji"] for r in response.json()["reactions"]] == ["👍", "🔥"]

    def test_several_users_are_counted_together(
        self, auth_client, auth_user, member_shot, message_factory, reaction_factory
    ):
        message = message_factory(shot=member_shot)
        other = reaction_factory(message=message, emoji="👍")

        response = put_json(auth_client, _url(message), {"emoji": "👍"})

        reaction = response.json()["reactions"][0]
        assert reaction["user_ids"] == [other.created_by_id, auth_user.id]

    def test_can_react_to_a_system_message(self, auth_client, auth_user, member_shot):
        system = Message.objects.create(
            shot=member_shot,
            type=Message.Type.SYSTEM,
            event=Message.Event.TASK_ADDED,
            created_by=auth_user,
        )

        response = put_json(auth_client, _url(system), {"emoji": "👍"})

        assert response.status_code == HTTPStatus.OK

    def test_cannot_react_to_a_deleted_message(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot)
        message.mark_deleted(auth_user)

        response = put_json(auth_client, _url(message), {"emoji": "👍"})

        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize("emoji", ["", "a b", " ", "x" * 65])
    def test_rejects_an_invalid_emoji(
        self, auth_client, member_shot, message_factory, emoji
    ):
        message = message_factory(shot=member_shot)

        response = put_json(auth_client, _url(message), {"emoji": emoji})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_role_without_permission_cannot_react(
        self, auth_client, readonly_shot, message_factory
    ):
        message = message_factory(shot=readonly_shot)

        response = put_json(auth_client, _url(message), {"emoji": "👍"})

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_non_member_gets_a_404(
        self, auth_client, message_factory, project_membership_factory
    ):
        message = message_factory()
        project_membership_factory(project=message.shot.project)

        response = put_json(auth_client, _url(message), {"emoji": "👍"})

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestRemoveReaction:
    def test_removes_your_reaction(
        self, auth_client, auth_user, member_shot, message_factory, reaction_factory
    ):
        message = message_factory(shot=member_shot)
        reaction_factory(message=message, emoji="👍", created_by=auth_user)

        response = auth_client.delete(_remove_url(message, "👍"))

        assert response.status_code == HTTPStatus.OK, response.content
        assert response.json() == {"reactions": []}
        assert not Reaction.objects.exists()

    def test_does_not_touch_other_users_reactions(
        self, auth_client, auth_user, member_shot, message_factory, reaction_factory
    ):
        message = message_factory(shot=member_shot)
        reaction_factory(message=message, emoji="👍", created_by=auth_user)
        theirs = reaction_factory(message=message, emoji="👍")

        response = auth_client.delete(_remove_url(message, "👍"))

        assert response.json()["reactions"][0]["user_ids"] == [theirs.created_by_id]

    def test_removing_a_missing_reaction_changes_nothing(
        self, auth_client, member_shot, message_factory, reaction_factory
    ):
        message = message_factory(shot=member_shot)
        reaction_factory(message=message, emoji="🔥")

        response = auth_client.delete(_remove_url(message, "👍"))

        assert response.status_code == HTTPStatus.OK
        assert Reaction.objects.count() == 1

    def test_the_emoji_is_required(self, auth_client, member_shot, message_factory):
        message = message_factory(shot=member_shot)

        response = auth_client.delete(_url(message))

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_role_without_permission_cannot_remove(
        self, auth_client, readonly_shot, message_factory
    ):
        message = message_factory(shot=readonly_shot)

        response = auth_client.delete(_remove_url(message, "👍"))

        assert response.status_code == HTTPStatus.FORBIDDEN
