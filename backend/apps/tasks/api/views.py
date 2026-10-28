from http import HTTPStatus

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q
from dmr import APIError, Body, Path, Query, ResponseSpec, modify
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer

from apps.access.checks import (
    can_in_project,
    companies_q,
    projects_q,
    require_company_perm,
    require_project_perm,
)
from apps.access.permissions import P
from apps.auth.api.controllers import AuthenticatedController
from apps.chat.events import (
    record_assignee_changed,
    record_status_changed,
    record_task_added,
)
from apps.companies.models import Company
from apps.projects.api.views import _get_company_or_404, _get_project_or_404
from apps.projects.models import Project, ProjectMembership
from apps.shots.api.views import _get_shot_or_404
from apps.tasks.models import ShotTask, Task, TaskStatus, TaskType
from apps.users.api.views import _serialize_user
from apps.users.models import User

from .schemas import (
    CompanyTaskStatusesPath,
    CompanyTaskTypesPath,
    ProjectTasksPath,
    ShotTaskCreateIn,
    ShotTaskListOut,
    ShotTaskOut,
    ShotTaskPath,
    ShotTasksPath,
    ShotTaskUpdateIn,
    TaskCreateIn,
    TaskListOut,
    TaskListQuery,
    TaskOut,
    TaskPath,
    TaskStatusCreateIn,
    TaskStatusListOut,
    TaskStatusListQuery,
    TaskStatusOut,
    TaskStatusPath,
    TaskStatusUpdateIn,
    TaskTypeCreateIn,
    TaskTypeListOut,
    TaskTypeListQuery,
    TaskTypeOut,
    TaskTypePath,
    TaskTypeUpdateIn,
    TaskUpdateIn,
)


_SHOT_TASK_UNIQUE_CONSTRAINT = "unique_task_per_shot"


# --- shared helpers ---------------------------------------------------------


def _conflict(controller, message: str, loc: list[str]) -> APIError:
    """A 409 for something that clashes with existing data."""
    return APIError(
        controller.format_error(message, loc=loc, error_type=ErrorType.value_error),
        status_code=HTTPStatus.CONFLICT,
    )


