import datetime as dt
from http import HTTPStatus

from django.utils import timezone
import pytest

from apps.chat.models import Message


pytestmark = pytest.mark.django_db


def _url(project):
    return f"/api/v1/projects/{project.id}/feed/"


def _keys(response):
    return [item["key"] for item in response.json()["items"]]


def _days_ago(days: float) -> dt.datetime:
    return timezone.now() - dt.timedelta(days=days)


@pytest.fixture
def system_message(message_factory):
    def _make(shot, event=Message.Event.STATUS_CHANGED, **kwargs):
        return message_factory(
            shot=shot,
            type=Message.Type.SYSTEM,
            event=event,
            text="",
            payload={"task_code": "CLN1234", "task_name": "Клинап"},
            **kwargs,
        )

    return _make


class TestAccess:
    def test_requires_authentication(self, client, project):
        response = client.get(_url(project))

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_not_a_member_is_404(self, auth_client, project_factory):
        response = auth_client.get(_url(project_factory()))

        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize("role", ["client", "freelancer"])
    def test_role_without_the_feed_permission_gets_a_403(
        self, auth_client, auth_user, project_factory, project_membership_factory, role
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project, role=role)

        response = auth_client.get(_url(project))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_executor_can_read(
        self, auth_client, auth_user, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(user=auth_user, project=project, role="executor")

        response = auth_client.get(_url(project))

        assert response.status_code == HTTPStatus.OK


class TestContent:
    def test_empty_project(self, auth_client, project):
        response = auth_client.get(_url(project))

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"items": [], "next_before_date": None}

    def test_merges_messages_versions_and_task_events_newest_first(
        self,
        auth_client,
        project,
        shot_factory,
        message_factory,
        version_factory,
        system_message,
        at,
    ):
        shot = shot_factory(project=project)
        message = at(message_factory(shot=shot), _days_ago(3))
        version = at(version_factory(shot=shot), _days_ago(2))
        task_event = at(system_message(shot), _days_ago(1))

        response = auth_client.get(_url(project))

        assert _keys(response) == [
            f"task-{task_event.id}",
            f"version-{version.id}",
            f"chat-{message.id}",
        ]

    def test_events_of_other_projects_are_left_out(
        self, auth_client, project, message_factory, version_factory
    ):
        message_factory()
        version_factory()

        assert auth_client.get(_url(project)).json()["items"] == []

    def test_deleted_messages_are_left_out(
        self, auth_client, project, shot_factory, message_factory, auth_user
    ):
        shot = shot_factory(project=project)
        message = message_factory(shot=shot)
        message.mark_deleted(auth_user)

        assert auth_client.get(_url(project)).json()["items"] == []

    def test_version_upload_system_message_does_not_duplicate_the_version(
        self, auth_client, project, shot_factory, version_factory, system_message
    ):
        shot = shot_factory(project=project)
        version = version_factory(shot=shot)
        system_message(shot, event=Message.Event.VERSION_UPLOADED)

        response = auth_client.get(_url(project))

        assert _keys(response) == [f"version-{version.id}"]

    @pytest.mark.parametrize(
        "event",
        [
            Message.Event.TASK_ADDED,
            Message.Event.STATUS_CHANGED,
            Message.Event.ASSIGNEE_CHANGED,
        ],
    )
    def test_task_events_are_included(
        self, auth_client, project, shot_factory, system_message, event
    ):
        shot = shot_factory(project=project)
        message = system_message(shot, event=event)

        assert _keys(auth_client.get(_url(project))) == [f"task-{message.id}"]

    def test_shape_of_a_chat_item(
        self,
        auth_client,
        project,
        shot_factory,
        message_factory,
        attachment_factory,
        version_factory,
    ):
        shot = shot_factory(project=project)
        message = message_factory(shot=shot, text="Привет")
        attachment = attachment_factory(shot=shot, message=message)
        version = version_factory(shot=shot)
        message.versions.add(version)

        items = auth_client.get(_url(project)).json()["items"]
        item = next(i for i in items if i["type"] == "chat")

        assert item["key"] == f"chat-{message.id}"
        assert item["type"] == "chat"
        assert item["shot"] == {"id": shot.id, "name": shot.name}
        assert item["created_by"]["id"] == message.created_by_id
        assert item["text"] == "Привет"
        assert [a["id"] for a in item["attachments"]] == [attachment.id]
        assert [v["id"] for v in item["versions"]] == [version.id]
        assert item["version"] is None
        assert item["event"] is None
        assert item["payload"] == {}

    def test_shape_of_a_version_item(
        self, auth_client, project, shot_factory, version_factory
    ):
        shot = shot_factory(project=project)
        version = version_factory(shot=shot)

        item = auth_client.get(_url(project)).json()["items"][0]

        assert item["key"] == f"version-{version.id}"
        assert item["type"] == "version"
        assert item["version"]["id"] == version.id
        assert item["version"]["name"] == version.name
        assert item["version"]["thumb"].startswith("http")
        assert item["text"] is None
        assert item["attachments"] == []
        assert item["versions"] == []

    def test_shape_of_a_task_item(
        self, auth_client, project, shot_factory, system_message
    ):
        shot = shot_factory(project=project)
        system_message(shot, event=Message.Event.TASK_ADDED)

        item = auth_client.get(_url(project)).json()["items"][0]

        assert item["type"] == "task"
        assert item["event"] == "task_added"
        assert item["payload"]["task_code"] == "CLN1234"
        assert item["text"] is None


