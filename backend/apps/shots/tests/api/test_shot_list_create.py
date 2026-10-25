from http import HTTPStatus
import json

import pytest

from apps.shots.models import Shot


pytestmark = pytest.mark.django_db


def _post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


class TestListShotsByProject:
    def test_returns_every_shot_in_the_project_regardless_of_group(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
        shot_group_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        group = shot_group_factory(project=project)
        shot_factory(project=project, name="Grouped", groups=[group])
        shot_factory(project=project, name="Ungrouped")

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        names = {item["name"] for item in body["items"]}
        assert names == {"Grouped", "Ungrouped"}

    def test_search_filters_by_name(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot_factory(project=project, name="Findable")
        shot_factory(project=project, name="Other")

        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shots/?search=findable"
        )

        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Findable"

    def test_name_filters_by_exact_name_not_by_substring(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot_factory(project=project, name="0010")
        shot_factory(project=project, name="00100")
        shot_factory(project=project, name="A0010")

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/?name=0010")

        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "0010"

    def test_page_size_up_to_500_is_accepted(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shots/?page_size=500"
        )

        assert response.status_code == 200
        assert response.json()["page_size"] == 500

    def test_page_size_over_500_is_rejected(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = auth_client.get(
            f"/api/v1/projects/{project.id}/shots/?page_size=501"
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_of_project_gets_404(
        self, auth_client, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(project=project)  # some other user

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project):
        response = client.get(f"/api/v1/projects/{project.id}/shots/")

        assert response.status_code == 401


class TestListShotsByGroup:
    def test_returns_only_shots_in_that_group(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
        shot_group_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        group_a = shot_group_factory(project=project, name="A")
        group_b = shot_group_factory(project=project, name="B")
        shot_factory(project=project, name="In A", groups=[group_a])
        shot_factory(project=project, name="In B", groups=[group_b])
        shot_factory(project=project, name="In Both", groups=[group_a, group_b])
        shot_factory(project=project, name="In Neither")

        response = auth_client.get(f"/api/v1/shot-groups/{group_a.id}/shots/")

        body = response.json()
        names = {item["name"] for item in body["items"]}
        assert names == {"In A", "In Both"}

    def test_non_member_of_project_gets_404(
        self, auth_client, shot_group_factory, project_membership_factory
    ):
        shot_group = shot_group_factory()
        project_membership_factory(project=shot_group.project)  # some other user

        response = auth_client.get(f"/api/v1/shot-groups/{shot_group.id}/shots/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, shot_group):
        response = client.get(f"/api/v1/shot-groups/{shot_group.id}/shots/")

        assert response.status_code == 401


class TestCreateShot:
    def test_creates_a_shot_with_no_groups(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010"},
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["name"] == "0010"
        assert body["project_id"] == project.id
        assert body["group_ids"] == []
        assert body["rec_timecode"] is None
        assert body["duration"] is None

    def test_creates_a_shot_with_groups_and_timing_fields(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_group_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        group_a = shot_group_factory(project=project)
        group_b = shot_group_factory(project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {
                "name": "0010",
                "group_ids": [group_a.id, group_b.id],
                "rec_timecode": 3600,
                "duration": 48,
            },
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert set(body["group_ids"]) == {group_a.id, group_b.id}
        assert body["rec_timecode"] == 3600
        assert body["duration"] == 48

    def test_can_belong_to_several_groups_simultaneously(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_group_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        group_a = shot_group_factory(project=project)
        group_b = shot_group_factory(project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "group_ids": [group_a.id, group_b.id]},
        )

        shot = Shot.objects.get(id=response.json()["id"])
        assert shot.groups.count() == 2

    def test_defaults_to_the_companys_default_status(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)
        default_status = project.company.shot_statuses.get(is_default=True)

        response = _post_json(
            auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": "0010"}
        )

        assert response.json()["status_id"] == default_status.id

    def test_creates_with_an_explicit_status_id(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_status_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        status = shot_status_factory(company=project.company, name="Blocked")

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "status_id": status.id},
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["status_id"] == status.id

    def test_rejects_a_status_from_a_different_company(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_status_factory,
        company_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        foreign_status = shot_status_factory(company=company_factory())

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "status_id": foreign_status.id},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Shot.objects.filter(project=project, name="0010").exists()

    def test_rejects_an_unknown_status_id(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "status_id": 999999},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_fails_when_company_has_no_default_status_and_none_given(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)
        project.company.shot_statuses.update(is_default=False)

        response = _post_json(
            auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": "0010"}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_a_group_from_a_different_project(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_group_factory,
        project_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        other_project = project_factory()
        foreign_group = shot_group_factory(project=other_project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "group_ids": [foreign_group.id]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Shot.objects.filter(project=project, name="0010").exists()

    def test_rejects_an_unknown_group_id(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "group_ids": [999999]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_duplicate_name_within_project(
        self, auth_client, auth_user, project, project_membership_factory, shot_factory
    ):
        project_membership_factory(user=auth_user, project=project)
        shot_factory(project=project, name="0010")

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_same_name_allowed_in_a_different_project(
        self,
        auth_client,
        auth_user,
        project_factory,
        project_membership_factory,
        shot_factory,
    ):
        other_project = project_factory()
        shot_factory(project=other_project, name="0010")
        my_project = project_factory()
        project_membership_factory(user=auth_user, project=my_project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{my_project.id}/shots/",
            {"name": "0010"},
        )

        assert response.status_code == HTTPStatus.CREATED

    def test_rejects_blank_name(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": ""}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize(
        "name", ["PRJ 0010", "PRJ/0010", " PRJ0010", "PRJ0010\t", "PRJ\u00a00010"]
    )
    def test_rejects_name_with_slash_or_whitespace(
        self, auth_client, auth_user, project, project_membership_factory, name
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": name}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not Shot.objects.filter(project=project).exists()

    def test_accepts_name_with_underscores_hyphens_and_non_latin_letters(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        for name in ["ZS_0010", "ep01-0020", "Кадр_30"]:
            response = _post_json(
                auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": name}
            )

            assert response.status_code == HTTPStatus.CREATED

    def test_client_role_cannot_create_shots(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project, role="client")

        response = _post_json(
            auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": "0010"}
        )

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not Shot.objects.filter(project=project).exists()

    def test_rejects_negative_rec_timecode(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "rec_timecode": -1},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_rejects_zero_duration(
        self, auth_client, auth_user, project, project_membership_factory
    ):
        project_membership_factory(user=auth_user, project=project)

        response = _post_json(
            auth_client,
            f"/api/v1/projects/{project.id}/shots/",
            {"name": "0010", "duration": 0},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_member_of_project_gets_404(
        self, auth_client, project_factory, project_membership_factory
    ):
        project = project_factory()
        project_membership_factory(project=project)  # some other user

        response = _post_json(
            auth_client, f"/api/v1/projects/{project.id}/shots/", {"name": "0010"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_requires_authentication(self, client, project):
        response = _post_json(
            client, f"/api/v1/projects/{project.id}/shots/", {"name": "0010"}
        )

        assert response.status_code == 401


class TestShotThumb:
    def test_is_the_thumbnail_of_the_latest_version(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
        version_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot = shot_factory(project=project)
        version_factory(shot=shot, name="PRJ_0010_v01")
        latest = version_factory(shot=shot, name="PRJ_0010_v02")

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        thumb = response.json()["items"][0]["thumb"]
        assert thumb.endswith(latest.thumb.url)
        assert thumb.startswith("http")

    def test_is_null_when_the_shot_has_no_versions(
        self, auth_client, auth_user, project, project_membership_factory, shot_factory
    ):
        project_membership_factory(user=auth_user, project=project)
        shot_factory(project=project)

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert response.json()["items"][0]["thumb"] is None

    def test_is_null_when_the_latest_version_has_no_thumbnail(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
        version_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        shot = shot_factory(project=project)
        version_factory(shot=shot, thumb="")

        response = auth_client.get(f"/api/v1/projects/{project.id}/shots/")

        assert response.json()["items"][0]["thumb"] is None

    def test_number_of_queries_does_not_grow_with_the_number_of_shots(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
        version_factory,
        django_assert_max_num_queries,
    ):
        project_membership_factory(user=auth_user, project=project)
        for _ in range(3):
            version_factory(shot=shot_factory(project=project))
        url = f"/api/v1/projects/{project.id}/shots/"
        auth_client.get(url)

        with django_assert_max_num_queries(12):
            response = auth_client.get(url)

        assert all(item["thumb"] for item in response.json()["items"])

    def test_is_also_in_the_group_shot_list_and_the_shot_detail(
        self,
        auth_client,
        auth_user,
        project,
        project_membership_factory,
        shot_factory,
        shot_group_factory,
        version_factory,
    ):
        project_membership_factory(user=auth_user, project=project)
        group = shot_group_factory(project=project)
        shot = shot_factory(project=project, groups=[group])
        version = version_factory(shot=shot)

        in_group = auth_client.get(f"/api/v1/shot-groups/{group.id}/shots/")
        detail = auth_client.get(f"/api/v1/shots/{shot.id}/")

        assert in_group.json()["items"][0]["thumb"].endswith(version.thumb.url)
        assert detail.json()["thumb"].endswith(version.thumb.url)
