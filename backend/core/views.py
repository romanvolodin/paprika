import re
import subprocess
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import HttpResponse, get_object_or_404, render
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User

from .forms import ReadXlsxForm, UploadMultiplePreviewsForm, UploadMultipleVersionsForm
from .models import (
    ChatMessage,
    Project,
    Shot,
    ShotGroup,
    ShotTask,
    Status,
    Task,
    TmpShotPreview,
    Version,
)
from .serializers import (
    ChatMessageSerializer,
    GroupSerializer,
    ProjectSerializer,
    ShotGroupDetailsSerializer,
    ShotGroupListSerializer,
    ShotSerializer,
    ShotTaskSerializer,
    StatusSerializer,
    TaskDetailsSerializer,
    TaskListSerializer,
    UserSerializer,
    VersionSerializer,
)


@login_required
def read_xlsx(request):
    if request.method == "POST":
        form = ReadXlsxForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "core/xlsx_read.html", {"form": form})

        shot_group = form.cleaned_data["shot_group"]
        created_by = form.cleaned_data["created_by"]
        start_row = form.cleaned_data["start_row"]
        end_row = form.cleaned_data["end_row"]
        shot_name_column = form.cleaned_data["shot_name_column"]
        rec_timecode_column = form.cleaned_data["rec_timecode_column"]
        src_name_column = form.cleaned_data["source_name_column"]
        src_start_tc_column = form.cleaned_data["source_start_timecode_column"]
        src_end_tc_column = form.cleaned_data["source_end_timecode_column"]
        pixel_aspect_column = form.cleaned_data["pixel_aspect_column"]
        retime_speed_column = form.cleaned_data["retime_speed_column"]
        scene_column = form.cleaned_data["scene_column"]
        task_column = form.cleaned_data["task_column"]

        status_not_started = Status.objects.get(title="Не начата")

        new_shots = []

        wb = load_workbook(request.FILES["xlsx_file"])
        active_sheet = wb.active
        for row_number in range(start_row, end_row + 1):
            fields = {
                "created_by": created_by,
                "project": shot_group.project,
            }

            name = active_sheet[f"{shot_name_column}{row_number}"].value
            fields["name"] = name

            rec_timecode = active_sheet[f"{rec_timecode_column}{row_number}"].value
            if rec_timecode is not None:
                fields["rec_timecode"] = rec_timecode

            source_name = active_sheet[f"{src_name_column}{row_number}"].value
            if source_name is not None:
                fields["source_name"] = source_name

            source_start_timecode = active_sheet[f"{src_start_tc_column}{row_number}"].value
            if source_start_timecode is not None:
                fields["source_start_timecode"] = source_start_timecode

            source_end_timecode = active_sheet[f"{src_end_tc_column}{row_number}"].value
            if source_end_timecode is not None:
                fields["source_end_timecode"] = source_end_timecode

            pixel_aspect = active_sheet[f"{pixel_aspect_column}{row_number}"].value
            if pixel_aspect is not None:
                fields["pixel_aspect"] = pixel_aspect if isinstance(pixel_aspect, float) else 1

            retime_speed = active_sheet[f"{retime_speed_column}{row_number}"].value
            fields["retime_speed"] = retime_speed
            if retime_speed is None:
                fields["retime_speed"] = 100

            scene = active_sheet[f"{scene_column}{row_number}"].value
            if scene is not None:
                fields["scene"] = scene

            task_description = active_sheet[f"{task_column}{row_number}"].value
            if task_description is not None:
                try:
                    task = Task.objects.get(description=task_description)
                except ObjectDoesNotExist:
                    task = Task.objects.create(
                        project=shot_group.project,
                        created_by=created_by,
                        description=task_description,
                        default_status=status_not_started,
                    )

            shot = Shot.objects.create(**fields)
            shot.group.set([shot_group])

            new_shots.append(shot)

            ShotTask.objects.create(
                shot=shot,
                task=task,
                status=status_not_started,
            )
        return HttpResponse(f"{len(new_shots)} shot(s) created.")
    else:
        form = ReadXlsxForm()
    return render(request, "core/xlsx_read.html", {"form": form})


