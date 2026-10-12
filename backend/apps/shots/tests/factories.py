import factory
from factory.django import DjangoModelFactory

from apps.shots.models import Shot, ShotGroup, ShotStatus


class ShotGroupFactory(DjangoModelFactory):
    """Builds `ShotGroup` instances for tests.

    Usage:
        shot_group_factory()                        # saved, random project + name
        shot_group_factory(project=project, name="Int. Office")
        shot_group_factory.build(...)               # unsaved instance (no DB hit)
    """

    class Meta:
        model = ShotGroup

    project = factory.SubFactory("apps.projects.tests.factories.ProjectFactory")
    name = factory.Sequence(lambda n: f"Shot Group {n}")


class ShotStatusFactory(DjangoModelFactory):
    """Builds `ShotStatus` instances for tests.

    Usage:
        shot_status_factory()                     # saved, random company + name
        shot_status_factory(company=company, name="В работе", color="#FFAA00")
    """

    class Meta:
        model = ShotStatus

    company = factory.SubFactory("apps.companies.tests.factories.CompanyFactory")
    name = factory.Sequence(lambda n: f"Status {n}")
    color = "#FF5733"
    order = None
    is_default = False


class ShotFactory(DjangoModelFactory):
    """Builds `Shot` instances for tests.

    Usage:
        shot_factory()                           # saved, random project/name, no groups
        shot_factory(project=project, name="0010")
        shot_factory(groups=[group_a, group_b])  # M2M set after creation
        shot_factory(status=some_status)         # override the default status
        shot_factory.build(...)                  # unsaved instance (no DB hit)
    """

    class Meta:
        model = Shot
        skip_postgeneration_save = True

    project = factory.SubFactory("apps.projects.tests.factories.ProjectFactory")
    # `Company` seeds a default `ShotStatus` on creation (see
    # apps.shots.signals), so reuse it rather than creating a redundant
    # extra status per shot - but still scoped to the shot's own
    # project's company, not some unrelated random one.
    status = factory.LazyAttribute(
        lambda o: (
            o.project.company.shot_statuses.filter(is_default=True).first()
            or ShotStatusFactory(company=o.project.company)
        )
    )
    name = factory.Sequence(lambda n: f"Shot{n}")

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.groups.set(extracted)
