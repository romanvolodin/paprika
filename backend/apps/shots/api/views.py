from http import HTTPStatus

from django.core.paginator import Paginator
from django.db.models import ProtectedError
from dmr import APIError, Body, Path, Query, ResponseSpec, modify
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer

from apps.auth.api.controllers import AuthenticatedController
from apps.companies.models import Company
from apps.companies.permissions import require_company_admin
from apps.projects.api.views import _get_company_or_404, _get_project_or_404
from apps.projects.models import Project
from apps.projects.permissions import require_can_write
from apps.shots.models import Shot, ShotGroup, ShotStatus
from apps.users.api.views import _serialize_user
from apps.users.models import User

from .schemas import (
    CompanyShotStatusesPath,
    ProjectShotGroupsPath,
    ProjectShotsPath,
    ShotCreateIn,
    ShotGroupCreateIn,
    ShotGroupListOut,
    ShotGroupListQuery,
    ShotGroupOut,
    ShotGroupPath,
    ShotGroupShotsPath,
    ShotGroupUpdateIn,
    ShotListOut,
    ShotListQuery,
    ShotOut,
    ShotPath,
    ShotStatusCreateIn,
    ShotStatusListOut,
    ShotStatusListQuery,
    ShotStatusOut,
    ShotStatusPath,
    ShotStatusUpdateIn,
    ShotUpdateIn,
)


def _serialize_shot_group(request, shot_group: ShotGroup) -> ShotGroupOut:
    return ShotGroupOut(
        id=shot_group.id,
        project_id=shot_group.project_id,
        name=shot_group.name,
        created_by=_serialize_user(request, shot_group.created_by)
        if shot_group.created_by
        else None,
        updated_by=_serialize_user(request, shot_group.updated_by)
        if shot_group.updated_by
        else None,
        created_at=shot_group.created_at,
        updated_at=shot_group.updated_at,
    )


