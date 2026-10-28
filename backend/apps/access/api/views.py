from http import HTTPStatus

from django.db.models import Count, RestrictedError
from dmr import APIError, Body, Path, ResponseSpec, modify
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer

from apps.access.checks import (
    companies_q,
    require_company_perm,
    role_manager_would_vanish,
)
from apps.access.models import Role
from apps.access.permissions import P
from apps.auth.api.controllers import AuthenticatedController
from apps.companies.models import Company
from apps.users.models import User

from .schemas import (
    CompanyRolesPath,
    PermissionListOut,
    RoleCreateIn,
    RoleListOut,
    RoleOut,
    RolePath,
    RoleUpdateIn,
    permission_list,
)


def _conflict(controller, message: str, loc: list[str]) -> APIError:
    return APIError(
        controller.format_error(message, loc=loc, error_type=ErrorType.value_error),
        status_code=HTTPStatus.CONFLICT,
    )


def _bad_request(controller, message: str, loc: list[str]) -> APIError:
    return APIError(
        controller.format_error(message, loc=loc, error_type=ErrorType.value_error),
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _roles(company: Company):
    return Role.objects.filter(company=company).annotate(
        company_members_count=Count("company_memberships", distinct=True),
        project_members_count=Count("project_memberships", distinct=True),
    )


def _serialize_role(role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        company_id=role.company_id,
        name=role.name,
        color=role.color,
        permissions=list(role.permissions),
        sees_all_projects=role.sees_all_projects,
        company_members_count=role.company_members_count,
        project_members_count=role.project_members_count,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def _get_company_or_404(user: User, company_id: int) -> Company:
    try:
        return Company.objects.filter(companies_q(user, "pk")).get(pk=company_id)
    except Company.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Company with id={company_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_role_or_404(user: User, role_id: int) -> Role:
    try:
        role = (
            Role.objects.filter(companies_q(user))
            .select_related("company")
            .get(pk=role_id)
        )
    except Role.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Role with id={role_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc
    return _roles(role.company).get(pk=role.pk)


def _name_taken(company: Company, name: str, exclude_pk: int | None = None) -> bool:
    others = Role.objects.filter(company=company, name=name)
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)
    return others.exists()


class PermissionListController(AuthenticatedController[PydanticSerializer]):
    """`GET /api/v1/permissions/` - the fixed list of permissions."""

    @modify(
        summary="List permissions",
        description=(
            "Return every permission a role can be made of, in display "
            "order. The list is fixed: new permissions come with new "
            "features, roles only choose among them."
        ),
        response_description="All permissions.",
        tags=["Roles"],
    )
    def get(self) -> PermissionListOut:
        return permission_list()


class RoleListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/<company_id>/roles/` - a company's roles."""

    @modify(
        summary="List a company's roles",
        description=(
            "Return every role of the company (not paginated). Any member of "
            "the company can read them."
        ),
        response_description="The company's roles.",
        extra_responses=[ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND)],
        tags=["Roles"],
    )
    def get(self, parsed_path: Path[CompanyRolesPath]) -> RoleListOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        return RoleListOut(items=[_serialize_role(r) for r in _roles(company)])

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a role",
        description=(
            "Create a role in the company. The name must be unique within "
            "the company (409 otherwise). Needs the `company.roles` permission."
        ),
        response_description="The created role.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Roles"],
    )
    def post(
        self,
        parsed_path: Path[CompanyRolesPath],
        parsed_body: Body[RoleCreateIn],
    ) -> RoleOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_ROLES)

        if _name_taken(company, parsed_body.name):
            raise _conflict(
                self, "A role with this name already exists in this company.", ["name"]
            )

        role = Role.objects.create(
            company=company,
            name=parsed_body.name,
            color=parsed_body.color,
            permissions=parsed_body.permissions,
            sees_all_projects=parsed_body.sees_all_projects,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_role(_get_role_or_404(self.request.user, role.pk))


class RoleDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/roles/<id>/` - manage a single role."""

    @modify(
        summary="Get a role",
        description="Return a single role by id.",
        response_description="The requested role.",
        extra_responses=[ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND)],
        tags=["Roles"],
    )
    def get(self, parsed_path: Path[RolePath]) -> RoleOut:
        return _serialize_role(_get_role_or_404(self.request.user, parsed_path.role_id))

    @modify(
        summary="Update a role",
        description=(
            "Partially update a role. A change that would leave the company "
            "with nobody who can edit roles is rejected with a 409. Needs "
            "the `company.roles` permission."
        ),
        response_description="The updated role.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Roles"],
    )
    def patch(
        self,
        parsed_path: Path[RolePath],
        parsed_body: Body[RoleUpdateIn],
    ) -> RoleOut:
        role = _get_role_or_404(self.request.user, parsed_path.role_id)
        require_company_perm(self.request.user, role.company, P.COMPANY_ROLES)

        for field in ("name", "color", "permissions", "sees_all_projects"):
            if (
                field in parsed_body.model_fields_set
                and getattr(parsed_body, field) is None
            ):
                raise _bad_request(self, f"{field} cannot be null.", [field])

        update_fields = parsed_body.model_dump(exclude_unset=True)

        if "name" in update_fields and _name_taken(
            role.company, update_fields["name"], exclude_pk=role.pk
        ):
            raise _conflict(
                self, "A role with this name already exists in this company.", ["name"]
            )
        if "permissions" in update_fields and role_manager_would_vanish(
            role.company, edit=(role.pk, update_fields["permissions"])
        ):
            raise _conflict(
                self,
                "The company must keep at least one person who can edit roles.",
                ["permissions"],
            )

        for field, value in update_fields.items():
            setattr(role, field, value)
        if update_fields:
            role.updated_by = self.request.user
            role.save(update_fields=[*update_fields, "updated_by", "updated_at"])

        return _serialize_role(_get_role_or_404(self.request.user, role.pk))

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a role",
        description=(
            "Permanently delete a role. Rejected with a 409 while anyone "
            "still has it, in the company or in a project. Needs the "
            "`company.roles` permission."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Roles"],
    )
    def delete(self, parsed_path: Path[RolePath]) -> None:
        role = _get_role_or_404(self.request.user, parsed_path.role_id)
        require_company_perm(self.request.user, role.company, P.COMPANY_ROLES)
        try:
            role.delete()
        except RestrictedError as exc:
            raise APIError(
                {"detail": "Cannot delete this role while someone still has it."},
                status_code=HTTPStatus.CONFLICT,
            ) from exc
        return None
