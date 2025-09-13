from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Project, Shot, ShotGroup


@api_view(["POST"])
def create_shots(request, project_code: str):
    user = request.user
    shots = request.data
    project = get_object_or_404(Project, code=project_code)
    new_shots = []
    for shot in shots:
        s = Shot.objects.create(
            name=shot["name"],
            project=project,
            created_by=user,
        )
        new_shots.append(s)
    return Response({"shots": len(new_shots)})


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