def _get_shot_group_or_404(user: User, shot_group_id: int) -> ShotGroup:
    """Look up a shot group, scoped to projects the user is a member of.

    Mirrors `apps.projects.api.views._get_project_or_404` - visibility
    follows the parent project's `ProjectMembership`; there's no separate
    membership model for shot groups.
    """
    try:
        return (
            ShotGroup.objects.filter(project__memberships__user=user)
            .distinct()
            .get(pk=shot_group_id)
        )
    except ShotGroup.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Shot group with id={shot_group_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


class ShotGroupListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/projects/<project_id>/shot-groups/` - list and
    create shot groups within a project.
    """

    @modify(
        summary="List a project's shot groups",
        description=(
            "Return a paginated list of shot groups within the given "
            "project, optionally filtered by `search` against the name."
        ),
        response_description="A page of shot groups.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shot groups"],
    )
    def get(
        self,
        parsed_path: Path[ProjectShotGroupsPath],
        parsed_query: Query[ShotGroupListQuery],
    ) -> ShotGroupListOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)

        queryset = ShotGroup.objects.filter(project=project)

        if parsed_query.search:
            queryset = queryset.filter(name__icontains=parsed_query.search)

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        return ShotGroupListOut(
            items=[
                _serialize_shot_group(self.request, shot_group)
                for shot_group in page.object_list
            ],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a shot group",
        description="Create a new shot group within the project.",
        response_description="The created shot group.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot groups"],
    )
    def post(
        self,
        parsed_path: Path[ProjectShotGroupsPath],
        parsed_body: Body[ShotGroupCreateIn],
    ) -> ShotGroupOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        require_can_write(self.request.user, project)

        if ShotGroup.objects.filter(project=project, name=parsed_body.name).exists():
            raise APIError(
                self.format_error(
                    "A shot group with this name already exists in this project.",
                    loc=["name"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        shot_group = ShotGroup.objects.create(
            project=project,
            name=parsed_body.name,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_shot_group(self.request, shot_group)


class ShotGroupDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/shot-groups/<id>/` - manage a single shot
    group.
    """

    @modify(
        summary="Get a shot group",
        description="Return a single shot group by id.",
        response_description="The requested shot group.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shot groups"],
    )
    def get(self, parsed_path: Path[ShotGroupPath]) -> ShotGroupOut:
        shot_group = _get_shot_group_or_404(
            self.request.user, parsed_path.shot_group_id
        )
        return _serialize_shot_group(self.request, shot_group)

    @modify(
        summary="Rename a shot group",
        description="Update a shot group's name.",
        response_description="The updated shot group.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot groups"],
    )
    def patch(
        self,
        parsed_path: Path[ShotGroupPath],
        parsed_body: Body[ShotGroupUpdateIn],
    ) -> ShotGroupOut:
        shot_group = _get_shot_group_or_404(
            self.request.user, parsed_path.shot_group_id
        )
        require_can_write(self.request.user, shot_group.project)

        name_taken = (
            ShotGroup.objects.filter(project=shot_group.project, name=parsed_body.name)
            .exclude(pk=shot_group.pk)
            .exists()
        )
        if name_taken:
            raise APIError(
                self.format_error(
                    "A shot group with this name already exists in this project.",
                    loc=["name"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        shot_group.name = parsed_body.name
        shot_group.updated_by = self.request.user
        shot_group.save(update_fields=["name", "updated_by"])

        return _serialize_shot_group(self.request, shot_group)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a shot group",
        description="Permanently delete a shot group.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot groups"],
    )
    def delete(self, parsed_path: Path[ShotGroupPath]) -> None:
        shot_group = _get_shot_group_or_404(
            self.request.user, parsed_path.shot_group_id
        )
        require_can_write(self.request.user, shot_group.project)
        shot_group.delete()
        return None


def _serialize_shot_status(request, shot_status: ShotStatus) -> ShotStatusOut:
    return ShotStatusOut(
        id=shot_status.id,
        company_id=shot_status.company_id,
        name=shot_status.name,
        color=shot_status.color,
        order=shot_status.order,
        is_default=shot_status.is_default,
        created_by=_serialize_user(request, shot_status.created_by)
        if shot_status.created_by
        else None,
        updated_by=_serialize_user(request, shot_status.updated_by)
        if shot_status.updated_by
        else None,
        created_at=shot_status.created_at,
        updated_at=shot_status.updated_at,
    )


def _get_shot_status_or_404(user: User, shot_status_id: int) -> ShotStatus:
    """Look up a shot status, scoped to companies the user is a member of.

    Mirrors `apps.projects.api.views._get_company_or_404`.
    """
    try:
        return (
            ShotStatus.objects.filter(company__memberships__user=user)
            .distinct()
            .get(pk=shot_status_id)
        )
    except ShotStatus.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Shot status with id={shot_status_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _unset_other_defaults(company: Company, *, exclude_pk: int | None = None) -> None:
    """Clear `is_default` on every other status of `company`.

    Called before saving a status with `is_default=True` so there's
    always at most one default per company - the swap, not a DB
    constraint, is what enforces "at most one" (see `ShotStatus`'s
    docstring for why).
    """
    queryset = ShotStatus.objects.filter(company=company, is_default=True)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    queryset.update(is_default=False)


class ShotStatusListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/<company_id>/shot-statuses/` - list and
    create a company's shot statuses.
    """

    @modify(
        summary="List a company's shot statuses",
        description=(
            "Return every shot status defined for the given company "
            "(not paginated - this list is short and bounded), "
            "optionally filtered by `search` against the name."
        ),
        response_description="The company's shot statuses.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shot statuses"],
    )
    def get(
        self,
        parsed_path: Path[CompanyShotStatusesPath],
        parsed_query: Query[ShotStatusListQuery],
    ) -> ShotStatusListOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)

        queryset = ShotStatus.objects.filter(company=company)
        if parsed_query.search:
            queryset = queryset.filter(name__icontains=parsed_query.search)

        return ShotStatusListOut(
            items=[_serialize_shot_status(self.request, status) for status in queryset]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a shot status",
        description=(
            "Create a new shot status for the company. Setting "
            "`is_default=True` automatically unsets the company's "
            "previous default."
        ),
        response_description="The created shot status.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot statuses"],
    )
    def post(
        self,
        parsed_path: Path[CompanyShotStatusesPath],
        parsed_body: Body[ShotStatusCreateIn],
    ) -> ShotStatusOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_admin(self.request.user, company)

        if ShotStatus.objects.filter(company=company, name=parsed_body.name).exists():
            raise APIError(
                self.format_error(
                    "A shot status with this name already exists in this company.",
                    loc=["name"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        if parsed_body.is_default:
            _unset_other_defaults(company)

        shot_status = ShotStatus.objects.create(
            company=company,
            name=parsed_body.name,
            color=parsed_body.color,
            order=parsed_body.order,
            is_default=parsed_body.is_default,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_shot_status(self.request, shot_status)


class ShotStatusDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/shot-statuses/<id>/` - manage a single
    shot status.
    """

    @modify(
        summary="Get a shot status",
        description="Return a single shot status by id.",
        response_description="The requested shot status.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shot statuses"],
    )
    def get(self, parsed_path: Path[ShotStatusPath]) -> ShotStatusOut:
        shot_status = _get_shot_status_or_404(
            self.request.user, parsed_path.shot_status_id
        )
        return _serialize_shot_status(self.request, shot_status)

    @modify(
        summary="Update a shot status",
        description=(
            "Partially update a shot status. Setting `is_default=True` "
            "automatically unsets the company's previous default."
        ),
        response_description="The updated shot status.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot statuses"],
    )
    def patch(
        self,
        parsed_path: Path[ShotStatusPath],
        parsed_body: Body[ShotStatusUpdateIn],
    ) -> ShotStatusOut:
        shot_status = _get_shot_status_or_404(
            self.request.user, parsed_path.shot_status_id
        )
        require_company_admin(self.request.user, shot_status.company)

        update_fields = parsed_body.model_dump(exclude_unset=True)

        if "name" in update_fields:
            name_taken = (
                ShotStatus.objects.filter(
                    company=shot_status.company, name=update_fields["name"]
                )
                .exclude(pk=shot_status.pk)
                .exists()
            )
            if name_taken:
                raise APIError(
                    self.format_error(
                        "A shot status with this name already exists in this company.",
                        loc=["name"],
                        error_type=ErrorType.value_error,
                    ),
                    status_code=HTTPStatus.BAD_REQUEST,
                )

        if update_fields.get("is_default") is True:
            _unset_other_defaults(shot_status.company, exclude_pk=shot_status.pk)

        for field, value in update_fields.items():
            setattr(shot_status, field, value)
        if update_fields:
            shot_status.updated_by = self.request.user
            shot_status.save(update_fields=[*update_fields, "updated_by"])

        return _serialize_shot_status(self.request, shot_status)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a shot status",
        description=(
            "Permanently delete a shot status. Rejected with a 400 if "
            "any shot still has this status, including when it's the "
            "company's current default - deleting the default itself is "
            "otherwise allowed and simply leaves the company without "
            "one until another status is marked default."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot statuses"],
    )
    def delete(self, parsed_path: Path[ShotStatusPath]) -> None:
        shot_status = _get_shot_status_or_404(
            self.request.user, parsed_path.shot_status_id
        )
        require_company_admin(self.request.user, shot_status.company)
        try:
            shot_status.delete()
        except ProtectedError as exc:
            raise APIError(
                {"detail": ("Cannot delete this status while shots still use it.")},
                status_code=HTTPStatus.BAD_REQUEST,
            ) from exc
        return None


def _serialize_shot(request, shot: Shot) -> ShotOut:
    return ShotOut(
        id=shot.id,
        project_id=shot.project_id,
        group_ids=[group.id for group in shot.groups.all()],
        status_id=shot.status_id,
        name=shot.name,
        rec_timecode=shot.rec_timecode,
        duration=shot.duration,
        created_by=_serialize_user(request, shot.created_by)
        if shot.created_by
        else None,
        updated_by=_serialize_user(request, shot.updated_by)
        if shot.updated_by
        else None,
        created_at=shot.created_at,
        updated_at=shot.updated_at,
    )


def _get_shot_or_404(user: User, shot_id: int) -> Shot:
    """Look up a shot, scoped to projects the user is a member of.

    Mirrors `_get_shot_group_or_404` - visibility follows the parent
    project's `ProjectMembership` directly, regardless of which (if any)
    groups the shot belongs to.
    """
    try:
        return (
            Shot.objects.filter(project__memberships__user=user)
            .distinct()
            .get(pk=shot_id)
        )
    except Shot.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Shot with id={shot_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _resolve_group_ids(
    controller, project: Project, group_ids: list[int]
) -> list[ShotGroup]:
    """Resolve `group_ids` to `ShotGroup` rows, all belonging to `project`.

    Raises a 400 naming the first offending id if any group doesn't
    exist or belongs to a different project - groups aren't shared
    across projects, so either case means the id is simply wrong here.
    """
    groups = list(ShotGroup.objects.filter(project=project, pk__in=group_ids))
    found_ids = {group.id for group in groups}
    missing_ids = [group_id for group_id in group_ids if group_id not in found_ids]
    if missing_ids:
        raise APIError(
            controller.format_error(
                f"Shot group with id={missing_ids[0]} was not found in this project.",
                loc=["group_ids"],
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return groups


def _resolve_status_for_create(
    controller, project: Project, status_id: int | None
) -> ShotStatus:
    """Resolve the status a new shot should get.

    If `status_id` is given, it must belong to the project's company.
    Otherwise, fall back to that company's `is_default` status - and if
    it has none (e.g. it was deleted and never replaced), creation
    fails with a 400 rather than silently picking one.
    """
    if status_id is not None:
        try:
            return ShotStatus.objects.get(company=project.company, pk=status_id)
        except ShotStatus.DoesNotExist as exc:
            raise APIError(
                controller.format_error(
                    f"Shot status with id={status_id} was not found in this "
                    "project's company.",
                    loc=["status_id"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            ) from exc

    default_status = ShotStatus.objects.filter(
        company=project.company, is_default=True
    ).first()
    if default_status is None:
        raise APIError(
            controller.format_error(
                "This company has no default shot status - specify "
                "status_id explicitly.",
                loc=["status_id"],
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return default_status


def _resolve_status_for_update(
    controller, project: Project, status_id: int
) -> ShotStatus:
    """Resolve a status to switch an existing shot to via PATCH.

    Unlike creation, there's no default fallback here - `status_id` is
    only ever called with a value the client actually sent.
    """
    try:
        return ShotStatus.objects.get(company=project.company, pk=status_id)
    except ShotStatus.DoesNotExist as exc:
        raise APIError(
            controller.format_error(
                f"Shot status with id={status_id} was not found in this "
                "project's company.",
                loc=["status_id"],
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        ) from exc


def _filter_shots(queryset, query: ShotListQuery):
    """Apply the filters shared by both shot list endpoints."""
    if query.search:
        queryset = queryset.filter(name__icontains=query.search)
    if query.name:
        queryset = queryset.filter(name=query.name)
    if query.task_type is not None:
        # `tasks` is the reverse side of `Task.shots` from `apps.tasks`;
        # looked up by name so `apps.shots` doesn't import the tasks app.
        # A shot with several tasks of that type would otherwise repeat.
        queryset = queryset.filter(tasks__type_id=query.task_type).distinct()
    return queryset


class ShotListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/projects/<project_id>/shots/` - list every shot in
    a project (regardless of group) and create new shots.

    This is the only shot-creation endpoint - see `ShotCreateIn` for why
    there's no corresponding create on the group-scoped collection.
    """

    @modify(
        summary="List a project's shots",
        description=(
            "Return a paginated list of every shot in the given project, "
            "regardless of which group(s) it belongs to, optionally "
            "filtered by `search` against the name."
        ),
        response_description="A page of shots.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shots"],
    )
    def get(
        self,
        parsed_path: Path[ProjectShotsPath],
        parsed_query: Query[ShotListQuery],
    ) -> ShotListOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)

        queryset = Shot.objects.filter(project=project)

        queryset = _filter_shots(queryset, parsed_query)

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        return ShotListOut(
            items=[_serialize_shot(self.request, shot) for shot in page.object_list],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a shot",
        description=(
            "Create a new shot within the project, optionally placing it "
            "into one or more existing shot groups via `group_ids`. A "
            "shot may belong to zero, one, or several groups - there is "
            "no default group. `status_id` is optional and defaults to "
            "the project's company's default shot status."
        ),
        response_description="The created shot.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shots"],
    )
    def post(
        self,
        parsed_path: Path[ProjectShotsPath],
        parsed_body: Body[ShotCreateIn],
    ) -> ShotOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        require_can_write(self.request.user, project)

        if Shot.objects.filter(project=project, name=parsed_body.name).exists():
            raise APIError(
                self.format_error(
                    "A shot with this name already exists in this project.",
                    loc=["name"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        groups = _resolve_group_ids(self, project, parsed_body.group_ids)
        status = _resolve_status_for_create(self, project, parsed_body.status_id)

        shot = Shot.objects.create(
            project=project,
            status=status,
            name=parsed_body.name,
            rec_timecode=parsed_body.rec_timecode,
            duration=parsed_body.duration,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        if groups:
            shot.groups.set(groups)

        return _serialize_shot(self.request, shot)


class ShotGroupShotListController(AuthenticatedController[PydanticSerializer]):
    """`GET /api/v1/shot-groups/<id>/shots/` - list the shots belonging to
    a single group. Read-only - shots are created via
    `ShotListController`, not here.
    """

    @modify(
        summary="List a shot group's shots",
        description=(
            "Return a paginated list of shots belonging to the given "
            "group, optionally filtered by `search` against the name."
        ),
        response_description="A page of shots.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shots"],
    )
    def get(
        self,
        parsed_path: Path[ShotGroupShotsPath],
        parsed_query: Query[ShotListQuery],
    ) -> ShotListOut:
        shot_group = _get_shot_group_or_404(
            self.request.user, parsed_path.shot_group_id
        )

        queryset = Shot.objects.filter(groups=shot_group)

        queryset = _filter_shots(queryset, parsed_query)

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        return ShotListOut(
            items=[_serialize_shot(self.request, shot) for shot in page.object_list],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )


class ShotDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/shots/<id>/` - manage a single shot."""

    @modify(
        summary="Get a shot",
        description="Return a single shot by id.",
        response_description="The requested shot.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shots"],
    )
    def get(self, parsed_path: Path[ShotPath]) -> ShotOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        return _serialize_shot(self.request, shot)

    @modify(
        summary="Update a shot",
        description=(
            "Partially update a shot. `group_ids`, when present, replaces "
            "the full set of group memberships. `status_id` switches the "
            "shot to a different status from the same company - it "
            "cannot be sent as null, since a shot always has one. `name` "
            "cannot be changed - it's immutable once set."
        ),
        response_description="The updated shot.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shots"],
    )
    def patch(
        self,
        parsed_path: Path[ShotPath],
        parsed_body: Body[ShotUpdateIn],
    ) -> ShotOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        require_can_write(self.request.user, shot.project)

        if (
            "status_id" in parsed_body.model_fields_set
            and parsed_body.status_id is None
        ):
            raise APIError(
                self.format_error(
                    "status_id cannot be null - a shot always has a status.",
                    loc=["status_id"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        update_fields = parsed_body.model_dump(
            exclude={"group_ids", "status_id"}, exclude_unset=True
        )
        for field, value in update_fields.items():
            setattr(shot, field, value)

        if parsed_body.status_id is not None:
            shot.status = _resolve_status_for_update(
                self, shot.project, parsed_body.status_id
            )
            update_fields["status"] = shot.status

        if update_fields:
            shot.updated_by = self.request.user
            shot.save(update_fields=[*update_fields, "updated_by"])

        if "group_ids" in parsed_body.model_fields_set:
            groups = _resolve_group_ids(self, shot.project, parsed_body.group_ids or [])
            shot.groups.set(groups)

        return _serialize_shot(self.request, shot)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a shot",
        description="Permanently delete a shot.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shots"],
    )
    def delete(self, parsed_path: Path[ShotPath]) -> None:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        require_can_write(self.request.user, shot.project)
        shot.delete()
        return None
