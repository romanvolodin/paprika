from http import HTTPStatus

from django.conf import settings
from django.db import IntegrityError, transaction
from dmr import APIError, Body, Path, ResponseSpec, modify
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer

from apps.access.checks import require_project_perm
from apps.access.permissions import P
from apps.auth.api.controllers import AuthenticatedController
from apps.chat.models import Message
from apps.projects.api.views import _get_project_or_404
from apps.projects.models import Project
from apps.shots.api.schemas import SHOT_NAME_PATTERN
from apps.shots.models import Shot, ShotGroup, ShotStatus
from apps.tasks.models import ShotTask, Task, TaskStatus, TaskType

from .schemas import (
    ProjectShotImportsPath,
    ShotImportIn,
    ShotImportOut,
)


def _bad_request(errors: list[dict]) -> APIError:
    return APIError({"detail": errors}, status_code=HTTPStatus.BAD_REQUEST)


def _error(message: str, loc: list[str | int]) -> dict:
    return {"msg": message, "loc": loc, "type": str(ErrorType.value_error)}


def _default_shot_status(project: Project) -> ShotStatus:
    status = ShotStatus.objects.filter(company=project.company, is_default=True).first()
    if status is None:
        raise _bad_request(
            [_error("This company has no default shot status.", ["shots"])]
        )
    return status


def _default_task_status(project: Project) -> TaskStatus:
    status = TaskStatus.objects.filter(company=project.company, is_default=True).first()
    if status is None:
        raise _bad_request(
            [_error("This company has no default task status.", ["shots"])]
        )
    return status


def _task_key(task) -> tuple[str, int]:
    return (task.name, task.type_id)


def _validate(project: Project, body: ShotImportIn) -> list[dict]:
    """Check every row and return all the problems found, not just the first.

    The preview page shows them next to the rows, so the person can fix
    or skip them in one go.
    """
    errors: list[dict] = []
    max_length = settings.CHAT_MESSAGE_MAX_LENGTH

    names = [shot.name for shot in body.shots]
    existing_names = set(
        Shot.objects.filter(project=project, name__in=names).values_list(
            "name", flat=True
        )
    )

    task_ids = {
        task.task_id
        for shot in body.shots
        for task in shot.tasks
        if task.task_id is not None
    }
    found_task_ids = set(
        Task.objects.filter(project=project, pk__in=task_ids).values_list(
            "pk", flat=True
        )
    )
    type_ids = {
        task.type_id
        for shot in body.shots
        for task in shot.tasks
        if task.type_id is not None
    }
    found_type_ids = set(
        TaskType.objects.filter(company=project.company, pk__in=type_ids).values_list(
            "pk", flat=True
        )
    )

    first_row_of_name: dict[str, int] = {}
    for index, shot in enumerate(body.shots):
        if not SHOT_NAME_PATTERN.match(shot.name):
            errors.append(
                _error(
                    "Shot name may not be empty or contain slashes or whitespace.",
                    ["shots", index, "name"],
                )
            )
        elif shot.name in existing_names:
            errors.append(
                _error(
                    "A shot with this name already exists in this project.",
                    ["shots", index, "name"],
                )
            )
        elif shot.name in first_row_of_name:
            errors.append(
                _error(
                    "This name is repeated in the import "
                    f"(first at row {first_row_of_name[shot.name]}).",
                    ["shots", index, "name"],
                )
            )
        else:
            first_row_of_name[shot.name] = index

        seen_tasks: set = set()
        for task_index, task in enumerate(shot.tasks):
            loc = ["shots", index, "tasks", task_index]
            if task.task_id is not None:
                if task.task_id not in found_task_ids:
                    errors.append(
                        _error(
                            f"Task with id={task.task_id} was not found in this "
                            "project.",
                            loc + ["task_id"],
                        )
                    )
                key = ("id", task.task_id)
            else:
                if task.type_id not in found_type_ids:
                    errors.append(
                        _error(
                            f"Task type with id={task.type_id} was not found in "
                            "this project's company.",
                            loc + ["type_id"],
                        )
                    )
                key = ("new", *_task_key(task))
            if key in seen_tasks:
                errors.append(_error("This task is given twice for the shot.", loc))
            seen_tasks.add(key)

        for message_index, text in enumerate(shot.messages):
            loc = ["shots", index, "messages", message_index]
            if not text.strip():
                errors.append(_error("A message can't be empty.", loc))
            elif len(text.strip()) > max_length:
                errors.append(
                    _error(f"A message is at most {max_length} characters.", loc)
                )

    return errors


