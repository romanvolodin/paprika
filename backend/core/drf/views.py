from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Project, Shot, ShotGroup, ShotTask, Status, Task, Version
from core.serializers import ShotGroupCreateSerializer, ShotTaskSerializer
from core.utils import calc_shot_status


@api_view(["POST"])
def create_shots(request, project_code: str):
    user = request.user
    shots = request.data
    project = get_object_or_404(Project, code=project_code)
    status_not_started = Status.objects.get(title="Не начата")
    new_shots = []
    errors = []

    for shot in shots:
        try:
            task_description = shot.get("task")
            task = None
            if task_description is not None:
                try:
                    task = Task.objects.get(description=task_description, project=project)
                except ObjectDoesNotExist:
                    task = Task.objects.create(
                        project=project,
                        created_by=user,
                        description=task_description,
                        default_status=status_not_started,
                    )

            group_description = shot.get("group")
            group = None
            if group_description is not None:
                try:
                    group = ShotGroup.objects.get(name=group_description, project=project)
                except ObjectDoesNotExist:
                    group = ShotGroup.objects.create(
                        name=group_description,
                        project=project,
                        created_by=user,
                    )

            shot = Shot(
                name=shot["name"],
                project=project,
                rec_timecode=shot.get("rec_timecode"),
                created_by=user,
            )
            shot.full_clean()
            shot.save()

            if group:
                shot.group.set([group])

            if task:
                ShotTask.objects.create(
                    shot=shot,
                    task=task,
                    status=status_not_started,
                )
            new_shots.append(shot)
        except ValidationError as e:
            errors.append(e.message_dict)
        except Exception as e:
            errors.append(str(e))

    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"shots": len(new_shots)})


@api_view(["GET"])
def list_shots(request, project_code: str):
    project = get_object_or_404(Project, code=project_code)

    shot_groups = project.shot_groups.filter(is_root=True).prefetch_related(
        Prefetch(
            "shots",
            queryset=Shot.objects.prefetch_related(
                Prefetch(
                    "versions",
                    queryset=Version.objects.order_by("-created_at"),
                    to_attr="version_list",
                ),
                Prefetch(
                    "shot_tasks",
                    queryset=ShotTask.objects.select_related("task", "status").exclude(
                        task__description="Выдать материал"
                    ),
                    to_attr="filtered_tasks",
                ),
            ),
        )
    )

    out_shot_groups = []
    for shot_group in shot_groups:
        shots = []
        for shot in shot_group.shots.all():
            thumb = None
            if hasattr(shot, "version_list") and shot.version_list:
                thumb = request.build_absolute_uri(shot.version_list[0].preview.url)

            statuses = [st.status.title for st in shot.filtered_tasks]

            shots.append(
                {
                    "id": shot.id,
                    "name": shot.name,
                    "created_at": shot.created_at,
                    "thumb": thumb,
                    "status": calc_shot_status(statuses),
                }
            )

        shots.sort(key=lambda shot: shot["name"])

        out_shot_groups.append(
            {
                "id": shot_group.id,
                "name": shot_group.name,
                "is_default": shot_group.is_default,
                "is_root": shot_group.is_root,
                "shots": shots,
            }
        )
    return Response(out_shot_groups)


@api_view(["POST"])
def create_shot_groups(request, project_code: str):
    user = request.user
    project = get_object_or_404(Project, code=project_code)

    shot_groups_data = request.data
    if isinstance(shot_groups_data, dict):
        shot_groups_data = [shot_groups_data]

    created_groups = []
    errors = []

    for group_data in shot_groups_data:
        group_data["project"] = project.id

        serializer = ShotGroupCreateSerializer(data=group_data)
        if serializer.is_valid():
            group = serializer.save(created_by=user)
            created_groups.append(group)
        else:
            errors.append(serializer.errors)

    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"shot_groups": len(created_groups)}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def list_shot_tasks(request, project_code: str, shot_name: str):
    project = get_object_or_404(Project, code=project_code)
    shot = get_object_or_404(Shot, project=project, name=shot_name)
    tasks = shot.shot_tasks.all()
    serializer = ShotTaskSerializer(tasks, many=True)
    return Response(serializer.data)
