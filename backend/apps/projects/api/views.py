from http import HTTPStatus

from django.core.paginator import Paginator
from dmr import (
    APIError,
    Body,
    FileMetadata,
    Path,
    Query,
    ResponseSpec,
    modify,
)
from dmr.errors import ErrorType
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer

from apps.auth.api.controllers import AuthenticatedController
from apps.companies.models import Company
from apps.core.storage import delete_stored_file
from apps.projects.models import Project, ProjectMembership
from apps.projects.permissions import require_can_manage_project
from apps.users.api.views import _serialize_user
from apps.users.models import User

from .schemas import (
    CompanyProjectsPath,
    ProjectCoverFiles,
    ProjectCreateIn,
    ProjectListOut,
    ProjectListQuery,
    ProjectMemberCreateIn,
    ProjectMemberListOut,
    ProjectMemberOut,
    ProjectMemberPath,
    ProjectMemberUpdateIn,
    ProjectOut,
    ProjectPath,
    ProjectUpdateIn,
)


def _serialize_project(request, project: Project) -> ProjectOut:
    cover_url = request.build_absolute_uri(project.cover.url) if project.cover else None
    return ProjectOut(
        id=project.id,
        company_id=project.company_id,
        name=project.name,
        code=project.code,
        description=project.description,
        cover=cover_url,
        start_date=project.start_date,
        deadline=project.deadline,
        is_active=project.is_active,
        created_by=_serialize_user(request, project.created_by)
        if project.created_by
        else None,
        updated_by=_serialize_user(request, project.updated_by)
        if project.updated_by
        else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _apply_cover(project: Project, files: ProjectCoverFiles, request) -> None:
    """Replace the project's cover with the uploaded file, if any was sent.

    See `apps.users.api.views._apply_avatar` - same pattern, same reason
    for deleting the old file from storage directly rather than via
    `FieldFile.delete()`.
    """
    if files.cover is None:
        return

    old_name = project.cover.name if project.cover else None
    old_storage = project.cover.storage if project.cover else None

    project.cover = request.FILES["cover"]
    project.save(update_fields=["cover"])

    if old_name:
        delete_stored_file(old_storage, old_name)


def _clear_cover(project: Project) -> None:
    """Remove the project's current cover, if any."""
    old_name = project.cover.name if project.cover else None
    old_storage = project.cover.storage if project.cover else None

    project.cover = ""
    project.save(update_fields=["cover"])

    if old_name:
        delete_stored_file(old_storage, old_name)


def _serialize_member(request, membership: ProjectMembership) -> ProjectMemberOut:
    avatar_url = (
        request.build_absolute_uri(membership.user.avatar.url)
        if membership.user.avatar
        else None
    )
    return ProjectMemberOut(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        first_name=membership.user.first_name,
        last_name=membership.user.last_name,
        avatar=avatar_url,
        role=ProjectMembership.Role(membership.role),
        created_at=membership.created_at,
    )


def _get_company_or_404(user: User, company_id: int) -> Company:
    """Look up a company, scoped to companies the user is a member of.

    A company the user doesn't belong to 404s exactly like one that
    doesn't exist at all - membership isn't leaked to non-members.
    """
    try:
        return (
            Company.objects.filter(memberships__user=user).distinct().get(pk=company_id)
        )
    except Company.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Company with id={company_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_project_or_404(user: User, project_id: int) -> Project:
    """Look up a project, scoped to projects the user is a member of.

    Company membership alone doesn't grant visibility - only an explicit
    `ProjectMembership` does. A project the user isn't a member of 404s
    exactly like one that doesn't exist at all.
    """
    try:
        return (
            Project.objects.filter(memberships__user=user).distinct().get(pk=project_id)
        )
    except Project.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Project with id={project_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_membership_or_404(project: Project, user_id: int) -> ProjectMembership:
    try:
        return ProjectMembership.objects.select_related("user").get(
            project=project, user_id=user_id
        )
    except ProjectMembership.DoesNotExist as exc:
        raise APIError(
            {"detail": (f"User with id={user_id} is not a member of this project.")},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_company_member_or_404(company: Company, user_id: int) -> User:
    """Look up a user, scoped to members of the given company.

    Project membership can only be granted to existing company members,
    so this both validates the target user exists and that they belong
    to the right company.
    """
    try:
        return User.objects.get(pk=user_id, company_memberships__company=company)
    except User.DoesNotExist as exc:
        raise APIError(
            {
                "detail": (
                    f"User with id={user_id} is not a member of this project's company."
                )
            },
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


class ProjectListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/<company_id>/projects/` - list and create
    projects within a company.

    A user only ever sees projects they're an explicit member of, even
    within a company they belong to. Creating a project automatically
    makes the creator an `ADMIN` member of it.
    """

    @modify(
        summary="List a company's projects",
        description=(
            "Return a paginated list of projects within the given company "
            "that the current user is a member of, optionally filtered by "
            "`search` against the name."
        ),
        response_description="A page of projects.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Projects"],
    )
    def get(
        self,
        parsed_path: Path[CompanyProjectsPath],
        parsed_query: Query[ProjectListQuery],
    ) -> ProjectListOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)

        queryset = Project.objects.filter(
            company=company, memberships__user=self.request.user
        ).distinct()

        if parsed_query.search:
            queryset = queryset.filter(name__icontains=parsed_query.search)

        if parsed_query.code:
            queryset = queryset.filter(code=parsed_query.code)

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        return ProjectListOut(
            items=[
                _serialize_project(self.request, project)
                for project in page.object_list
            ],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )

    @modify(
        parsers=[MultiPartParser()],
        status_code=HTTPStatus.CREATED,
        summary="Create a project",
        description=(
            "Create a new project within the company, optionally with a "
            "cover image. Send as `multipart/form-data`: regular fields "
            "for `name`, `code`, `description`, `start_date`, `deadline`, "
            "plus an optional `cover` file field. The creator is "
            "automatically added as an `admin` member."
        ),
        response_description="The created project.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
        ],
        tags=["Projects"],
    )
    def post(
        self,
        parsed_path: Path[CompanyProjectsPath],
        parsed_body: Body[ProjectCreateIn],
        parsed_file_metadata: FileMetadata[ProjectCoverFiles],
    ) -> ProjectOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)

        if Project.objects.filter(company=company, code=parsed_body.code).exists():
            raise APIError(
                self.format_error(
                    "A project with this code already exists in this company.",
                    loc=["code"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        project = Project.objects.create(
            company=company,
            name=parsed_body.name,
            code=parsed_body.code,
            description=parsed_body.description,
            start_date=parsed_body.start_date,
            deadline=parsed_body.deadline,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        ProjectMembership.objects.create(
            user=self.request.user,
            project=project,
            role=ProjectMembership.Role.ADMIN,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        _apply_cover(project, parsed_file_metadata, self.request)
        return _serialize_project(self.request, project)


class ProjectDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/projects/<id>/` - manage a single project."""

    @modify(
        summary="Get a project",
        description="Return a single project by id.",
        response_description="The requested project.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Projects"],
    )
    def get(self, parsed_path: Path[ProjectPath]) -> ProjectOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        return _serialize_project(self.request, project)

    @modify(
        parsers=[MultiPartParser()],
        summary="Update a project",
        description=(
            "Partially update a project, optionally replacing or removing "
            "its cover in the same request. Send as `multipart/form-data`: "
            "any of `name`, `description`, `start_date`, `deadline`, "
            "`is_active`, `remove_cover`, plus an optional `cover` file "
            "field. Only fields actually present are changed. `code` "
            "cannot be changed - it's immutable once set."
        ),
        response_description="The updated project.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
        ],
        tags=["Projects"],
    )
    def patch(
        self,
        parsed_path: Path[ProjectPath],
        parsed_body: Body[ProjectUpdateIn],
        parsed_file_metadata: FileMetadata[ProjectCoverFiles],
    ) -> ProjectOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)

        update_fields = parsed_body.model_dump(
            exclude={"remove_cover"},
            exclude_unset=True,
        )
        for field, value in update_fields.items():
            setattr(project, field, value)
        if update_fields:
            project.updated_by = self.request.user
            project.save(update_fields=[*update_fields, "updated_by"])

        if parsed_file_metadata.cover is not None:
            _apply_cover(project, parsed_file_metadata, self.request)
        elif parsed_body.remove_cover and project.cover:
            _clear_cover(project)

        return _serialize_project(self.request, project)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a project",
        description=(
            "Permanently delete a project and everything in it. Only a "
            "project admin or producer can do this."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Projects"],
    )
    def delete(self, parsed_path: Path[ProjectPath]) -> None:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        require_can_manage_project(self.request.user, project)
        project.delete()
        return None


class ProjectMemberListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/projects/<id>/members/` - list and add members."""

    @modify(
        summary="List project members",
        description="Return every member of the project.",
        response_description="The project's members.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Projects"],
    )
    def get(self, parsed_path: Path[ProjectPath]) -> ProjectMemberListOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        memberships = project.memberships.select_related("user").order_by("user__email")
        return ProjectMemberListOut(
            items=[
                _serialize_member(self.request, membership)
                for membership in memberships
            ]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Add a project member",
        description=(
            "Add an existing company member to the project with the given "
            "role. The target user must already be a member of the "
            "project's company."
        ),
        response_description="The created membership.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
        ],
        tags=["Projects"],
    )
    def post(
        self,
        parsed_path: Path[ProjectPath],
        parsed_body: Body[ProjectMemberCreateIn],
    ) -> ProjectMemberOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        target_user = _get_company_member_or_404(project.company, parsed_body.user_id)

        if ProjectMembership.objects.filter(project=project, user=target_user).exists():
            raise APIError(
                self.format_error(
                    "This user is already a member of the project.",
                    loc=["user_id"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        membership = ProjectMembership.objects.create(
            user=target_user,
            project=project,
            role=parsed_body.role,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_member(self.request, membership)


class ProjectMemberDetailController(AuthenticatedController[PydanticSerializer]):
    """`PATCH/DELETE /api/v1/projects/<id>/members/<user_id>/` - manage a member."""

    @modify(
        summary="Update a project member's role",
        description="Change the role of an existing project member.",
        response_description="The updated membership.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Projects"],
    )
    def patch(
        self,
        parsed_path: Path[ProjectMemberPath],
        parsed_body: Body[ProjectMemberUpdateIn],
    ) -> ProjectMemberOut:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        membership = _get_membership_or_404(project, parsed_path.user_id)

        membership.role = parsed_body.role
        membership.updated_by = self.request.user
        membership.save(update_fields=["role", "updated_by"])

        return _serialize_member(self.request, membership)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Remove a project member",
        description="Remove a member from the project.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Projects"],
    )
    def delete(self, parsed_path: Path[ProjectMemberPath]) -> None:
        project = _get_project_or_404(self.request.user, parsed_path.project_id)
        membership = _get_membership_or_404(project, parsed_path.user_id)
        membership.delete()
        return None
