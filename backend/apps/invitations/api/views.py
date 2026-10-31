from http import HTTPStatus

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from dmr import APIError, Body, Controller, Path, ResponseSpec, modify
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer

from apps.access.api.schemas import RoleRefOut
from apps.access.checks import (
    companies_q,
    projects_q,
    require_can_grant_company_role,
    require_can_grant_project_role,
    require_company_perm,
    require_project_perm,
)
from apps.access.models import Role
from apps.access.permissions import COMPANY_CODES, P
from apps.auth.api.controllers import AuthenticatedController
from apps.companies.models import Company, CompanyMembership
from apps.projects.models import Project
from apps.users.models import User

from ..models import Invitation, InvitationProject
from ..services import accept_invitation
from .schemas import (
    CompanyInvitationsPath,
    InvitationCreateIn,
    InvitationInfoOut,
    InvitationListOut,
    InvitationOut,
    InvitationPath,
    ProjectInvitationCreateIn,
    ProjectInvitationsPath,
    RegisterIn,
    TokenPath,
)


_FORBIDDEN = ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN)
_NOT_FOUND = ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND)
_BAD_REQUEST = ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST)
_CONFLICT = ResponseSpec(dict, status_code=HTTPStatus.CONFLICT)
_GONE = ResponseSpec(dict, status_code=HTTPStatus.GONE)


def _error(controller, message: str, loc: list[str], status: HTTPStatus) -> APIError:
    return APIError(
        controller.format_error(message, loc=loc, error_type=ErrorType.value_error),
        status_code=status,
    )


def _serialize(invitation: Invitation) -> InvitationOut:
    creator = invitation.created_by
    return InvitationOut(
        id=invitation.id,
        company_id=invitation.company_id,
        email=invitation.email,
        role=RoleRefOut(
            id=invitation.role.id,
            name=invitation.role.name,
            color=invitation.role.color,
        ),
        projects=[
            {
                "project_id": invited.project_id,
                "project_name": invited.project.name,
                "role": RoleRefOut(
                    id=invited.role.id, name=invited.role.name, color=invited.role.color
                ),
            }
            for invited in invitation.projects.select_related("project", "role")
        ],
        token=invitation.token,
        expires_at=invitation.expires_at,
        is_expired=invitation.is_expired,
        created_by_name=(creator.get_full_name() or creator.email) if creator else None,
        created_at=invitation.created_at,
    )