def _bad_request(controller, message: str, loc: list[str]) -> APIError:
    return APIError(
        controller.format_error(message, loc=loc, error_type=ErrorType.value_error),
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _reject_explicit_nulls(controller, body, fields: list[str]) -> None:
    """400 if the client sent `null` for a field that can't be null.

    Optional fields in a PATCH payload default to `None` meaning "not
    sent"; sending an explicit `null` for a required column would
    otherwise reach the database.
    """
    for field in fields:
        if field in body.model_fields_set and getattr(body, field) is None:
            raise _bad_request(controller, f"{field} cannot be null.", loc=[field])


def _audit(request, obj) -> dict:
    return {
        "created_by": _serialize_user(request, obj.created_by)
        if obj.created_by
        else None,
        "updated_by": _serialize_user(request, obj.updated_by)
        if obj.updated_by
        else None,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _hours(value) -> float | None:
    return float(value) if value is not None else None


# --- task types -------------------------------------------------------------


def _serialize_task_type(request, task_type: TaskType) -> TaskTypeOut:
    return TaskTypeOut(
        id=task_type.id,
        company_id=task_type.company_id,
        name=task_type.name,
        abbreviation=task_type.abbreviation,
        color=task_type.color,
        **_audit(request, task_type),
    )


def _get_task_type_or_404(user: User, task_type_id: int) -> TaskType:
    """Look up a task type, scoped to companies the user is a member of."""
    try:
        return (
            TaskType.objects.filter(companies_q(user, "company"))
            .select_related("created_by", "updated_by")
            .distinct()
            .get(pk=task_type_id)
        )
    except TaskType.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Task type with id={task_type_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _task_type_clash(
    company: Company, *, name=None, abbreviation=None, exclude_pk=None
) -> tuple[str, str] | None:
    """Return (message, field) if `name`/`abbreviation` is already taken."""
    others = TaskType.objects.filter(company=company)
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)
    if name is not None and others.filter(name=name).exists():
        return ("A task type with this name already exists in this company.", "name")
    if abbreviation is not None and others.filter(abbreviation=abbreviation).exists():
        return (
            "A task type with this abbreviation already exists in this company.",
            "abbreviation",
        )
    return None


class TaskTypeListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/<company_id>/task-types/` - list and
    create a company's task types.
    """

    @modify(
        summary="List a company's task types",
        description=(
            "Return every task type defined for the given company (not "
            "paginated - this list is short and bounded), optionally "
            "filtered by `search` against the name or abbreviation."
        ),
        response_description="The company's task types.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Task types"],
    )
    def get(
        self,
        parsed_path: Path[CompanyTaskTypesPath],
        parsed_query: Query[TaskTypeListQuery],
    ) -> TaskTypeListOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)

        queryset = TaskType.objects.filter(company=company).select_related(
            "created_by", "updated_by"
        )
        if parsed_query.search:
            queryset = queryset.filter(
                Q(name__icontains=parsed_query.search)
                | Q(abbreviation__icontains=parsed_query.search)
            )

        return TaskTypeListOut(
            items=[_serialize_task_type(self.request, t) for t in queryset]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a task type",
        description=(
            "Create a new task type for the company. The name and the "
            "abbreviation must each be unique within the company (409 "
            "otherwise)."
        ),
        response_description="The created task type.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Task types"],
    )
    def post(
        self,
        parsed_path: Path[CompanyTaskTypesPath],
        parsed_body: Body[TaskTypeCreateIn],
    ) -> TaskTypeOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_PIPELINE)

        clash = _task_type_clash(
            company, name=parsed_body.name, abbreviation=parsed_body.abbreviation
        )
        if clash:
            raise _conflict(self, clash[0], [clash[1]])

        task_type = TaskType.objects.create(
            company=company,
            name=parsed_body.name,
            abbreviation=parsed_body.abbreviation,
            color=parsed_body.color,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_task_type(self.request, task_type)


class TaskTypeDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/task-types/<id>/` - manage a single task
    type.
    """

    @modify(
        summary="Get a task type",
        description="Return a single task type by id.",
        response_description="The requested task type.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Task types"],
    )
    def get(self, parsed_path: Path[TaskTypePath]) -> TaskTypeOut:
        task_type = _get_task_type_or_404(self.request.user, parsed_path.task_type_id)
        return _serialize_task_type(self.request, task_type)

    @modify(
        summary="Update a task type",
        description=(
            "Partially update a task type. Changing the abbreviation "
            "doesn't change the codes of tasks that already exist."
        ),
        response_description="The updated task type.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Task types"],
    )
    def patch(
        self,
        parsed_path: Path[TaskTypePath],
        parsed_body: Body[TaskTypeUpdateIn],
    ) -> TaskTypeOut:
        task_type = _get_task_type_or_404(self.request.user, parsed_path.task_type_id)
        require_company_perm(self.request.user, task_type.company, P.COMPANY_PIPELINE)
        _reject_explicit_nulls(self, parsed_body, ["name", "abbreviation", "color"])

        update_fields = parsed_body.model_dump(exclude_unset=True)

        clash = _task_type_clash(
            task_type.company,
            name=update_fields.get("name"),
            abbreviation=update_fields.get("abbreviation"),
            exclude_pk=task_type.pk,
        )
        if clash:
            raise _conflict(self, clash[0], [clash[1]])

        for field, value in update_fields.items():
            setattr(task_type, field, value)
        if update_fields:
            task_type.updated_by = self.request.user
            task_type.save(update_fields=[*update_fields, "updated_by"])

        return _serialize_task_type(self.request, task_type)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a task type",
        description=(
            "Permanently delete a task type. Rejected with a 409 while "
            "any task still has this type - move those tasks to another "
            "type first."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Task types"],
    )
    def delete(self, parsed_path: Path[TaskTypePath]) -> None:
        task_type = _get_task_type_or_404(self.request.user, parsed_path.task_type_id)
        require_company_perm(self.request.user, task_type.company, P.COMPANY_PIPELINE)
        try:
            task_type.delete()
        except ProtectedError as exc:
            raise APIError(
                {"detail": "Cannot delete this task type while tasks still use it."},
                status_code=HTTPStatus.CONFLICT,
            ) from exc
        return None


# --- task statuses ----------------------------------------------------------


def _serialize_task_status(request, task_status: TaskStatus) -> TaskStatusOut:
    return TaskStatusOut(
        id=task_status.id,
        company_id=task_status.company_id,
        name=task_status.name,
        color=task_status.color,
        order=task_status.order,
        is_default=task_status.is_default,
        **_audit(request, task_status),
    )


def _get_task_status_or_404(user: User, task_status_id: int) -> TaskStatus:
    """Look up a task status, scoped to companies the user is a member of."""
    try:
        return (
            TaskStatus.objects.filter(companies_q(user, "company"))
            .select_related("created_by", "updated_by")
            .distinct()
            .get(pk=task_status_id)
        )
    except TaskStatus.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Task status with id={task_status_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _unset_other_defaults(company: Company, *, exclude_pk: int | None = None) -> None:
    """Clear `is_default` on every other status of `company`.

    Called before saving a status with `is_default=True`, so there is
    always at most one default per company.
    """
    queryset = TaskStatus.objects.filter(company=company, is_default=True)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    queryset.update(is_default=False)


class TaskStatusListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/<company_id>/task-statuses/` - list and
    create a company's task statuses.
    """

    @modify(
        summary="List a company's task statuses",
        description=(
            "Return every task status defined for the given company (not "
            "paginated - this list is short and bounded), optionally "
            "filtered by `search` against the name."
        ),
        response_description="The company's task statuses.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Task statuses"],
    )
    def get(
        self,
        parsed_path: Path[CompanyTaskStatusesPath],
        parsed_query: Query[TaskStatusListQuery],
    ) -> TaskStatusListOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)

        queryset = TaskStatus.objects.filter(company=company).select_related(
            "created_by", "updated_by"
        )
        if parsed_query.search:
            queryset = queryset.filter(name__icontains=parsed_query.search)

        return TaskStatusListOut(
            items=[_serialize_task_status(self.request, s) for s in queryset]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a task status",
        description=(
            "Create a new task status for the company. The name must be "
            "unique within the company (409 otherwise). Setting "
            "`is_default=True` automatically unsets the company's "
            "previous default."
        ),
        response_description="The created task status.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Task statuses"],
    )
    def post(
        self,
        parsed_path: Path[CompanyTaskStatusesPath],
        parsed_body: Body[TaskStatusCreateIn],
    ) -> TaskStatusOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_PIPELINE)

        if TaskStatus.objects.filter(company=company, name=parsed_body.name).exists():
            raise _conflict(
                self,
                "A task status with this name already exists in this company.",
                ["name"],
            )

        if parsed_body.is_default:
            _unset_other_defaults(company)

        task_status = TaskStatus.objects.create(
            company=company,
            name=parsed_body.name,
            color=parsed_body.color,
            order=parsed_body.order,
            is_default=parsed_body.is_default,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_task_status(self.request, task_status)


class TaskStatusDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/task-statuses/<id>/` - manage a single
    task status.
    """

    @modify(
        summary="Get a task status",
        description="Return a single task status by id.",
        response_description="The requested task status.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Task statuses"],
    )
    def get(self, parsed_path: Path[TaskStatusPath]) -> TaskStatusOut:
        task_status = _get_task_status_or_404(
            self.request.user, parsed_path.task_status_id
        )
        return _serialize_task_status(self.request, task_status)

    @modify(
        summary="Update a task status",
        description=(
            "Partially update a task status. Setting `is_default=True` "
            "automatically unsets the company's previous default."
        ),
        response_description="The updated task status.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Task statuses"],
    )
    def patch(
        self,
        parsed_path: Path[TaskStatusPath],
        parsed_body: Body[TaskStatusUpdateIn],
    ) -> TaskStatusOut:
        task_status = _get_task_status_or_404(
            self.request.user, parsed_path.task_status_id
        )
        require_company_perm(self.request.user, task_status.company, P.COMPANY_PIPELINE)
        _reject_explicit_nulls(self, parsed_body, ["name", "color", "is_default"])

        update_fields = parsed_body.model_dump(exclude_unset=True)

        if "name" in update_fields:
            name_taken = (
                TaskStatus.objects.filter(
                    company=task_status.company, name=update_fields["name"]
                )
                .exclude(pk=task_status.pk)
                .exists()
            )
            if name_taken:
                raise _conflict(
                    self,
                    "A task status with this name already exists in this company.",
                    ["name"],
                )

        if update_fields.get("is_default") is True:
            _unset_other_defaults(task_status.company, exclude_pk=task_status.pk)

        for field, value in update_fields.items():
            setattr(task_status, field, value)
        if update_fields:
            task_status.updated_by = self.request.user
            task_status.save(update_fields=[*update_fields, "updated_by"])

        return _serialize_task_status(self.request, task_status)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a task status",
        description=(
            "Permanently delete a task status. Rejected with a 409 while "
            "any shot task still has this status, including when it's the "
            "company's current default - deleting the default itself is "
            "otherwise allowed and simply leaves the company without one "
            "until another status is marked default."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Task statuses"],
    )
    def delete(self, parsed_path: Path[TaskStatusPath]) -> None:
        task_status = _get_task_status_or_404(
            self.request.user, parsed_path.task_status_id
        )
        require_company_perm(self.request.user, task_status.company, P.COMPANY_PIPELINE)
        try:
            task_status.delete()
        except ProtectedError as exc:
            raise APIError(
                {"detail": "Cannot delete this status while shot tasks still use it."},
                status_code=HTTPStatus.CONFLICT,
            ) from exc
        return None


# --- tasks ------------------------------------------------------------------


def _serialize_task(request, task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        project_id=task.project_id,
        code=task.code,
        name=task.name,
        description=task.description,
        type_id=task.type_id,
        shot_ids=[shot.id for shot in task.shots.all()],
        **_audit(request, task),
    )


def _task_queryset():
    return Task.objects.select_related("created_by", "updated_by").prefetch_related(
        "shots"
    )


def _get_task_or_404(user: User, task_id: int) -> Task:
    """Look up a task, scoped to projects the user is a member of."""
    try:
        return _task_queryset().filter(projects_q(user, "project")).get(pk=task_id)
    except Task.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Task with id={task_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _resolve_task_type(controller, project: Project, type_id: int) -> TaskType:
    """Resolve `type_id` to a `TaskType` of the project's company (else 400)."""
    try:
        return TaskType.objects.get(company=project.company, pk=type_id)
    except TaskType.DoesNotExist as exc:
        raise _bad_request(
            controller,
            f"Task type with id={type_id} was not found in this project's company.",
            ["type_id"],
        ) from exc


class TaskListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/projects/<project_id>/tasks/` - list a project's
    tasks and create new ones.
    """

    @modify(
        summary="List a project's tasks",
        description=(
            "Return a paginated list of the project's tasks, newest "
            "first, optionally filtered by `search` against the name or "
            "code and by `type` (a task type id)."
        ),
        response_description="A page of tasks.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Tasks"],
    )
    def get(
        self,
        parsed_path: Path[ProjectTasksPath],
        parsed_query: Query[TaskListQuery],
    ) -> TaskListOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)

        queryset = _task_queryset().filter(project=project)
        if parsed_query.search:
            queryset = queryset.filter(
                Q(name__icontains=parsed_query.search)
                | Q(code__icontains=parsed_query.search)
            )
        if parsed_query.type is not None:
            queryset = queryset.filter(type_id=parsed_query.type)

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        return TaskListOut(
            items=[_serialize_task(self.request, t) for t in page.object_list],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a task",
        description=(
            "Create a new task in the project. It gets a generated "
            "`code` (the type's abbreviation plus four digits) and starts "
            "out standalone - place it on shots with "
            "`POST /api/v1/shots/<id>/tasks/`. Needs the `task.create` "
            "permission."
        ),
        response_description="The created task.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Tasks"],
    )
    def post(
        self,
        parsed_path: Path[ProjectTasksPath],
        parsed_body: Body[TaskCreateIn],
    ) -> TaskOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        require_project_perm(self.request.user, project, P.TASK_CREATE)

        task_type = _resolve_task_type(self, project, parsed_body.type_id)

        task = Task.objects.create(
            project=project,
            type=task_type,
            name=parsed_body.name,
            description=parsed_body.description,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_task(self.request, task)


class TaskDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/tasks/<id>/` - manage a single task."""

    @modify(
        summary="Get a task",
        description="Return a single task by id.",
        response_description="The requested task.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Tasks"],
    )
    def get(self, parsed_path: Path[TaskPath]) -> TaskOut:
        task = _get_task_or_404(self.request.user, parsed_path.task_id)
        return _serialize_task(self.request, task)

    @modify(
        summary="Update a task",
        description=(
            "Partially update a task's name, description or type. The "
            "task's `code` never changes, not even when its type does. "
            "Needs the `task.edit` permission."
        ),
        response_description="The updated task.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Tasks"],
    )
    def patch(
        self,
        parsed_path: Path[TaskPath],
        parsed_body: Body[TaskUpdateIn],
    ) -> TaskOut:
        task = _get_task_or_404(self.request.user, parsed_path.task_id)
        require_project_perm(self.request.user, task.project, P.TASK_EDIT)
        _reject_explicit_nulls(self, parsed_body, ["name", "description", "type_id"])

        update_fields = parsed_body.model_dump(exclude={"type_id"}, exclude_unset=True)
        for field, value in update_fields.items():
            setattr(task, field, value)

        if parsed_body.type_id is not None:
            task.type = _resolve_task_type(self, task.project, parsed_body.type_id)
            update_fields["type"] = task.type

        if update_fields:
            task.updated_by = self.request.user
            task.save(update_fields=[*update_fields, "updated_by"])

        return _serialize_task(self.request, task)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a task",
        description=(
            "Permanently delete a task together with its placements on "
            "shots (and the status, assignee and hours tracked there). "
            "Needs the `task.delete` permission."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Tasks"],
    )
    def delete(self, parsed_path: Path[TaskPath]) -> None:
        task = _get_task_or_404(self.request.user, parsed_path.task_id)
        require_project_perm(self.request.user, task.project, P.TASK_DELETE)
        task.delete()
        return None


