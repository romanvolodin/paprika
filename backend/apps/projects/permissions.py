from http import HTTPStatus

from dmr import APIError

from apps.projects.models import Project, ProjectMembership
from apps.users.models import User


def require_can_write(user: User, project: Project) -> None:
    """Reject read-only project members (role `client`) with a 403.

    Callers have already established that `user` is a member of
    `project` (the `_get_*_or_404` helpers answer 404 to non-members),
    so this only has to look at the role. Other role-based differences
    (executor, freelancer) are intentionally not modelled yet - they'll
    be added for shots, versions and tasks together.
    """
    is_client = ProjectMembership.objects.filter(
        project=project, user=user, role=ProjectMembership.Role.CLIENT
    ).exists()
    if is_client:
        raise APIError(
            {"detail": "Your role in this project is read-only."},
            status_code=HTTPStatus.FORBIDDEN,
        )


def require_can_manage_project(user: User, project: Project) -> None:
    """Reject everyone except project admins and producers with a 403.

    Same precondition as `require_can_write`: the caller has already
    established that `user` is a member of `project`.
    """
    can_manage = ProjectMembership.objects.filter(
        project=project,
        user=user,
        role__in=[ProjectMembership.Role.ADMIN, ProjectMembership.Role.PRODUCER],
    ).exists()
    if not can_manage:
        raise APIError(
            {"detail": "Only a project admin or producer can do this."},
            status_code=HTTPStatus.FORBIDDEN,
        )
