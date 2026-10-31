"""Who can see what, and who can do what.

Every endpoint goes through this module: the `visible_*` helpers and the
`*_q` filters decide which companies, projects and their contents a user
sees at all (everything else answers 404), and `require_*` decide whether
they may act on something they see (403).

A superuser (the server administrator) passes every check and sees every
company and project.
"""

from http import HTTPStatus

from django.db.models import Q, QuerySet
from dmr import APIError

from apps.companies.models import Company, CompanyMembership
from apps.projects.models import Project, ProjectMembership
from apps.users.models import User

from .models import Role
from .permissions import COMPANY_CODES, PROJECT_CODES, P


def visible_companies(user: User) -> QuerySet[Company]:
    """Companies the user belongs to (all of them for a superuser)."""
    if user.is_superuser:
        return Company.objects.all()
    return Company.objects.filter(memberships__user=user)


def visible_projects(user: User) -> QuerySet[Project]:
    """Projects the user can see.

    A project is visible to its members, and to members of its company
    whose company role has `sees_all_projects`.
    """
    if user.is_superuser:
        return Project.objects.all()
    return Project.objects.filter(
        Q(memberships__user=user)
        | Q(
            company__memberships__user=user,
            company__memberships__role__sees_all_projects=True,
        )
    )


def companies_q(user: User, lookup: str = "company") -> Q:
    """A filter keeping only rows of companies the user can see.

    `lookup` is the path from the filtered model to its company
    (`company`, `project__company`...).
    """
    if user.is_superuser:
        return Q()
    return Q(**{f"{lookup}__in": visible_companies(user).values("pk")})


def projects_q(user: User, lookup: str = "project") -> Q:
    """A filter keeping only rows of projects the user can see."""
    if user.is_superuser:
        return Q()
    return Q(**{f"{lookup}__in": visible_projects(user).values("pk")})


def company_permissions(user: User, company: Company) -> frozenset[str]:
    """What the user may do in the company itself."""
    if user.is_superuser:
        return COMPANY_CODES
    codes = (
        CompanyMembership.objects.filter(user=user, company=company)
        .values_list("role__permissions", flat=True)
        .first()
    )
    return COMPANY_CODES & frozenset(codes or ())


def company_permissions_by_id(
    user: User, company_ids: list[int]
) -> dict[int, frozenset[str]]:
    """`company_permissions` for several companies at once (for lists)."""
    if user.is_superuser:
        return {pk: COMPANY_CODES for pk in company_ids}
    rows = CompanyMembership.objects.filter(
        user=user, company_id__in=company_ids
    ).values_list("company_id", "role__permissions")
    return {pk: COMPANY_CODES & frozenset(codes or ()) for pk, codes in rows}


def project_permissions(user: User, project: Project) -> frozenset[str]:
    """What the user may do inside the project."""
    if user.is_superuser:
        return PROJECT_CODES
    codes = (
        ProjectMembership.objects.filter(user=user, project=project)
        .values_list("role__permissions", flat=True)
        .first()
    )
    if codes is None:
        # Not a member: only a company role that sees every project reaches in.
        codes = (
            CompanyMembership.objects.filter(
                user=user, company_id=project.company_id, role__sees_all_projects=True
            )
            .values_list("role__permissions", flat=True)
            .first()
        )
    return PROJECT_CODES & frozenset(codes or ())


def project_permissions_by_id(
    user: User, projects: list[Project]
) -> dict[int, frozenset[str]]:
    """`project_permissions` for several projects at once (for lists)."""
    if user.is_superuser:
        return {project.pk: PROJECT_CODES for project in projects}
    own = dict(
        ProjectMembership.objects.filter(
            user=user, project__in=[project.pk for project in projects]
        ).values_list("project_id", "role__permissions")
    )
    wide = dict(
        CompanyMembership.objects.filter(
            user=user,
            company_id__in={project.company_id for project in projects},
            role__sees_all_projects=True,
        ).values_list("company_id", "role__permissions")
    )
    result = {}
    for project in projects:
        codes = own.get(project.pk)
        if codes is None:
            codes = wide.get(project.company_id)
        result[project.pk] = PROJECT_CODES & frozenset(codes or ())
    return result


def can_in_company(user: User, company: Company, code: str) -> bool:
    return code in company_permissions(user, company)


def can_in_project(user: User, project: Project, code: str) -> bool:
    return code in project_permissions(user, project)


def _forbidden() -> APIError:
    return APIError(
        {"detail": "You don't have permission to do this."},
        status_code=HTTPStatus.FORBIDDEN,
    )


def require_company_perm(user: User, company: Company, code: str) -> None:
    """Reject with a 403 unless the user's company role has the permission."""
    if code not in company_permissions(user, company):
        raise _forbidden()


def require_project_perm(user: User, project: Project, code: str) -> None:
    """Reject with a 403 unless the user's role in the project has the permission."""
    if code not in project_permissions(user, project):
        raise _forbidden()


def require_superuser(user: User) -> None:
    if not user.is_superuser:
        raise _forbidden()


def _has_role_manager(
    company: Company,
    *,
    remove_user_id: int | None = None,
    move: tuple[int, Role] | None = None,
    edit: tuple[int, list[str]] | None = None,
) -> bool:
    for membership in CompanyMembership.objects.filter(company=company).select_related(
        "role"
    ):
        if membership.user_id == remove_user_id:
            continue
        role = membership.role
        permissions = role.permissions
        if move and membership.user_id == move[0]:
            role = move[1]
            permissions = role.permissions
        if edit and role.id == edit[0]:
            permissions = edit[1]
        if P.COMPANY_ROLES in permissions:
            return True
    return False


def role_manager_would_vanish(
    company: Company,
    *,
    remove_user_id: int | None = None,
    move: tuple[int, Role] | None = None,
    edit: tuple[int, list[str]] | None = None,
) -> bool:
    """Whether a change would leave the company with nobody who can edit roles.

    `remove_user_id` takes a member out, `move=(user_id, role)` gives a
    member another role, `edit=(role_id, permissions)` changes what a role
    allows. A company that already has nobody like that isn't blocked.
    """
    if not _has_role_manager(company):
        return False
    return not _has_role_manager(
        company, remove_user_id=remove_user_id, move=move, edit=edit
    )


def _company_role_sees_all_projects(user: User, company: Company) -> bool:
    return CompanyMembership.objects.filter(
        user=user, company=company, role__sees_all_projects=True
    ).exists()


def can_grant_company_role(user: User, company: Company, role: Role) -> bool:
    """Whether the user may give `role` to someone in the company.

    Nobody can hand out more than they have: the role's company permissions
    must all be among the user's own, and a role that sees every project
    only goes to someone who sees every project themselves.
    """
    if user.is_superuser:
        return True
    if not (COMPANY_CODES & frozenset(role.permissions)) <= company_permissions(
        user, company
    ):
        return False
    return not role.sees_all_projects or _company_role_sees_all_projects(user, company)


def can_grant_project_role(user: User, project: Project, role: Role) -> bool:
    """Whether the user may give `role` to someone in the project."""
    if user.is_superuser:
        return True
    return (PROJECT_CODES & frozenset(role.permissions)) <= project_permissions(
        user, project
    )


def require_can_grant_company_role(user: User, company: Company, role: Role) -> None:
    if not can_grant_company_role(user, company, role):
        raise _forbidden()


def require_can_grant_project_role(user: User, project: Project, role: Role) -> None:
    if not can_grant_project_role(user, project, role):
        raise _forbidden()
