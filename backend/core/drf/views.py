from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Project, Shot


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
