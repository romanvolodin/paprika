from django.core.exceptions import ValidationError
from django.db import IntegrityError
import pytest

from apps.shots.models import Shot


pytestmark = pytest.mark.django_db

FULL_CLEAN_EXCLUDE = ["project", "status", "created_by", "updated_by"]


class TestShotModel:
    def test_str_contains_project_and_name(self, shot_factory, project_factory):
        project = project_factory(code="PRJ", name="Acme Feature")
        shot = shot_factory(project=project, name="0010")

        # `Project.__str__` is itself "code — name", so this nests that.
        assert str(shot) == "PRJ — Acme Feature — 0010"

    def test_repr_contains_id_name_and_project_id(self, shot_factory, project):
        shot = shot_factory(project=project, name="0010")

        text = repr(shot)

        assert f"id={shot.id}" in text
        assert "name=0010" in text
        assert f"project_id={project.id}" in text

    def test_name_must_be_unique_within_project(self, shot_factory, project):
        shot_factory(project=project, name="0010")

        with pytest.raises(IntegrityError):
            shot_factory(project=project, name="0010")

    def test_same_name_allowed_in_different_projects(
        self, shot_factory, project_factory
    ):
        project_a = project_factory()
        project_b = project_factory()
        shot_factory(project=project_a, name="0010")

        # Should not raise.
        shot_factory(project=project_b, name="0010")

    @pytest.mark.parametrize("name", ["PRJ 0010", "PRJ/0010", "PRJ0010\n", ""])
    def test_full_clean_rejects_slash_whitespace_and_blank_name(self, name):
        shot = Shot(name=name)

        with pytest.raises(ValidationError) as exc_info:
            shot.full_clean(exclude=FULL_CLEAN_EXCLUDE)

        assert "name" in exc_info.value.message_dict

    @pytest.mark.parametrize("name", ["0010", "ZS_0010", "ep01-0020", "Кадр_30"])
    def test_full_clean_accepts_plain_names(self, name):
        Shot(name=name).full_clean(exclude=FULL_CLEAN_EXCLUDE)

    def test_has_no_groups_by_default(self, shot_factory):
        shot = shot_factory()

        assert shot.groups.count() == 0

    def test_can_belong_to_several_groups_at_once(
        self, shot_factory, shot_group_factory, project
    ):
        group_a = shot_group_factory(project=project, name="A")
        group_b = shot_group_factory(project=project, name="B")
        shot = shot_factory(project=project, groups=[group_a, group_b])

        assert set(shot.groups.all()) == {group_a, group_b}

    def test_rec_timecode_rejects_negative_values(self, shot_factory, project):
        shot = shot_factory.build(project=project, rec_timecode=-1)

        with pytest.raises(ValidationError):
            shot.full_clean()

    def test_duration_rejects_zero(self, shot_factory, project):
        shot = shot_factory.build(project=project, duration=0)

        with pytest.raises(ValidationError):
            shot.full_clean()

    def test_rec_timecode_and_duration_default_to_null(self, shot_factory):
        shot = shot_factory()

        assert shot.rec_timecode is None
        assert shot.duration is None

    def test_ordering_is_by_project_then_name(self, shot_factory, project):
        shot_factory(project=project, name="0030")
        shot_factory(project=project, name="0010")
        shot_factory(project=project, name="0020")

        names = list(
            Shot.objects.filter(project=project).values_list("name", flat=True)
        )

        assert names == sorted(names)

    def test_created_by_is_set_to_null_when_creator_is_deleted(
        self, shot_factory, user_factory
    ):
        creator = user_factory()
        shot = shot_factory(created_by=creator)

        creator.delete()
        shot.refresh_from_db()

        assert shot.created_by is None

    def test_is_deleted_when_project_is_deleted(self, shot_factory, project):
        shot = shot_factory(project=project)
        shot_id = shot.id

        project.delete()

        assert not Shot.objects.filter(id=shot_id).exists()

    def test_group_membership_is_removed_when_group_is_deleted_but_shot_remains(
        self, shot_factory, shot_group_factory, project
    ):
        group = shot_group_factory(project=project)
        shot = shot_factory(project=project, groups=[group])

        group.delete()

        shot.refresh_from_db()
        assert shot.groups.count() == 0
        assert Shot.objects.filter(id=shot.id).exists()
