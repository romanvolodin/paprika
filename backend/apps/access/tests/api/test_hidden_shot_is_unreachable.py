"""One scenario for the whole of "what a Фрилансер sees".

A project with two shots; the user holds a role with every permission but
`sees_all_shots` off, and is assigned to a task on the first shot only.
Every address that reaches a shot, or something that belongs to it, must
answer 404 for the second shot - even though the role is allowed to do
everything - and keep working for the first.
"""

from dataclasses import dataclass
from http import HTTPStatus
import json
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from apps.access.permissions import PROJECT_CODES
from apps.versions.tests.conftest import make_jpeg


pytestmark = pytest.mark.django_db


@dataclass
class Things:
    """Everything that hangs off one shot."""

    shot: Any
    group: Any
    version: Any
    message: Any
    attachment: Any
    shot_task: Any
    task: Any


@pytest.fixture
def project(project_factory):
    return project_factory()


@pytest.fixture
def user(auth_user, project, role_factory, project_membership_factory):
    role = role_factory(
        company=project.company,
        permissions=sorted(PROJECT_CODES),
        sees_all_shots=False,
    )
    project_membership_factory(user=auth_user, project=project, role=role)
    return auth_user


@pytest.fixture
def build(
    project,
    shot_factory,
    shot_group_factory,
    version_factory,
    message_factory,
    attachment_factory,
    task_factory,
    shot_task_factory,
):
    def _build(name, assignee=None):
        shot = shot_factory(project=project, name=name)
        group = shot_group_factory(project=project, name=f"G-{name}")
        shot.groups.set([group])
        task = task_factory(project=project, name=f"Задача {name}")
        return Things(
            shot=shot,
            group=group,
            version=version_factory(shot=shot),
            message=message_factory(shot=shot),
            attachment=attachment_factory(shot=shot, created_by=assignee),
            shot_task=shot_task_factory(shot=shot, task=task, assignee=assignee),
            task=task,
        )

    return _build


@pytest.fixture
def visible(build, user):
    return build("SEEN", assignee=user)


@pytest.fixture
def hidden(build, visible):
    return build("HIDDEN")


def _json(client_method, url, body):
    return client_method(url, data=json.dumps(body), content_type="application/json")


def _upload_version(client, url, _body):
    return client.post(
        url, {"source": SimpleUploadedFile("a.jpg", make_jpeg(), "image/jpeg")}
    )


def _upload_attachment(client, url, _body):
    return client.post(
        url, {"file": SimpleUploadedFile("n.txt", b"hello", "text/plain")}
    )


