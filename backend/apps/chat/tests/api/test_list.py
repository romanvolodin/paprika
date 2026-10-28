from http import HTTPStatus

import pytest

from apps.chat.models import Message


pytestmark = pytest.mark.django_db


def _url(shot):
    return f"/api/v1/shots/{shot.id}/chat/"


def _ids(response):
    return [m["id"] for m in response.json()["items"]]


class TestListChat:
    def test_returns_the_messages_in_chronological_order(
        self, auth_client, member_shot, message_factory
    ):
        first = message_factory(shot=member_shot)
        second = message_factory(shot=member_shot)
        message_factory()  # some other shot

        response = auth_client.get(_url(member_shot))

        assert response.status_code == HTTPStatus.OK
        assert _ids(response) == [first.id, second.id]
        assert response.json()["has_older"] is False
        assert response.json()["has_newer"] is False

    def test_item_shape_of_a_user_message(
        self, auth_client, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot, text="Привет")

        item = auth_client.get(_url(member_shot)).json()["items"][0]

        assert item["id"] == message.id
        assert item["shot_id"] == member_shot.id
        assert item["type"] == "user"
        assert item["text"] == "Привет"
        assert item["event"] is None
        assert item["payload"] == {}
        assert item["reply_to"] is None
        assert item["versions"] == []
        assert item["attachments"] == []
        assert item["reactions"] == []
        assert item["edited_at"] is None
        assert item["created_by"]["id"] == message.created_by_id

    def test_the_default_page_is_the_last_50_messages(
        self, auth_client, member_shot, message_factory
    ):
        messages = [message_factory(shot=member_shot) for _ in range(55)]

        response = auth_client.get(_url(member_shot))

        assert _ids(response) == [m.id for m in messages[5:]]
        assert response.json()["has_older"] is True
        assert response.json()["has_newer"] is False

    def test_limit_returns_the_last_messages(
        self, auth_client, member_shot, message_factory
    ):
        messages = [message_factory(shot=member_shot) for _ in range(5)]

        response = auth_client.get(_url(member_shot), {"limit": 2})

        assert _ids(response) == [messages[3].id, messages[4].id]

    def test_before_loads_older_messages(
        self, auth_client, member_shot, message_factory
    ):
        messages = [message_factory(shot=member_shot) for _ in range(6)]

        response = auth_client.get(
            _url(member_shot), {"limit": 2, "before": messages[3].id}
        )

        assert _ids(response) == [messages[1].id, messages[2].id]
        assert response.json()["has_older"] is True
        assert response.json()["has_newer"] is True

    def test_before_the_oldest_message_returns_nothing(
        self, auth_client, member_shot, message_factory
    ):
        first = message_factory(shot=member_shot)

        response = auth_client.get(_url(member_shot), {"before": first.id})

        assert response.json() == {
            "items": [],
            "has_older": False,
            "has_newer": False,
        }

    def test_around_returns_a_window_including_the_message(
        self, auth_client, member_shot, message_factory
    ):
        messages = [message_factory(shot=member_shot) for _ in range(10)]

        response = auth_client.get(
            _url(member_shot), {"limit": 5, "around": messages[5].id}
        )

        assert _ids(response) == [m.id for m in messages[3:8]]
        assert response.json()["has_older"] is True
        assert response.json()["has_newer"] is True

    def test_around_near_the_end_fills_the_window_with_older_messages(
        self, auth_client, member_shot, message_factory
    ):
        messages = [message_factory(shot=member_shot) for _ in range(10)]

        response = auth_client.get(
            _url(member_shot), {"limit": 5, "around": messages[9].id}
        )

        assert _ids(response) == [m.id for m in messages[5:]]
        assert response.json()["has_newer"] is False

    def test_around_an_unknown_message_is_a_404(self, auth_client, member_shot):
        response = auth_client.get(_url(member_shot), {"around": 999999})

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_around_a_message_of_another_shot_is_a_404(
        self, auth_client, member_shot, message_factory
    ):
        other = message_factory()

        response = auth_client.get(_url(member_shot), {"around": other.id})

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_before_and_around_cannot_be_combined(
        self, auth_client, member_shot, message_factory
    ):
        message = message_factory(shot=member_shot)

        response = auth_client.get(
            _url(member_shot), {"before": message.id, "around": message.id}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_limit_is_capped(self, auth_client, member_shot):
        response = auth_client.get(_url(member_shot), {"limit": 101})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_deleted_messages_are_not_listed(
        self, auth_client, member_shot, message_factory, auth_user
    ):
        kept = message_factory(shot=member_shot)
        deleted = message_factory(shot=member_shot)
        deleted.mark_deleted(auth_user)

        response = auth_client.get(_url(member_shot))

        assert _ids(response) == [kept.id]

    def test_system_messages_are_in_the_same_list(
        self, auth_client, member_shot, message_factory, auth_user
    ):
        user_message = message_factory(shot=member_shot)
        system = Message.objects.create(
            shot=member_shot,
            type=Message.Type.SYSTEM,
            event=Message.Event.TASK_ADDED,
            payload={"task_code": "CLN1234"},
            created_by=auth_user,
        )

        response = auth_client.get(_url(member_shot))

        assert _ids(response) == [user_message.id, system.id]
        item = response.json()["items"][1]
        assert item["type"] == "system"
        assert item["event"] == "task_added"
        assert item["payload"] == {"task_code": "CLN1234"}
        assert item["text"] == ""

    def test_a_reply_carries_a_short_quote(
        self, auth_client, member_shot, message_factory
    ):
        quoted = message_factory(shot=member_shot, text="x" * 300)
        reply = message_factory(shot=member_shot, reply_to=quoted)

        items = auth_client.get(_url(member_shot)).json()["items"]

        quote = next(i for i in items if i["id"] == reply.id)["reply_to"]
        assert quote["id"] == quoted.id
        assert quote["text"] == "x" * 200
        assert quote["deleted"] is False
        assert quote["author"]["id"] == quoted.created_by_id

    def test_a_deleted_quoted_message_is_shown_as_deleted(
        self, auth_client, auth_user, member_shot, message_factory
    ):
        quoted = message_factory(shot=member_shot, text="secret")
        reply = message_factory(shot=member_shot, reply_to=quoted)
        quoted.mark_deleted(auth_user)

        items = auth_client.get(_url(member_shot)).json()["items"]

        assert [i["id"] for i in items] == [reply.id]
        assert items[0]["reply_to"]["deleted"] is True
        assert items[0]["reply_to"]["text"] == ""

    def test_reactions_are_collapsed_by_emoji(
        self, auth_client, member_shot, message_factory, reaction_factory, user_factory
    ):
        message = message_factory(shot=member_shot)
        first, second = user_factory(), user_factory()
        reaction_factory(message=message, emoji="👍", created_by=first)
        reaction_factory(message=message, emoji="🔥", created_by=first)
        reaction_factory(message=message, emoji="👍", created_by=second)

        item = auth_client.get(_url(member_shot)).json()["items"][0]

        assert item["reactions"] == [
            {"emoji": "👍", "user_ids": [first.id, second.id]},
            {"emoji": "🔥", "user_ids": [first.id]},
        ]

    def test_reactions_of_deleted_users_are_left_out(
        self, auth_client, member_shot, message_factory, reaction_factory, user_factory
    ):
        message = message_factory(shot=member_shot)
        gone, stays = user_factory(), user_factory()
        reaction_factory(message=message, emoji="🔥", created_by=gone)
        reaction_factory(message=message, emoji="👍", created_by=gone)
        reaction_factory(message=message, emoji="👍", created_by=stays)
        gone.delete()

        item = auth_client.get(_url(member_shot)).json()["items"][0]

        assert item["reactions"] == [{"emoji": "👍", "user_ids": [stays.id]}]

    def test_a_client_can_read(self, auth_client, readonly_shot):
        response = auth_client.get(_url(readonly_shot))

        assert response.status_code == HTTPStatus.OK

    def test_non_member_gets_a_404(self, auth_client, shot, project_membership_factory):
        project_membership_factory(project=shot.project)  # some other user

        response = auth_client.get(_url(shot))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot):
        response = client.get(_url(shot))

        assert response.status_code == HTTPStatus.UNAUTHORIZED