# --- shot tasks -------------------------------------------------------------


def _serialize_shot_task(request, shot_task: ShotTask) -> ShotTaskOut:
    return ShotTaskOut(
        id=shot_task.id,
        shot_id=shot_task.shot_id,
        task=_serialize_task(request, shot_task.task),
        status_id=shot_task.status_id,
        assignee=_serialize_user(request, shot_task.assignee)
        if shot_task.assignee
        else None,
        estimated_hours=_hours(shot_task.estimated_hours),
        actual_hours=_hours(shot_task.actual_hours),
        **_audit(request, shot_task),
    )


def _shot_task_queryset():
    return ShotTask.objects.select_related(
        "task__created_by",
        "task__updated_by",
        "shot__project__company",
        "status",
        "assignee",
        "created_by",
        "updated_by",
    ).prefetch_related("task__shots")


def _get_shot_task_or_404(user: User, shot_task_id: int) -> ShotTask:
    """Look up a shot task, scoped to projects the user is a member of."""
    try:
        return (
            _shot_task_queryset()
            .filter(projects_q(user, "shot__project"))
            .get(pk=shot_task_id)
        )
    except ShotTask.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Shot task with id={shot_task_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _resolve_task_status(controller, project: Project, status_id: int) -> TaskStatus:
    """Resolve `status_id` to a `TaskStatus` of the project's company (else 400)."""
    try:
        return TaskStatus.objects.get(company=project.company, pk=status_id)
    except TaskStatus.DoesNotExist as exc:
        raise _bad_request(
            controller,
            f"Task status with id={status_id} was not found in this project's company.",
            ["status_id"],
        ) from exc


def _resolve_status_for_create(
    controller, project: Project, status_id: int | None
) -> TaskStatus:
    """The status a new shot task gets: the given one, else the company's
    default (400 if it has none rather than silently picking one).
    """
    if status_id is not None:
        return _resolve_task_status(controller, project, status_id)

    default_status = TaskStatus.objects.filter(
        company=project.company, is_default=True
    ).first()
    if default_status is None:
        raise _bad_request(
            controller,
            "This company has no default task status - specify status_id explicitly.",
            ["status_id"],
        )
    return default_status


def _resolve_assignee(controller, project: Project, assignee_id: int) -> User:
    """Resolve `assignee_id` to a member of `project` (else 400)."""
    is_member = ProjectMembership.objects.filter(
        project=project, user_id=assignee_id
    ).exists()
    if not is_member:
        raise _bad_request(
            controller,
            f"User with id={assignee_id} is not a member of this project.",
            ["assignee_id"],
        )
    return User.objects.get(pk=assignee_id)


def _is_own_status_change(user: User, project: Project, shot_task, body) -> bool:
    """Whether this is the assignee changing only the status of their own task."""
    return (
        shot_task.assignee_id == user.id
        and body.model_fields_set == {"status_id"}
        and can_in_project(user, project, P.TASK_UPDATE_OWN)
    )


class ShotTaskListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/shots/<shot_id>/tasks/` - list the tasks placed on
    a shot and place another one.
    """

    @modify(
        summary="List a shot's tasks",
        description=(
            "Return every task placed on the shot, in the order they "
            "were placed (not paginated - a shot has only a few). Each "
            "item carries the tracking of the work on this shot (status, "
            "assignee, hours) and the nested task."
        ),
        response_description="The shot's tasks.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shot tasks"],
    )
    def get(self, parsed_path: Path[ShotTasksPath]) -> ShotTaskListOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)

        queryset = _shot_task_queryset().filter(shot=shot)
        return ShotTaskListOut(
            items=[_serialize_shot_task(self.request, st) for st in queryset]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Place a task on a shot",
        description=(
            "Place an existing task (`task_id`) of the shot's project on "
            "the shot. `status_id` defaults to the company's default task "
            "status; `assignee_id` must be a member of the project. A "
            "task can be placed on a given shot only once (409 "
            "otherwise). Needs the `task.create` permission."
        ),
        response_description="The created shot task.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
        ],
        tags=["Shot tasks"],
    )
    def post(
        self,
        parsed_path: Path[ShotTasksPath],
        parsed_body: Body[ShotTaskCreateIn],
    ) -> ShotTaskOut:
        shot = _get_shot_or_404(self.request.user, parsed_path.shot_id)
        project = shot.project
        require_project_perm(self.request.user, project, P.TASK_CREATE)

        try:
            task = Task.objects.get(project=project, pk=parsed_body.task_id)
        except Task.DoesNotExist as exc:
            raise _bad_request(
                self,
                f"Task with id={parsed_body.task_id} was not found in this project.",
                ["task_id"],
            ) from exc

        if ShotTask.objects.filter(task=task, shot=shot).exists():
            raise self._already_placed_error(task)

        status = _resolve_status_for_create(self, project, parsed_body.status_id)
        assignee = (
            _resolve_assignee(self, project, parsed_body.assignee_id)
            if parsed_body.assignee_id is not None
            else None
        )

        try:
            with transaction.atomic():
                shot_task = ShotTask.objects.create(
                    task=task,
                    shot=shot,
                    status=status,
                    assignee=assignee,
                    estimated_hours=parsed_body.estimated_hours,
                    actual_hours=parsed_body.actual_hours,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
                record_task_added(shot_task, self.request.user)
        except IntegrityError as exc:
            if _SHOT_TASK_UNIQUE_CONSTRAINT not in str(exc):
                raise
            raise self._already_placed_error(task) from exc

        # Reload with the relations the serializer reads, in one query.
        shot_task = _shot_task_queryset().get(pk=shot_task.pk)
        return _serialize_shot_task(self.request, shot_task)

    def _already_placed_error(self, task: Task) -> APIError:
        return _conflict(
            self,
            f"Task {task.code} is already placed on this shot.",
            ["task_id"],
        )


class ShotTaskDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/shot-tasks/<id>/` - manage a single task
    placed on a shot.
    """

    @modify(
        summary="Get a shot task",
        description="Return a single shot task by id.",
        response_description="The requested shot task.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Shot tasks"],
    )
    def get(self, parsed_path: Path[ShotTaskPath]) -> ShotTaskOut:
        shot_task = _get_shot_task_or_404(self.request.user, parsed_path.shot_task_id)
        return _serialize_shot_task(self.request, shot_task)

    @modify(
        summary="Update a shot task",
        description=(
            "Partially update the tracking of a task on a shot: status, "
            "assignee (null to unassign) and estimated/actual hours (null "
            "to clear). The task and the shot can't be changed. Needs "
            "`task.edit`; the assignee can change just the status of "
            "their own task with `task.update_own`."
        ),
        response_description="The updated shot task.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot tasks"],
    )
    def patch(
        self,
        parsed_path: Path[ShotTaskPath],
        parsed_body: Body[ShotTaskUpdateIn],
    ) -> ShotTaskOut:
        shot_task = _get_shot_task_or_404(self.request.user, parsed_path.shot_task_id)
        project = shot_task.shot.project
        if not _is_own_status_change(
            self.request.user, project, shot_task, parsed_body
        ):
            require_project_perm(self.request.user, project, P.TASK_EDIT)
        _reject_explicit_nulls(self, parsed_body, ["status_id"])

        old_status = shot_task.status
        old_assignee = shot_task.assignee

        update_fields = parsed_body.model_dump(
            exclude={"status_id", "assignee_id"}, exclude_unset=True
        )
        for field, value in update_fields.items():
            setattr(shot_task, field, value)

        if parsed_body.status_id is not None:
            shot_task.status = _resolve_task_status(
                self, project, parsed_body.status_id
            )
            update_fields["status"] = shot_task.status

        if "assignee_id" in parsed_body.model_fields_set:
            shot_task.assignee = (
                _resolve_assignee(self, project, parsed_body.assignee_id)
                if parsed_body.assignee_id is not None
                else None
            )
            update_fields["assignee"] = shot_task.assignee

        if update_fields:
            shot_task.updated_by = self.request.user
            # The chat events are saved together with the change.
            with transaction.atomic():
                shot_task.save(update_fields=[*update_fields, "updated_by"])
                if shot_task.status_id != old_status.id:
                    record_status_changed(shot_task, old_status, self.request.user)
                old_assignee_id = old_assignee.id if old_assignee else None
                if shot_task.assignee_id != old_assignee_id:
                    record_assignee_changed(shot_task, old_assignee, self.request.user)

        return _serialize_shot_task(self.request, shot_task)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Remove a task from a shot",
        description=(
            "Remove the task from the shot, discarding the tracking "
            "recorded for it there. The task itself stays. Needs the "
            "`task.delete` permission."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Shot tasks"],
    )
    def delete(self, parsed_path: Path[ShotTaskPath]) -> None:
        shot_task = _get_shot_task_or_404(self.request.user, parsed_path.shot_task_id)
        require_project_perm(self.request.user, shot_task.shot.project, P.TASK_DELETE)
        shot_task.delete()
        return None
