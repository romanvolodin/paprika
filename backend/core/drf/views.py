from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import (
    ChatMessage,
    Project,
    Shot,
    ShotGroup,
    ShotTask,
    Status,
    Task,
    Version,
)
from core.serializers import (
    FeedItemSerializer,
    ShotGroupCreateSerializer,
    ShotTaskSerializer,
)
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
                ChatMessage.objects.create(
                    shot=shot,
                    created_by=user,
                    created_at=timezone.now(),
                    text=task.description,
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
    assigned_to_id = request.query_params.get("assigned_to")

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
                    queryset=ShotTask.objects.select_related(
                        "task", "status", "assigned_to"
                    ).exclude(task__description="Выдать материал"),
                    to_attr="filtered_tasks",
                ),
            ),
        )
    )

    out_shot_groups = []
    for shot_group in shot_groups:
        shots = []
        for shot in shot_group.shots.all():
            # Собираем уникальных исполнителей
            assignees = []
            seen_ids = set()
            for st in shot.filtered_tasks:
                if st.assigned_to and st.assigned_to.id not in seen_ids:
                    seen_ids.add(st.assigned_to.id)
                    full_name = f"{st.assigned_to.first_name} {st.assigned_to.last_name}".strip()
                    assignees.append(
                        {
                            "id": st.assigned_to.id,
                            "name": full_name,
                        }
                    )

            # Фильтрация по исполнителю, если задан
            if assigned_to_id:
                try:
                    assigned_to_id_int = int(assigned_to_id)
                except ValueError:
                    pass
                else:
                    if not any(a["id"] == assigned_to_id_int for a in assignees):
                        continue  # пропускаем шот

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
                    "assignees": assignees,  # добавляем список исполнителей
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


@api_view(["GET"])
def project_feed(request, project_code: str):
    project = get_object_or_404(Project, code=project_code)

    LIMIT = 50
    my_only = request.query_params.get("my") == "true"

    versions = Version.objects.filter(shot__project=project).select_related(
        "created_by", "shot"
    ).order_by("-created_at")[:LIMIT*2]

    tasks = Task.objects.filter(project=project).select_related(
        "created_by"
    ).order_by("-created_at")[:LIMIT]

    chat_messages = (
        ChatMessage.objects.filter(shot__project=project)
        .select_related("created_by", "shot")
        .prefetch_related("attachments")
        .order_by("-created_at")[: LIMIT * 2]
    )

    # Если фильтр "мои" — определяем шоты, где есть задачи, назначенные на текущего пользователя
    if my_only and request.user.is_authenticated:
        my_shot_ids = set(
            ShotTask.objects.filter(
                assigned_to=request.user,
                shot__project=project,
            )
            .values_list("shot_id", flat=True)
            .distinct()
        )
        my_task_ids = set(
            ShotTask.objects.filter(
                assigned_to=request.user,
                shot__project=project,
            )
            .values_list("task_id", flat=True)
            .distinct()
        )
    else:
        my_shot_ids = None
        my_task_ids = None

    feed_items = []

    for v in versions:
        if my_shot_ids is not None and v.shot_id not in my_shot_ids:
            continue
        feed_items.append({
            "type": "version",
            "id": v.id,
            "created_at": v.created_at,
            "created_by": v.created_by,
            "data": {
                "name": v.name,
                "shot_name": v.shot.name,
                "preview": request.build_absolute_uri(v.preview.url) if v.preview else None,
                "video": request.build_absolute_uri(v.video.url) if v.video else None,
            },
        })

    for t in tasks:
        if my_task_ids is not None and t.id not in my_task_ids:
            continue
        feed_items.append({
            "type": "task",
            "id": t.id,
            "created_at": t.created_at,
            "created_by": t.created_by,
            "data": {
                "description": t.description,
            },
        })

    for cm in chat_messages:
        if my_shot_ids is not None and cm.shot_id not in my_shot_ids:
            continue

        attachments_data = []
        for att in cm.attachments.all():
            attachment = {
                "id": att.id,
                "file": request.build_absolute_uri(att.file.url) if att.file else None,
            }
            if att.preview:
                attachment["preview"] = request.build_absolute_uri(att.preview.url)
            attachments_data.append(attachment)

        feed_items.append(
            {
                "type": "chat_message",
                "id": cm.id,
                "created_at": cm.created_at,
                "created_by": cm.created_by,
                "data": {
                    "shot_name": cm.shot.name,
                    "text": cm.text[:100],
                    "attachments": attachments_data,
                },
            }
        )

    feed_items.sort(key=lambda x: x["created_at"], reverse=True)

    serializer = FeedItemSerializer(feed_items, many=True, context={"request": request})
    return Response(serializer.data)