@login_required
def save_multiple_uploaded_shot_previews(request):
    if request.method == "POST":
        form = UploadMultiplePreviewsForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "core/upload_multiple_shot_previews.html", {"form": form})

        previews = form.cleaned_data["previews"]
        successful_count = 0
        errors = []
        for preview in previews:
            shot_name = preview.name.split(".")[0]

            if shot_name is None:
                errors.append(f"Нет имени шота в '{preview.name}'")
                continue

            try:
                shot = Shot.objects.get(name=shot_name)
            except ObjectDoesNotExist:
                errors.append(f"Шот '{shot_name}' не найден")
                continue

            TmpShotPreview.objects.create(shot=shot, image=preview)
            successful_count += 1
        return HttpResponse(
            f"{successful_count} картинок загружено.<br><br>Ошибки:<br>{'<br>'.join(errors)}"
        )
    else:
        form = UploadMultiplePreviewsForm()
    return render(request, "core/upload_multiple_shot_previews.html", {"form": form})


@login_required
def shot_group_list(request, project_code):
    project = Project.objects.get(code=project_code)
    shot_groups = project.shot_groups.all().order_by("name")
    context = {
        "shot_groups": shot_groups,
        "count": len(shot_groups),
    }
    return render(request, "core/shot_group_list.html", context)


@login_required
def shot_group_details(request, project_code, shot_group_id):
    shot_group = ShotGroup.objects.get(pk=shot_group_id)
    context = {
        "shot_group": shot_group,
    }
    return render(request, "core/shot_group_details.html", context)


@login_required
def task_list(request, project_code):
    project = Project.objects.get(code=project_code)
    tasks = project.tasks.all().order_by("description")
    context = {
        "tasks": tasks,
        "count": len(tasks),
    }
    return render(request, "core/task_list.html", context)


@login_required
def task_details(request, project_code, task_id):
    task = Task.objects.get(pk=task_id)
    shots = []
    for shot in task.shots.all():
        shot_task = [st for st in shot.task_statuses.all() if st.task == task][0]
        d = shot.__dict__
        d["status"] = shot_task.status.title
        d["status_color"] = shot_task.status.color

        try:
            version = shot.versions.latest()
            d["versions"] = {"latest": {"preview": {"url": version.preview.url}}}
        except ObjectDoesNotExist:
            pass

        shots.append(d)

    context = {"task": task, "shots": shots}
    return render(request, "core/task_details.html", context)


@login_required
def project_list(request):
    projects = Project.objects.order_by("name")
    context = {
        "projects": projects,
        "count": len(projects),
    }
    return render(request, "core/project_list.html", context)


@login_required
def project_details(request, project_code):
    project = Project.objects.get(code=project_code)
    context = {
        "project": project,
    }
    return render(request, "core/project_details.html", context)


@login_required
def save_multiple_uploaded_versions(request):
    if request.method == "POST":
        form = UploadMultipleVersionsForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "core/upload_multiple_versions.html", {"form": form})

        shot_name_template = form.cleaned_data["shot_name_template"]
        versions = form.cleaned_data["versions"]
        successful_count = 0
        errors = []
        for uploaded_version in versions:
            match = re.search(shot_name_template, uploaded_version.name)
            shot_name = match.group(0)

            if shot_name is None:
                errors.append(f"Нет имени шота в '{uploaded_version.name}'")
                continue

            try:
                shot = Shot.objects.get(name=shot_name)
            except ObjectDoesNotExist:
                errors.append(f"Шот '{shot_name}' не найден")
                continue

            version = Version.objects.create(
                name=Path(uploaded_version.name).stem,
                shot=shot,
                video=uploaded_version,
                created_by=request.user,
            )

            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                version.video.path,
                "-frames:v",
                "1",
                f"{version.video.path}.jpg",
            ]
            subprocess.run(cmd)
            version.preview = f"{version.video.name}.jpg"
            version.save()
            successful_count += 1

        errors_message = ""
        if errors:
            errors_message = f"<br><br>Ошибки:<br>{'<br>'.join(errors)}"

        return HttpResponse(
            (
                f"{successful_count} версий загружено.{errors_message}"
                "<br><br><a href='/dj/versions/upload/'>Загрузить ещё</a>"
            )
        )
    else:
        form = UploadMultipleVersionsForm()
    return render(request, "core/upload_multiple_versions.html", {"form": form})