def _requests(t: Things, extra_task_id: int):
    """(label, send(client)) for every address that reaches `t`."""
    shot_url = f"/api/v1/shots/{t.shot.id}/"
    return [
        ("shot GET", lambda c: c.get(shot_url)),
        ("shot PATCH", lambda c: _json(c.patch, shot_url, {"group_ids": []})),
        ("shot DELETE", lambda c: c.delete(shot_url)),
        ("versions GET", lambda c: c.get(f"{shot_url}versions/")),
        ("versions POST", lambda c: _upload_version(c, f"{shot_url}versions/", None)),
        ("chat GET", lambda c: c.get(f"{shot_url}chat/")),
        ("chat POST", lambda c: _json(c.post, f"{shot_url}chat/", {"text": "hi"})),
        (
            "chat attachment POST",
            lambda c: _upload_attachment(c, f"{shot_url}chat/attachments/", None),
        ),
        ("shot tasks GET", lambda c: c.get(f"{shot_url}tasks/")),
        (
            "shot tasks POST",
            lambda c: _json(c.post, f"{shot_url}tasks/", {"task_id": extra_task_id}),
        ),
        ("version GET", lambda c: c.get(f"/api/v1/versions/{t.version.id}/")),
        ("version DELETE", lambda c: c.delete(f"/api/v1/versions/{t.version.id}/")),
        ("message GET", lambda c: c.get(f"/api/v1/chat/{t.message.id}/")),
        (
            "message PATCH",
            lambda c: _json(c.patch, f"/api/v1/chat/{t.message.id}/", {"text": "x"}),
        ),
        ("message DELETE", lambda c: c.delete(f"/api/v1/chat/{t.message.id}/")),
        (
            "reaction PUT",
            lambda c: _json(
                c.put, f"/api/v1/chat/{t.message.id}/reactions/", {"emoji": "🔥"}
            ),
        ),
        (
            "reaction DELETE",
            lambda c: c.delete(f"/api/v1/chat/{t.message.id}/reactions/?emoji=🔥"),
        ),
        (
            "attachment DELETE",
            lambda c: c.delete(f"/api/v1/chat/attachments/{t.attachment.id}/"),
        ),
        ("shot task GET", lambda c: c.get(f"/api/v1/shot-tasks/{t.shot_task.id}/")),
        (
            "shot task PATCH",
            lambda c: _json(
                c.patch, f"/api/v1/shot-tasks/{t.shot_task.id}/", {"actual_hours": 1}
            ),
        ),
        (
            "shot task DELETE",
            lambda c: c.delete(f"/api/v1/shot-tasks/{t.shot_task.id}/"),
        ),
        ("task GET", lambda c: c.get(f"/api/v1/tasks/{t.task.id}/")),
        (
            "task PATCH",
            lambda c: _json(c.patch, f"/api/v1/tasks/{t.task.id}/", {"name": "N"}),
        ),
        ("task DELETE", lambda c: c.delete(f"/api/v1/tasks/{t.task.id}/")),
        ("group GET", lambda c: c.get(f"/api/v1/shot-groups/{t.group.id}/")),
        (
            "group shots GET",
            lambda c: c.get(f"/api/v1/shot-groups/{t.group.id}/shots/"),
        ),
        (
            "group PATCH",
            lambda c: _json(
                c.patch, f"/api/v1/shot-groups/{t.group.id}/", {"name": "N"}
            ),
        ),
        ("group DELETE", lambda c: c.delete(f"/api/v1/shot-groups/{t.group.id}/")),
    ]


def _labels():
    placeholder = Things(*([type("Stub", (), {"id": 0})()] * 7))
    return [label for label, _ in _requests(placeholder, 0)]


@pytest.fixture
def spare_task(project, task_factory):
    return task_factory(project=project, name="Запасная")


@pytest.mark.parametrize("label", _labels())
def test_a_hidden_shot_and_everything_on_it_answers_404(
    auth_client, user, visible, hidden, spare_task, label
):
    send = dict(_requests(hidden, spare_task.id))[label]

    response = send(auth_client)

    assert response.status_code == HTTPStatus.NOT_FOUND, label


@pytest.mark.parametrize("label", _labels())
def test_the_assigned_shot_and_everything_on_it_stays_reachable(
    auth_client, user, visible, hidden, spare_task, label
):
    send = dict(_requests(visible, spare_task.id))[label]

    response = send(auth_client)

    assert response.status_code != HTTPStatus.NOT_FOUND, (label, response.content)


class TestEverythingThatListsThings:
    def test_each_list_holds_only_what_belongs_to_the_assigned_shot(
        self, auth_client, user, project, visible, hidden, shot_task_factory
    ):
        colleague_elsewhere = hidden.shot_task
        pid = project.id

        shots = auth_client.get(f"/api/v1/projects/{pid}/shots/").json()
        groups = auth_client.get(f"/api/v1/projects/{pid}/shot-groups/").json()
        tasks = auth_client.get(f"/api/v1/projects/{pid}/tasks/").json()
        filters = auth_client.get(f"/api/v1/projects/{pid}/shot-filters/").json()
        feed = auth_client.get(f"/api/v1/projects/{pid}/feed/").json()
        members = auth_client.get(f"/api/v1/projects/{pid}/members/").json()

        assert [s["id"] for s in shots["items"]] == [visible.shot.id]
        assert [g["id"] for g in groups["items"]] == [visible.group.id]
        assert [t["id"] for t in tasks["items"]] == [visible.task.id]
        assert {i["shot"]["id"] for i in feed["items"]} == {visible.shot.id}
        assert filters["assignee_ids"] == [user.id]
        assert {m["user_id"] for m in members["items"]} == {user.id}
        assert colleague_elsewhere.shot_id == hidden.shot.id
