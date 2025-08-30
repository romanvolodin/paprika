from datetime import datetime
from typing import List, Union

from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema

from .models import Project


api = NinjaAPI(title="Paprika API")


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
