from typing import Annotated

import pydantic


NonEmptyName = Annotated[
    str, pydantic.StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class ProjectShotImportsPath(pydantic.BaseModel):
    project_id: int


class ShotImportTaskIn(pydantic.BaseModel):
    """A task to put on an imported shot.

    Either `task_id` - an existing task of the project - or `name` plus
    `type_id` - a new task. The same new task (same `name` and `type_id`)
    given for several shots is created once and shared by them.
    """

    task_id: int | None = None
    name: NonEmptyName | None = None
    type_id: int | None = None

    @pydantic.model_validator(mode="after")
    def check_exactly_one_form(self):
        is_existing = self.task_id is not None
        is_new = self.name is not None or self.type_id is not None
        if is_existing and is_new:
            raise ValueError("Give either task_id or name with type_id, not both.")
        if not is_existing and (self.name is None or self.type_id is None):
            raise ValueError("Give either task_id or both name and type_id.")
        return self


class ShotImportShotIn(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=255)
    rec_timecode: int | None = pydantic.Field(
        default=None,
        ge=0,
        description="Start position of the shot in the edit, in frames.",
    )
    groups: list[NonEmptyName] = pydantic.Field(
        default_factory=list,
        description=(
            "Names of the groups to put the shot into. A group that doesn't "
            "exist in the project yet is created."
        ),
    )
    tasks: list[ShotImportTaskIn] = pydantic.Field(default_factory=list)
    messages: list[str] = pydantic.Field(
        default_factory=list,
        max_length=10,
        description=(
            "Texts of chat messages to post to the shot, in order. They are "
            "written by the importing user as ordinary messages."
        ),
    )


class ShotImportIn(pydantic.BaseModel):
    """Payload for `POST /api/v1/projects/<id>/shot-imports/`."""

    shots: list[ShotImportShotIn] = pydantic.Field(min_length=1)


class ShotImportOut(pydantic.BaseModel):
    shots_created: int
    groups_created: int
    tasks_created: int
    messages_created: int