class ProjectShotImportController(AuthenticatedController[PydanticSerializer]):
    """`POST /api/v1/projects/<project_id>/shot-imports/` - create many
    shots at once, together with their groups, tasks and chat messages.

    The spreadsheet itself is read by the client; this endpoint receives
    the finished list. It is all-or-nothing: one transaction, so either
    every shot is created or - if anything is wrong - none is.
    """

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Import shots",
        description=(
            "Create several shots in the project in one request. Each shot "
            "may be put into groups by name (a missing group is created), "
            "get tasks (existing ones by id, new ones by name and type; the "
            "same new task is created once and shared) and get chat "
            "messages written by the current user. All shots get the "
            "company's default status; tasks on shots get the default task "
            "status. Nothing is created if any row is invalid: the 400 "
            "response lists every problem with its row in `loc`."
        ),
        response_description="How many objects were created.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
        ],
        tags=["Shot import"],
    )
    def post(
        self,
        parsed_path: Path[ProjectShotImportsPath],
        parsed_body: Body[ShotImportIn],
    ) -> ShotImportOut:
        user = self.request.user
        project = _get_project_or_404(user, parsed_path.project_id)
        require_project_perm(user, project, P.SHOT_IMPORT)

        max_rows = settings.SHOT_IMPORT_MAX_ROWS
        if len(parsed_body.shots) > max_rows:
            raise _bad_request(
                [_error(f"At most {max_rows} shots per import.", ["shots"])]
            )

        errors = _validate(project, parsed_body)
        if errors:
            raise _bad_request(errors)

        shot_status = _default_shot_status(project)
        has_tasks = any(shot.tasks for shot in parsed_body.shots)
        task_status = _default_task_status(project) if has_tasks else None

        try:
            with transaction.atomic():
                return self._create(project, parsed_body, shot_status, task_status)
        except IntegrityError as exc:
            raise APIError(
                {
                    "detail": [
                        {
                            "msg": "The project changed while importing "
                            "(a name was taken in the meantime). Try again.",
                            "type": str(ErrorType.value_error),
                        }
                    ]
                },
                status_code=HTTPStatus.CONFLICT,
            ) from exc

    def _create(
        self,
        project: Project,
        body: ShotImportIn,
        shot_status: ShotStatus,
        task_status: TaskStatus | None,
    ) -> ShotImportOut:
        user = self.request.user

        group_names = {name for shot in body.shots for name in shot.groups}
        groups = {
            group.name: group
            for group in ShotGroup.objects.filter(project=project, name__in=group_names)
        }
        groups_created = 0
        for name in sorted(group_names - groups.keys()):
            groups[name] = ShotGroup.objects.create(
                project=project, name=name, created_by=user, updated_by=user
            )
            groups_created += 1

        # Created one by one: `Task.save()` generates the public code.
        new_tasks: dict[tuple[str, int], Task] = {}
        for shot in body.shots:
            for task in shot.tasks:
                if task.task_id is not None or _task_key(task) in new_tasks:
                    continue
                new_tasks[_task_key(task)] = Task.objects.create(
                    project=project,
                    type_id=task.type_id,
                    name=task.name,
                    created_by=user,
                    updated_by=user,
                )

        shots = Shot.objects.bulk_create(
            [
                Shot(
                    project=project,
                    status=shot_status,
                    name=row.name,
                    rec_timecode=row.rec_timecode,
                    created_by=user,
                    updated_by=user,
                )
                for row in body.shots
            ]
        )

        membership_model = Shot.groups.through
        membership_model.objects.bulk_create(
            [
                membership_model(shot_id=shot.pk, shotgroup_id=groups[name].pk)
                for shot, row in zip(shots, body.shots, strict=True)
                for name in dict.fromkeys(row.groups)
            ]
        )

        shot_tasks = [
            ShotTask(
                shot=shot,
                task_id=(
                    task.task_id
                    if task.task_id is not None
                    else new_tasks[_task_key(task)].pk
                ),
                status=task_status,
                created_by=user,
                updated_by=user,
            )
            for shot, row in zip(shots, body.shots, strict=True)
            for task in row.tasks
        ]
        ShotTask.objects.bulk_create(shot_tasks)

        messages = Message.objects.bulk_create(
            [
                Message(
                    shot=shot,
                    type=Message.Type.USER,
                    text=text.strip(),
                    created_by=user,
                    updated_by=user,
                )
                for shot, row in zip(shots, body.shots, strict=True)
                for text in row.messages
            ]
        )

        return ShotImportOut(
            shots_created=len(shots),
            groups_created=groups_created,
            tasks_created=len(new_tasks),
            messages_created=len(messages),
        )