class TestFilters:
    @pytest.fixture
    def events(
        self, project, shot_factory, message_factory, version_factory, system_message
    ):
        shot = shot_factory(project=project)
        return {
            "chat": message_factory(shot=shot),
            "task": system_message(shot),
            "version": version_factory(shot=shot),
        }

    def test_one_type(self, auth_client, project, events):
        response = auth_client.get(_url(project), {"type": "version"})

        assert _keys(response) == [f"version-{events['version'].id}"]

    def test_several_types(self, auth_client, project, events):
        response = auth_client.get(_url(project), {"type": "chat,task"})

        assert sorted(_keys(response)) == sorted(
            [f"chat-{events['chat'].id}", f"task-{events['task'].id}"]
        )

    def test_unknown_type_is_rejected(self, auth_client, project):
        response = auth_client.get(_url(project), {"type": "chat,nonsense"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_empty_type_is_rejected(self, auth_client, project):
        response = auth_client.get(_url(project), {"type": ","})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_mine_keeps_only_shots_with_a_task_assigned_to_me(
        self,
        auth_client,
        auth_user,
        user_factory,
        project,
        shot_factory,
        shot_task_factory,
        message_factory,
        version_factory,
        system_message,
    ):
        my_shot = shot_factory(project=project)
        shot_task_factory(shot=my_shot, assignee=auth_user)
        shot_task_factory(shot=my_shot, assignee=user_factory())
        someone_elses = shot_factory(project=project)
        shot_task_factory(shot=someone_elses, assignee=user_factory())
        unassigned = shot_factory(project=project)
        shot_task_factory(shot=unassigned)

        message_factory(shot=my_shot)
        system_message(my_shot)
        version_factory(shot=my_shot)
        for shot in (someone_elses, unassigned):
            message_factory(shot=shot)
            system_message(shot)
            version_factory(shot=shot)

        response = auth_client.get(_url(project), {"mine": "true"})

        assert len(_keys(response)) == 3
        assert {item["shot"]["id"] for item in response.json()["items"]} == {my_shot.id}
        assert {key.split("-")[0] for key in _keys(response)} == {
            "chat",
            "task",
            "version",
        }

    def test_mine_does_not_duplicate_events_of_a_shot_with_several_tasks(
        self,
        auth_client,
        auth_user,
        project,
        shot_factory,
        shot_task_factory,
        message_factory,
    ):
        shot = shot_factory(project=project)
        shot_task_factory(shot=shot, assignee=auth_user)
        shot_task_factory(shot=shot, assignee=auth_user)
        message = message_factory(shot=shot)

        response = auth_client.get(_url(project), {"mine": "true"})

        assert _keys(response) == [f"chat-{message.id}"]

    def test_mine_and_type_combine(
        self,
        auth_client,
        auth_user,
        project,
        shot_factory,
        shot_task_factory,
        message_factory,
        version_factory,
    ):
        shot = shot_factory(project=project)
        shot_task_factory(shot=shot, assignee=auth_user)
        message_factory(shot=shot)
        version = version_factory(shot=shot)

        response = auth_client.get(_url(project), {"mine": "true", "type": "version"})

        assert _keys(response) == [f"version-{version.id}"]


class TestWindow:
    def test_a_slice_covers_five_days(
        self, auth_client, project, shot_factory, message_factory, at
    ):
        shot = shot_factory(project=project)
        recent = at(message_factory(shot=shot), _days_ago(1))
        edge = at(message_factory(shot=shot), _days_ago(5.5))
        at(message_factory(shot=shot), _days_ago(7))

        response = auth_client.get(_url(project))

        assert _keys(response) == [f"chat-{recent.id}", f"chat-{edge.id}"]
        assert response.json()["next_before_date"] is not None

    def test_next_slice_goes_older_and_the_last_one_has_no_cursor(
        self, auth_client, project, shot_factory, message_factory, at
    ):
        shot = shot_factory(project=project)
        first = at(message_factory(shot=shot), _days_ago(1))
        second = at(message_factory(shot=shot), _days_ago(8))
        third = at(message_factory(shot=shot), _days_ago(20))

        page_one = auth_client.get(_url(project)).json()
        page_two = auth_client.get(
            _url(project), {"before_date": page_one["next_before_date"]}
        ).json()
        page_three = auth_client.get(
            _url(project), {"before_date": page_two["next_before_date"]}
        ).json()

        assert [i["key"] for i in page_one["items"]] == [f"chat-{first.id}"]
        assert [i["key"] for i in page_two["items"]] == [f"chat-{second.id}"]
        assert [i["key"] for i in page_three["items"]] == [f"chat-{third.id}"]
        assert page_three["next_before_date"] is None

    def test_event_exactly_on_the_boundary_is_not_lost(
        self, auth_client, project, shot_factory, message_factory, at
    ):
        shot = shot_factory(project=project)
        newest_at = _days_ago(1)
        newest = at(message_factory(shot=shot), newest_at)
        on_boundary = at(message_factory(shot=shot), newest_at - dt.timedelta(days=5))

        page_one = auth_client.get(_url(project)).json()
        keys = [i["key"] for i in page_one["items"]]
        if page_one["next_before_date"] is not None:
            page_two = auth_client.get(
                _url(project), {"before_date": page_one["next_before_date"]}
            ).json()
            keys += [i["key"] for i in page_two["items"]]

        assert keys == [f"chat-{newest.id}", f"chat-{on_boundary.id}"]

    def test_quiet_period_does_not_give_an_empty_slice(
        self, auth_client, project, shot_factory, message_factory, at
    ):
        shot = shot_factory(project=project)
        new = at(message_factory(shot=shot), _days_ago(1))
        old = at(message_factory(shot=shot), _days_ago(60))

        page_one = auth_client.get(_url(project)).json()
        page_two = auth_client.get(
            _url(project), {"before_date": page_one["next_before_date"]}
        ).json()

        assert [i["key"] for i in page_one["items"]] == [f"chat-{new.id}"]
        assert [i["key"] for i in page_two["items"]] == [f"chat-{old.id}"]

    def test_the_cursor_respects_the_filters(
        self, auth_client, project, shot_factory, message_factory, version_factory, at
    ):
        shot = shot_factory(project=project)
        at(message_factory(shot=shot), _days_ago(1))
        at(version_factory(shot=shot), _days_ago(30))

        response = auth_client.get(_url(project), {"type": "chat"})

        assert len(response.json()["items"]) == 1
        assert response.json()["next_before_date"] is None
