from http import HTTPStatus
import os
import re

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from apps.core.storage import sanitize_name
from apps.versions.api.views import VersionListController
from apps.versions.models import Version
from apps.versions.tests.conftest import make_jpeg, make_png


pytestmark = pytest.mark.django_db


@pytest.fixture
def member_shot(auth_user, shot, project_membership_factory):
    """A shot in a project the logged-in user belongs to (default role)."""
    project_membership_factory(user=auth_user, project=shot.project)
    return shot


def _url(shot):
    return f"/api/v1/shots/{shot.id}/versions/"


def _upload(client, shot, name, data, content_type="application/octet-stream"):
    return client.post(
        _url(shot), {"source": SimpleUploadedFile(name, data, content_type)}
    )


def _stored_files(settings) -> list[str]:
    return [
        os.path.join(root, name)
        for root, _, names in os.walk(settings.MEDIA_ROOT)
        for name in names
    ]


class TestUploadVideo:
    def test_creates_a_version_from_an_mp4(
        self, auth_client, auth_user, member_shot, h264_video_bytes
    ):
        response = _upload(
            auth_client, member_shot, "PRJ_0060_v01.mp4", h264_video_bytes
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert body["name"] == "PRJ_0060_v01"
        assert body["type"] == "video"
        assert (body["width"], body["height"]) == (64, 64)
        assert body["duration"] == 9
        assert body["fps"] == pytest.approx(10)
        assert body["codec"] == "h264"
        assert body["file_size"] == len(h264_video_bytes)
        assert body["source"].endswith("/PRJ_0060_v01.mp4")
        assert body["thumb"].endswith(".jpg")
        assert body["converted"] is None
        assert body["created_by"]["id"] == auth_user.id
        assert body["shot_id"] == member_shot.id
        assert body["project_id"] == member_shot.project_id

    def test_stores_the_files(self, auth_client, member_shot, h264_video_bytes):
        _upload(auth_client, member_shot, "PRJ_0060_v01.mp4", h264_video_bytes)

        version = Version.objects.get()
        storage = version.source.storage
        assert storage.exists(version.source.name)
        assert storage.exists(version.thumb.name)
        assert version.updated_by is not None

    def test_files_are_stored_in_one_folder_inside_the_shot_folder(
        self, auth_client, member_shot, h264_video_bytes
    ):
        _upload(auth_client, member_shot, "PRJ_0060_v01.mp4", h264_video_bytes)

        version = Version.objects.get()
        project = member_shot.project
        folder = (
            rf"{project.company.storage_token}/{project.code}/shots/"
            rf"{sanitize_name(member_shot.name)}/versions/PRJ_0060_v01-[a-z0-9]{{8}}"
        )
        assert re.fullmatch(rf"{folder}/PRJ_0060_v01\.mp4", version.source.name)
        assert re.fullmatch(
            rf"{folder}/PRJ_0060_v01\.mp4_thumb\.jpg", version.thumb.name
        )
        assert (
            version.source.name.rpartition("/")[0]
            == (version.thumb.name.rpartition("/")[0])
        )

    def test_thumb_frame_position_comes_from_settings(
        self, auth_client, member_shot, h264_video_bytes, settings
    ):
        settings.VERSION_THUMB_FRAME_POSITION = 0.0

        response = _upload(auth_client, member_shot, "a.mp4", h264_video_bytes)

        assert response.status_code == HTTPStatus.CREATED

    def test_rejects_a_non_h264_codec(
        self, auth_client, member_shot, mpeg4_video_bytes, settings
    ):
        response = _upload(auth_client, member_shot, "a.mp4", mpeg4_video_bytes)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "codec" in response.content.decode()
        assert not Version.objects.exists()
        assert _stored_files(settings) == []

    def test_rejects_a_corrupt_mp4(self, auth_client, member_shot, settings):
        response = _upload(auth_client, member_shot, "a.mp4", b"not a video")

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert _stored_files(settings) == []


class TestUploadImage:
    def test_creates_a_version_from_a_jpg(self, auth_client, member_shot):
        response = _upload(
            auth_client, member_shot, "PRJ_0060_v02.jpg", make_jpeg((100, 80))
        )

        assert response.status_code == HTTPStatus.CREATED, response.content
        body = response.json()
        assert body["name"] == "PRJ_0060_v02"
        assert body["type"] == "image"
        assert (body["width"], body["height"]) == (100, 80)
        assert body["duration"] is None
        assert body["fps"] is None
        assert body["codec"] == ""
        assert body["thumb"] is not None

    def test_creates_a_version_from_a_png(self, auth_client, member_shot):
        response = _upload(auth_client, member_shot, "PRJ_0060_v03.png", make_png())

        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()["type"] == "image"

    def test_extension_is_case_insensitive(self, auth_client, member_shot):
        response = _upload(auth_client, member_shot, "PRJ_0060_v04.JPG", make_jpeg())

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["name"] == "PRJ_0060_v04"

    def test_only_the_last_extension_is_dropped_from_the_name(
        self, auth_client, member_shot
    ):
        response = _upload(
            auth_client, member_shot, "PRJ_0060.final_v01.png", make_png()
        )

        assert response.json()["name"] == "PRJ_0060.final_v01"

    def test_rejects_contents_that_do_not_match_the_extension(
        self, auth_client, member_shot
    ):
        response = _upload(auth_client, member_shot, "a.jpg", make_png())

        assert response.status_code == HTTPStatus.BAD_REQUEST


class TestUploadValidation:
    @pytest.mark.parametrize(
        "name", ["clip.mov", "clip.gif", "clip.exr", "clip", ".mp4"]
    )
    def test_rejects_unsupported_names(self, auth_client, member_shot, name):
        response = _upload(auth_client, member_shot, name, b"data")

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Version.objects.exists()

    def test_requires_the_source_file(self, auth_client, member_shot):
        response = auth_client.post(_url(member_shot), {})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_files_over_the_size_limit_get_a_413(
        self, auth_client, member_shot, settings
    ):
        settings.VERSION_MAX_FILE_SIZE_MB = 0

        response = _upload(auth_client, member_shot, "a.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert not Version.objects.exists()

    def test_the_size_limit_comes_from_settings(
        self, auth_client, member_shot, settings
    ):
        settings.VERSION_MAX_FILE_SIZE_MB = 1

        response = _upload(auth_client, member_shot, "a.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.CREATED


class TestDuplicateNames:
    def test_a_duplicate_name_in_the_same_shot_gets_a_409(
        self, auth_client, member_shot, version_factory, settings
    ):
        version_factory(shot=member_shot, name="PRJ_0060_v01")
        before = _stored_files(settings)

        response = _upload(auth_client, member_shot, "PRJ_0060_v01.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.CONFLICT
        assert "PRJ_0060_v01" in response.content.decode()
        assert Version.objects.count() == 1
        assert _stored_files(settings) == before

    def test_uniqueness_is_per_project_not_per_shot(
        self, auth_client, member_shot, shot_factory, version_factory
    ):
        other_shot_same_project = shot_factory(project=member_shot.project)
        version_factory(shot=other_shot_same_project, name="PRJ_0060_v01")

        response = _upload(auth_client, member_shot, "PRJ_0060_v01.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.CONFLICT

    def test_the_same_name_is_allowed_in_another_project(
        self, auth_client, member_shot, version_factory
    ):
        version_factory(name="PRJ_0060_v01")  # unrelated project

        response = _upload(auth_client, member_shot, "PRJ_0060_v01.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.CREATED

    def test_losing_a_race_is_a_409_and_leaves_no_files_behind(
        self, auth_client, member_shot, version_factory, settings, mocker
    ):
        version_factory(shot=member_shot, name="PRJ_0060_v01")
        before = _stored_files(settings)
        # Simulate another upload slipping in between the cheap name check
        # and the insert: the check says "free", the DB constraint disagrees.
        mocker.patch.object(VersionListController, "_name_taken", return_value=False)

        response = _upload(auth_client, member_shot, "PRJ_0060_v01.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.CONFLICT
        assert Version.objects.count() == 1
        assert _stored_files(settings) == before


class TestUploadPermissions:
    def test_read_only_client_gets_a_403(
        self, auth_client, auth_user, shot, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=shot.project, role="client")

        response = _upload(auth_client, shot, "a.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not Version.objects.exists()

    @pytest.mark.parametrize(
        "role", ["admin", "producer", "coordinator", "executor", "freelancer"]
    )
    def test_other_roles_can_upload(
        self,
        auth_client,
        auth_user,
        shot,
        project_membership_factory,
        shot_task_factory,
        role,
    ):
        project_membership_factory(user=auth_user, project=shot.project, role=role)
        shot_task_factory(shot=shot, assignee=auth_user)

        response = _upload(auth_client, shot, "a.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.CREATED

    def test_non_member_gets_a_404(self, auth_client, shot, project_membership_factory):
        project_membership_factory(project=shot.project)  # some other user

        response = _upload(auth_client, shot, "a.jpg", make_jpeg())

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert not Version.objects.exists()

    def test_requires_authentication(self, client, shot):
        response = client.post(
            _url(shot), {"source": SimpleUploadedFile("a.jpg", make_jpeg())}
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
