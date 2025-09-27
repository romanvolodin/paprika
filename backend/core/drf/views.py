from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Project, Shot, ShotGroup, ShotTask, Status, Task
from core.utils import calc_shot_status


@api_view(["POST"])
def create_shots(request, project_code: str):
    user = request.user
    shots = request.data
    project = get_object_or_404(Project, code=project_code)
    status_not_started = Status.objects.get(title="Не начата")
    new_shots = []
    for shot in shots:
        task_description = shot.get("task")
        if task_description is not None:
            try:
                task = Task.objects.get(description=task_description)
            except ObjectDoesNotExist:
                task = Task.objects.create(
                    project=project,
                    created_by=user,
                    description=task_description,
                    default_status=status_not_started,
                )

        group_description = shot.get("group")
        if group_description is not None:
            try:
                group = ShotGroup.objects.get(name=group_description)
            except ObjectDoesNotExist:
                group = ShotGroup.objects.create(
                    name=group_description,
                    project=project,
                    created_by=user,
                )

        s = Shot.objects.create(
            name=shot["name"],
            project=project,
            rec_timecode=shot.get("rec_timecode"),
            created_by=user,
        )

        s.group.set([group])

        ShotTask.objects.create(
            shot=s,
            task=task,
            status=status_not_started,
        )
        new_shots.append(s)
    return Response({"shots": len(new_shots)})


@api_view(["GET"])
def list_shots(request, project_code: str):
    project = get_object_or_404(Project, code=project_code)
    shot_groups = project.shot_groups.filter(is_root=True)
    out_shot_groups = []
    for shot_group in shot_groups:
        shots = []
        for shot in shot_group.shots.all():
            thumb = None
            if shot.versions.all():
                thumb = request.build_absolute_uri(shot.versions.latest().preview.url)
            statuses = [
                shot_task.status.title
                for shot_task in shot.shot_tasks.all()
                if shot_task.task.description != "Выдать материал"
            ]
            shots.append(
                {
                    "id": shot.id,
                    "name": shot.name,
                    "created_at": shot.created_at,
                    "thumb": thumb,
                    "status": calc_shot_status(statuses),
                }
            )

        out_shot_groups.append(
            {
                "id": shot_group.id,
                "name": shot_group.name,
                "is_default": shot_group.is_default,
                "is_root": shot_group.is_default,
                "shots": shots,
            }
        )
    return Response(out_shot_groups)


@api_view(["POST"])
def create_shot_groups(request, project_code: str):
    user = request.user
    shot_groups = request.data
    project = get_object_or_404(Project, code=project_code)
    new_shot_groups = []
    for shot_group in shot_groups:
        s = ShotGroup.objects.create(
            name=shot_group["name"],
            project=project,
            created_by=user,
            is_default=shot_group.get("is_default", False),
            is_root=shot_group.get("is_root", False),
        )
        new_shot_groups.append(s)
    return Response({"shot_groups": len(new_shot_groups)})
