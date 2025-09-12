from datetime import datetime
from typing import List, Union

from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema

from core.models import Project, Shot

from .auth import JWTAuth


api = NinjaAPI(
    title="Paprika API",
    auth=JWTAuth(),
)


class CreateShotRequest(Schema):
    name: str


class ShotOut(Schema):
    id: int
    thumb: Union[str, None] = None
    name: str
    created_at: datetime


class ShotGroupOut(Schema):
    id: int
    name: str
    is_default: bool
    is_root: bool
    shots: List[ShotOut]


class ShotTaskOut(Schema):
    id: int
    task: str
    status: str
    shot: ShotOut


@api.post("/me")
def me(request):
    return {"user": str(request.user), "is_authenticated": request.user.is_authenticated}


@api.get("/projects/{project_code}/shots/", response=List[ShotGroupOut])
def project_shots(request, project_code: str):
    project = get_object_or_404(Project, code=project_code)
    shot_groups = project.shot_groups.filter(is_root=True)
    return [
        {
            "id": shot_group.id,
            "name": shot_group.name,
            "is_default": shot_group.is_default,
            "is_root": shot_group.is_default,
            "shots": [
                {
                    "id": shot.id,
                    "name": shot.name,
                    "created_at": shot.created_at,
                    "thumb": request.build_absolute_uri(shot.versions.latest().preview.url),
                }
                for shot in shot_group.shots.all()
            ],
        }
        for shot_group in shot_groups
    ]


@api.post("/projects/{project_code}/shots/", response=List[ShotOut])
def create_shots(request, project_code: str, shots: list[CreateShotRequest]):
    user = request.user
    project = get_object_or_404(Project, code=project_code)
    new_shots = []
    for shot in shots:
        s = Shot.objects.create(
            name=shot.name,
            project=project,
            created_by=user,
        )
        new_shots.append(s)
    return new_shots


@api.get("/projects/{project_code}/shot_tasks/my", response=List[ShotTaskOut])
def get_my_shot_tasks(request, project_code: str):
    user = request.user
    shot_tasks = user.assigned_tasks.filter(shot__project__code=project_code)
    return [
        {
            "id": t.id,
            "task": t.task.description,
            "status": t.status.title,
            "shot": {
                "id": t.shot.id,
                "name": t.shot.name,
                "created_at": t.shot.created_at,
                "thumb": request.build_absolute_uri(t.shot.versions.latest().preview.url),
            },
        } for t in shot_tasks
    ]