def _get_company_or_404(user: User, company_id: int) -> Company:
    try:
        return Company.objects.filter(companies_q(user, "pk")).get(pk=company_id)
    except Company.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Company with id={company_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_project_or_404(user: User, project_id: int) -> Project:
    try:
        return (
            Project.objects.filter(projects_q(user, "pk"))
            .select_related("company")
            .get(pk=project_id)
        )
    except Project.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Project with id={project_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_invitation_or_404(user: User, invitation_id: int) -> Invitation:
    try:
        return (
            Invitation.objects.filter(companies_q(user), accepted_at__isnull=True)
            .select_related("company", "role", "created_by")
            .get(pk=invitation_id)
        )
    except Invitation.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Invitation with id={invitation_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _require_can_manage(user: User, invitation: Invitation) -> None:
    """Company managers manage every invitation, others only the ones they sent."""
    if invitation.created_by_id == user.id:
        return
    require_company_perm(user, invitation.company, P.COMPANY_MEMBERS)


def _get_role_or_400(
    controller, company: Company, role_id: int, loc: list[str]
) -> Role:
    try:
        return Role.objects.get(pk=role_id, company=company)
    except Role.DoesNotExist as exc:
        raise _error(
            controller,
            "This role does not belong to the company.",
            loc,
            HTTPStatus.BAD_REQUEST,
        ) from exc


def _clear_expired_for(company: Company, email: str) -> None:
    """Drop an old, expired invitation so the person can be invited again."""
    from django.utils import timezone

    Invitation.objects.filter(
        company=company,
        email__iexact=email,
        accepted_at__isnull=True,
        expires_at__lte=timezone.now(),
    ).delete()


def _create(
    controller,
    *,
    company: Company,
    email: str,
    role: Role,
    projects: list[tuple[Project, Role]],
) -> Invitation:
    email = User.objects.normalize_email(email)
    if CompanyMembership.objects.filter(
        company=company, user__email__iexact=email
    ).exists():
        raise _error(
            controller,
            "This person is already a member of the company.",
            ["email"],
            HTTPStatus.BAD_REQUEST,
        )
    _clear_expired_for(company, email)
    try:
        with transaction.atomic():
            invitation = Invitation.objects.create(
                company=company,
                email=email,
                role=role,
                created_by=controller.request.user,
                updated_by=controller.request.user,
            )
            for project, project_role in projects:
                InvitationProject.objects.create(
                    invitation=invitation, project=project, role=project_role
                )
    except IntegrityError as exc:
        raise _error(
            controller,
            "This person has already been invited. Renew the invitation to "
            "get a new link.",
            ["email"],
            HTTPStatus.CONFLICT,
        ) from exc
    return invitation


class CompanyInvitationListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/<id>/invitations/`."""

    @modify(
        summary="List a company's open invitations",
        description=(
            "Return the invitations of the company that nobody has accepted "
            "yet, expired ones included. Needs the `company.members` "
            "permission."
        ),
        response_description="The open invitations.",
        extra_responses=[_NOT_FOUND, _FORBIDDEN],
        tags=["Invitations"],
    )
    def get(self, parsed_path: Path[CompanyInvitationsPath]) -> InvitationListOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_MEMBERS)
        invitations = (
            Invitation.objects.filter(company=company, accepted_at__isnull=True)
            .select_related("role", "created_by")
            .order_by("-created_at")
        )
        return InvitationListOut(items=[_serialize(i) for i in invitations])

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Invite someone to a company",
        description=(
            "Invite a person by email, with a role in the company and, if "
            "wanted, projects with their roles. Nothing is sent: pass the "
            "link on yourself. You can only give roles that carry no more "
            "than you have. Needs the `company.members` permission."
        ),
        response_description="The invitation, with its token.",
        extra_responses=[_NOT_FOUND, _BAD_REQUEST, _FORBIDDEN, _CONFLICT],
        tags=["Invitations"],
    )
    def post(
        self,
        parsed_path: Path[CompanyInvitationsPath],
        parsed_body: Body[InvitationCreateIn],
    ) -> InvitationOut:
        user = self.request.user
        company = _get_company_or_404(user, parsed_path.company_id)
        require_company_perm(user, company, P.COMPANY_MEMBERS)
        role = _get_role_or_400(self, company, parsed_body.role_id, ["role_id"])
        require_can_grant_company_role(user, company, role)

        projects: list[tuple[Project, Role]] = []
        seen: set[int] = set()
        for index, item in enumerate(parsed_body.projects):
            loc = ["projects", str(index)]
            if item.project_id in seen:
                raise _error(self, "Duplicate project.", loc, HTTPStatus.BAD_REQUEST)
            seen.add(item.project_id)
            project = _get_project_or_404(user, item.project_id)
            if project.company_id != company.id:
                raise _error(
                    self,
                    "This project does not belong to the company.",
                    loc,
                    HTTPStatus.BAD_REQUEST,
                )
            project_role = _get_role_or_400(self, company, item.role_id, loc)
            require_can_grant_project_role(user, project, project_role)
            projects.append((project, project_role))

        invitation = _create(
            self, company=company, email=parsed_body.email, role=role, projects=projects
        )
        return _serialize(invitation)


class ProjectInvitationController(AuthenticatedController[PydanticSerializer]):
    """`POST /api/v1/projects/<id>/invitations/` - invite someone to one project."""

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Invite someone to a project",
        description=(
            "Invite a person by email to this project with the given role. "
            "They join the company too, and the same role is their role "
            "there, so a role that carries company permissions can only be "
            "given by inviting to the company. Needs the `project.members` "
            "permission."
        ),
        response_description="The invitation, with its token.",
        extra_responses=[_NOT_FOUND, _BAD_REQUEST, _FORBIDDEN, _CONFLICT],
        tags=["Invitations"],
    )
    def post(
        self,
        parsed_path: Path[ProjectInvitationsPath],
        parsed_body: Body[ProjectInvitationCreateIn],
    ) -> InvitationOut:
        user = self.request.user
        project = _get_project_or_404(user, parsed_path.project_id)
        require_project_perm(user, project, P.PROJECT_MEMBERS)
        company = project.company
        role = _get_role_or_400(self, company, parsed_body.role_id, ["role_id"])
        if (COMPANY_CODES & set(role.permissions)) or role.sees_all_projects:
            raise _error(
                self,
                "A role with company rights can only be given by inviting "
                "to the company.",
                ["role_id"],
                HTTPStatus.BAD_REQUEST,
            )
        require_can_grant_project_role(user, project, role)

        invitation = _create(
            self,
            company=company,
            email=parsed_body.email,
            role=role,
            projects=[(project, role)],
        )
        return _serialize(invitation)


class InvitationDetailController(AuthenticatedController[PydanticSerializer]):
    """`DELETE /api/v1/invitations/<id>/` - take an invitation back."""

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Revoke an invitation",
        description=(
            "Delete an invitation that nobody has accepted; its link stops "
            "working. Allowed for whoever sent it and for those with the "
            "`company.members` permission."
        ),
        extra_responses=[_NOT_FOUND, _FORBIDDEN],
        tags=["Invitations"],
    )
    def delete(self, parsed_path: Path[InvitationPath]) -> None:
        invitation = _get_invitation_or_404(
            self.request.user, parsed_path.invitation_id
        )
        _require_can_manage(self.request.user, invitation)
        invitation.delete()
        return None


class InvitationRenewController(AuthenticatedController[PydanticSerializer]):
    """`POST /api/v1/invitations/<id>/renew/` - a new link and a fresh term."""

    @modify(
        status_code=HTTPStatus.OK,
        summary="Renew an invitation",
        description=(
            "Give an invitation that nobody has accepted a new link and a "
            "fresh term; the old link stops working. Allowed for whoever "
            "sent it and for those with the `company.members` permission."
        ),
        response_description="The invitation with its new token.",
        extra_responses=[_NOT_FOUND, _FORBIDDEN],
        tags=["Invitations"],
    )
    def post(self, parsed_path: Path[InvitationPath]) -> InvitationOut:
        invitation = _get_invitation_or_404(
            self.request.user, parsed_path.invitation_id
        )
        _require_can_manage(self.request.user, invitation)
        invitation.renew()
        invitation.updated_by = self.request.user
        invitation.save(
            update_fields=["token", "expires_at", "updated_by", "updated_at"]
        )
        return _serialize(invitation)


# --- What the person who got the link does. No account needed to look. ------


def _get_by_token_or_404(token: str) -> Invitation:
    try:
        return Invitation.objects.select_related("company", "role").get(token=token)
    except Invitation.DoesNotExist as exc:
        raise APIError(
            {"detail": "This invitation link is not valid."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _require_open(invitation: Invitation) -> None:
    if invitation.is_accepted or invitation.is_expired:
        raise APIError(
            {"detail": "This invitation has been used or has expired."},
            status_code=HTTPStatus.GONE,
        )


class InviteInfoController(Controller[PydanticSerializer]):
    """`GET /api/v1/invite/<token>/` - what the link is for."""

    auth = None

    @modify(
        summary="Look at an invitation link",
        description=(
            "Public. Tell the holder of an invitation link whom it invites, "
            "where to, and whether that email already has an account."
        ),
        response_description="What the invitation offers.",
        extra_responses=[_NOT_FOUND],
        tags=["Invitations"],
    )
    def get(self, parsed_path: Path[TokenPath]) -> InvitationInfoOut:
        invitation = _get_by_token_or_404(parsed_path.token)
        if invitation.is_accepted:
            status = "accepted"
        elif invitation.is_expired:
            status = "expired"
        else:
            status = "pending"
        return InvitationInfoOut(
            email=invitation.email,
            company_id=invitation.company_id,
            company_name=invitation.company.name,
            role_name=invitation.role.name,
            project_names=[
                invited.project.name
                for invited in invitation.projects.select_related("project")
            ],
            expires_at=invitation.expires_at,
            status=status,
            account_exists=User.objects.filter(email__iexact=invitation.email).exists(),
        )


class InviteRegisterController(Controller[PydanticSerializer]):
    """`POST /api/v1/invite/<token>/register/` - make an account and join."""

    auth = None

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Make an account from an invitation",
        description=(
            "Public. Create the account of the invited email with the name "
            "and password given and accept the invitation. Sign in "
            "afterwards. If the email already has an account, accept the "
            "invitation while signed in to it instead (409)."
        ),
        extra_responses=[_NOT_FOUND, _BAD_REQUEST, _CONFLICT, _GONE],
        tags=["Invitations"],
    )
    def post(self, parsed_path: Path[TokenPath], parsed_body: Body[RegisterIn]) -> None:
        invitation = _get_by_token_or_404(parsed_path.token)
        _require_open(invitation)
        if User.objects.filter(email__iexact=invitation.email).exists():
            raise APIError(
                {"detail": "This email already has an account: sign in to accept."},
                status_code=HTTPStatus.CONFLICT,
            )
        try:
            validate_password(parsed_body.password)
        except DjangoValidationError as exc:
            raise _error(
                self, " ".join(exc.messages), ["password"], HTTPStatus.BAD_REQUEST
            ) from exc

        with transaction.atomic():
            user = User.objects.create_user(
                email=invitation.email,
                password=parsed_body.password,
                first_name=parsed_body.first_name,
                last_name=parsed_body.last_name,
            )
            accept_invitation(invitation, user)
        return None


class InviteAcceptController(AuthenticatedController[PydanticSerializer]):
    """`POST /api/v1/invite/<token>/accept/` - join with the account you have."""

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Accept an invitation",
        description=(
            "Accept the invitation as the signed-in user, whose email has to "
            "be the invited one (403 otherwise)."
        ),
        extra_responses=[_NOT_FOUND, _FORBIDDEN, _GONE],
        tags=["Invitations"],
    )
    def post(self, parsed_path: Path[TokenPath]) -> None:
        invitation = _get_by_token_or_404(parsed_path.token)
        _require_open(invitation)
        if self.request.user.email.lower() != invitation.email.lower():
            raise APIError(
                {"detail": "This invitation is for another email."},
                status_code=HTTPStatus.FORBIDDEN,
            )
        accept_invitation(invitation, self.request.user)
        return None
