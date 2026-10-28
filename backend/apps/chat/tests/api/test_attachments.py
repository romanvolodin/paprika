from http import HTTPStatus
import os
import re

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from apps.chat.models import Attachment


pytestmark = pytest.mark.django_db


def _upload_url(shot):
    return f"/api/v1/shots/{shot.id}/chat/attachments/"


def _detail_url(attachment):
    return f"/api/v1/chat/attachments/{attachment.id}/"


def _upload(client, shot, name="notes.txt", data=b"hello", content_type="text/plain"):
    return client.post(
        _upload_url(shot), {"file": SimpleUploadedFile(name, data, content_type)}
    )


def _stored_files(settings) -> list[str]:
    return [
        os.path.join(root, name)
        for root, _, names in os.walk(settings.MEDIA_ROOT)
        for name in names
    ]


class TestUploadAttachment:
    def test_uploads_a_file(self, auth_client, auth_user, member_shot):
        response = _upload(auth_client, member_shot, "заметки.txt", b"hello")

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert body["filename"] == "заметки.txt"
        assert body["size"] == 5
        assert body["content_type"] == "text/plain"
        assert "/chat/" in body["url"]
        attachment = Attachment.objects.get(pk=body["id"])
        assert re.search(
            r"/chat/\d{4}-\d{2}-\d{2}/заметки-[a-z0-9]{8}\.txt$", attachment.file.name
        )
        assert attachment.shot == member_shot
        assert attachment.message is None
        assert attachment.created_by == auth_user

    def test_any_file_type_is_accepted(self, auth_client, member_shot):
        for name in ("scene.nk", "shot.exr", "archive.zip", "page.html", "noext"):
            response = _upload(
                auth_client, member_shot, name, b"x", "application/octet-stream"
            )

            assert response.status_code == HTTPStatus.CREATED, name

    def test_the_path_is_unguessable_and_keeps_the_name(self, auth_client, member_shot):
        first = _upload(auth_client, member_shot, "same.txt").json()
        second = _upload(auth_client, member_shot, "same.txt").json()

        assert first["url"] != second["url"]
        assert re.search(r"/same-[a-z0-9]{8}\.txt$", first["url"])

    def test_a_path_in_the_name_is_dropped(self, auth_client, member_shot):
        response = _upload(auth_client, member_shot, "../../etc/passwd")

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["filename"] == "passwd"

    def test_rejects_a_too_large_file_with_413(
        self, auth_client, member_shot, settings
    ):
        settings.CHAT_ATTACHMENT_MAX_FILE_SIZE_MB = 1

        too_large = _upload(auth_client, member_shot, data=b"x" * (1024 * 1024 + 1))
        fits = _upload(auth_client, member_shot, data=b"x" * (1024 * 1024))

        assert too_large.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert fits.status_code == HTTPStatus.CREATED
        assert Attachment.objects.count() == 1

    def test_default_limit_is_100_mb(self, settings):
        assert settings.CHAT_ATTACHMENT_MAX_FILE_SIZE_MB == 100

    def test_the_file_field_is_required(self, auth_client, member_shot):
        response = auth_client.post(_upload_url(member_shot), {})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_role_without_permission_cannot_upload(self, auth_client, readonly_shot):
        response = _upload(auth_client, readonly_shot)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_non_member_gets_a_404(self, auth_client, shot, project_membership_factory):
        project_membership_factory(project=shot.project)  # some other user

        response = _upload(auth_client, shot)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot):
        response = _upload(client, shot)

        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestRemoveAttachment:
    def test_removes_an_unsent_file_and_its_storage(
        self,
        auth_client,
        auth_user,
        member_shot,
        attachment_factory,
        django_capture_on_commit_callbacks,
    ):
        attachment = attachment_factory(shot=member_shot, created_by=auth_user)
        stored = attachment.file.path
        assert os.path.exists(stored)

        with django_capture_on_commit_callbacks(execute=True):
            response = auth_client.delete(_detail_url(attachment))

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Attachment.objects.filter(pk=attachment.pk).exists()
        assert not os.path.exists(stored)

    def test_cannot_remove_a_file_that_is_in_a_message(
        self, auth_client, auth_user, member_shot, message_factory, attachment_factory
    ):
        message = message_factory(shot=member_shot)
        attachment = attachment_factory(
            shot=member_shot, created_by=auth_user, message=message
        )

        response = auth_client.delete(_detail_url(attachment))

        assert response.status_code == HTTPStatus.CONFLICT
        assert Attachment.objects.filter(pk=attachment.pk).exists()

    def test_cannot_remove_someone_elses_file(
        self, auth_client, member_shot, attachment_factory
    ):
        attachment = attachment_factory(shot=member_shot)

        response = auth_client.delete(_detail_url(attachment))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_role_without_permission_cannot_remove(
        self, auth_client, auth_user, readonly_shot, attachment_factory
    ):
        attachment = attachment_factory(shot=readonly_shot, created_by=auth_user)

        response = auth_client.delete(_detail_url(attachment))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_non_member_gets_a_404(
        self, auth_client, attachment_factory, project_membership_factory
    ):
        attachment = attachment_factory()
        project_membership_factory(project=attachment.shot.project)

        response = auth_client.delete(_detail_url(attachment))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_deleting_a_shot_removes_its_attachments_files(
        self,
        member_shot,
        attachment_factory,
        django_capture_on_commit_callbacks,
        settings,
    ):
        attachment_factory(shot=member_shot)
        assert _stored_files(settings)

        with django_capture_on_commit_callbacks(execute=True):
            member_shot.delete()

        assert not Attachment.objects.exists()
        assert not _stored_files(settings)