def api(request):
    return JsonResponse({"message": "ok!"})


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

    queryset = Group.objects.all().order_by("name")
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class ShotViewSet(viewsets.ModelViewSet):
    queryset = Shot.objects.all()
    serializer_class = ShotSerializer

    def list(self, request, project_code=None):
        project = get_object_or_404(Project, code=project_code)
        shot_group = get_object_or_404(ShotGroup, project=project, is_default=True)
        serializer = ShotSerializer(
            shot_group.shots.order_by("name"),
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    def retrieve(self, request, project_code=None, shot_name=None):
        project = get_object_or_404(Project, code=project_code)
        shot = get_object_or_404(Shot, project=project, name=shot_name)
        serializer = ShotSerializer(shot, context={"request": request})
        return Response(serializer.data)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("name")
    serializer_class = ProjectSerializer
    # permission_classes = [permissions.IsAuthenticated]


class ShotGroupViewSet(viewsets.ModelViewSet):
    queryset = ShotGroup.objects.all().order_by("name").prefetch_related("shots")
    serializer_class = ShotGroupDetailsSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def list(self, request, project_code=None):
        project = get_object_or_404(Project, code=project_code)
        serializer = ShotGroupListSerializer(
            project.shot_groups.order_by("name"),
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    def retrieve(self, request, project_code=None, shot_group_id=None):
        project = get_object_or_404(Project, code=project_code)
        shot_group = get_object_or_404(
            ShotGroup,
            project=project,
            id=shot_group_id,
        )
        serializer = ShotGroupDetailsSerializer(shot_group, context={"request": request})
        return Response(serializer.data)


class ShotTaskViewSet(viewsets.ModelViewSet):
    queryset = ShotTask.objects.all()
    serializer_class = ShotTaskSerializer
    # permission_classes = [permissions.IsAuthenticated]


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by("description").prefetch_related("shots")
    serializer_class = TaskListSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def list(self, request, project_code=None):
        project = get_object_or_404(Project, code=project_code)
        serializer = TaskListSerializer(
            project.tasks.order_by("description"),
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    def retrieve(self, request, project_code=None, task_id=None):
        project = get_object_or_404(Project, code=project_code)
        task = get_object_or_404(Task, project=project, id=task_id)
        serializer = TaskDetailsSerializer(task, context={"request": request})
        return Response(serializer.data)


class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all().order_by("title")
    serializer_class = StatusSerializer
    # permission_classes = [permissions.IsAuthenticated]


class VersionViewSet(viewsets.ModelViewSet):
    queryset = Version.objects.all().order_by("-created_at")
    serializer_class = VersionSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, project_code=None, shot_name=None):
        project = get_object_or_404(Project, code=project_code)
        shot = get_object_or_404(Shot, project=project, name=shot_name)
        uploaded_version = request.FILES.get("file")
        version = Version.objects.create(
            name=Path(uploaded_version.name).stem,
            shot=shot,
            video=uploaded_version,
            created_by=request.user,
        )

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            version.video.path,
            "-frames:v",
            "1",
            f"{version.video.path}.jpg",
        ]
        subprocess.run(cmd)
        version.preview = f"{version.video.name}.jpg"
        version.save()

        ChatMessage.objects.create(
            shot=shot,
            created_by=request.user,
            created_at=timezone.now(),
            text=f"Загружена версия {version.name}",
        )

        serializer = VersionSerializer(version, context={"request": request})
        return Response(serializer.data)


class ChatViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all().order_by("-created_at")
    serializer_class = ChatMessageSerializer
    # permission_classes = [permissions.IsAuthenticated]
