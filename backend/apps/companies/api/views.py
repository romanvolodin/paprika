from http import HTTPStatus

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import Paginator
from dmr import APIError, Body, Path, Query, ResponseSpec, modify
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer

from apps.access.api.schemas import RoleRefOut
from apps.access.checks import (
    companies_q,
    company_permissions,
    company_permissions_by_id,
    require_can_grant_company_role,
    require_company_perm,
    role_manager_would_vanish,
)
from apps.access.defaults import get_default_role
from apps.access.models import Role
from apps.access.permissions import P
from apps.auth.api.controllers import AuthenticatedController
from apps.companies.models import Company, CompanyMembership
from apps.users.models import User

from .schemas import (
    CompanyCreateIn,
    CompanyListOut,
    CompanyListQuery,
    CompanyMemberCreateIn,
    CompanyMemberListOut,
    CompanyMemberOut,
    CompanyMemberPath,
    CompanyMemberUpdateIn,
    CompanyOut,
    CompanyPath,
    CompanyUpdateIn,
)


def _serialize_company(company: Company, permissions) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        name=company.name,
        slug=company.slug,
        my_permissions=sorted(permissions),
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def _serialize_member(request, membership: CompanyMembership) -> CompanyMemberOut:
    avatar_url = (
        request.build_absolute_uri(membership.user.avatar.url)
        if membership.user.avatar
        else None
    )
    return CompanyMemberOut(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        first_name=membership.user.first_name,
        last_name=membership.user.last_name,
        avatar=avatar_url,
        role=RoleRefOut(
            id=membership.role.id,
            name=membership.role.name,
            color=membership.role.color,
        ),
        created_at=membership.created_at,
    )


def _get_company_or_404(user: User, company_id: int) -> Company:
    """Look up a company, scoped to companies the user is a member of.

    A company the user doesn't belong to 404s exactly like one that
    doesn't exist at all - membership isn't leaked to non-members.
    """
    try:
        return Company.objects.filter(companies_q(user, "pk")).get(pk=company_id)
    except Company.DoesNotExist as exc:
        raise APIError(
            {"detail": f"Company with id={company_id} was not found."},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_membership_or_404(company: Company, user_id: int) -> CompanyMembership:
    try:
        return CompanyMembership.objects.select_related("user", "role").get(
            company=company, user_id=user_id
        )
    except CompanyMembership.DoesNotExist as exc:
        raise APIError(
            {"detail": (f"User with id={user_id} is not a member of this company.")},
            status_code=HTTPStatus.NOT_FOUND,
        ) from exc


def _get_role_or_400(controller, company: Company, role_id: int) -> Role:
    try:
        return Role.objects.get(pk=role_id, company=company)
    except Role.DoesNotExist as exc:
        raise APIError(
            controller.format_error(
                "This role does not belong to the company.",
                loc=["role_id"],
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        ) from exc


def _last_role_manager_error() -> APIError:
    return APIError(
        {"detail": "The company must keep at least one person who can edit roles."},
        status_code=HTTPStatus.CONFLICT,
    )


class CompanyListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/` - list and create companies.

    A user only ever sees companies they're a member of - there is no
    "browse all companies" view, by design (data isolation between
    tenants). Creating a company automatically makes the creator its
    admin (the starter role with every permission).
    """

    @modify(
        summary="List companies",
        description=(
            "Return a paginated list of companies the current user is a "
            "member of, optionally filtered by `search` against the name."
        ),
        response_description="A page of companies.",
        tags=["Companies"],
    )
    def get(self, parsed_query: Query[CompanyListQuery]) -> CompanyListOut:
        queryset = Company.objects.filter(companies_q(self.request.user, "pk"))

        if parsed_query.search:
            queryset = queryset.filter(name__icontains=parsed_query.search)

        paginator = Paginator(queryset, parsed_query.page_size)
        page = paginator.get_page(parsed_query.page)

        companies = list(page.object_list)
        permissions = company_permissions_by_id(
            self.request.user, [company.id for company in companies]
        )
        return CompanyListOut(
            items=[
                _serialize_company(company, permissions.get(company.id, ()))
                for company in companies
            ],
            total=paginator.count,
            page=parsed_query.page,
            page_size=parsed_query.page_size,
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Create a company",
        description=(
            "Create a new company. The creator is automatically added as "
            "its admin and the company gets the starter set of roles."
        ),
        response_description="The created company.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
        ],
        tags=["Companies"],
    )
    def post(self, parsed_body: Body[CompanyCreateIn]) -> CompanyOut:
        if parsed_body.slug and Company.objects.filter(slug=parsed_body.slug).exists():
            raise APIError(
                self.format_error(
                    "A company with this slug already exists.",
                    loc=["slug"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        company = Company.objects.create(
            name=parsed_body.name,
            slug=parsed_body.slug or "",
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        CompanyMembership.objects.create(
            user=self.request.user,
            company=company,
            role=get_default_role(company, "admin"),
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_company(
            company, company_permissions(self.request.user, company)
        )


class CompanyDetailController(AuthenticatedController[PydanticSerializer]):
    """`GET/PATCH/DELETE /api/v1/companies/<id>/` - manage a single company."""

    @modify(
        summary="Get a company",
        description="Return a single company by id.",
        response_description="The requested company.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Companies"],
    )
    def get(self, parsed_path: Path[CompanyPath]) -> CompanyOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        return _serialize_company(
            company, company_permissions(self.request.user, company)
        )

    @modify(
        summary="Update a company",
        description=(
            "Partially update a company. Only fields present are changed. "
            "Needs the `company.edit` permission."
        ),
        response_description="The updated company.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Companies"],
    )
    def patch(
        self,
        parsed_path: Path[CompanyPath],
        parsed_body: Body[CompanyUpdateIn],
    ) -> CompanyOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_EDIT)

        update_fields = parsed_body.model_dump(exclude_unset=True)
        if "slug" in update_fields and (new_slug := update_fields["slug"]):
            if Company.objects.exclude(pk=company.pk).filter(slug=new_slug).exists():
                raise APIError(
                    self.format_error(
                        "A company with this slug already exists.",
                        loc=["slug"],
                        error_type=ErrorType.value_error,
                    ),
                    status_code=HTTPStatus.BAD_REQUEST,
                )

        for field, value in update_fields.items():
            setattr(company, field, value)
        if update_fields:
            company.updated_by = self.request.user
            company.save(update_fields=[*update_fields, "updated_by"])

        return _serialize_company(
            company, company_permissions(self.request.user, company)
        )

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Delete a company",
        description=(
            "Permanently delete a company with everything in it. Needs the "
            "`company.delete` permission."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Companies"],
    )
    def delete(self, parsed_path: Path[CompanyPath]) -> None:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_DELETE)
        company.delete()
        return None


class CompanyMemberListController(AuthenticatedController[PydanticSerializer]):
    """`GET/POST /api/v1/companies/<id>/members/` - list and add members."""

    @modify(
        summary="List company members",
        description="Return every member of the company.",
        response_description="The company's members.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
        ],
        tags=["Companies"],
    )
    def get(self, parsed_path: Path[CompanyPath]) -> CompanyMemberListOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        memberships = company.memberships.select_related("user", "role").order_by(
            "user__email"
        )
        return CompanyMemberListOut(
            items=[
                _serialize_member(self.request, membership)
                for membership in memberships
            ]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        summary="Add a company member",
        description=(
            "Add a person to the company with the given role. If nobody has "
            "this email yet, an account is created with the temporary "
            "password (the person has to change it at the first sign-in). "
            "If the account exists, it is added as is and the name and "
            "password sent are ignored, so the answer looks the same either "
            "way. Needs the `company.members` permission."
        ),
        response_description="The created membership.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Companies"],
    )
    def post(
        self,
        parsed_path: Path[CompanyPath],
        parsed_body: Body[CompanyMemberCreateIn],
    ) -> CompanyMemberOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_MEMBERS)
        role = _get_role_or_400(self, company, parsed_body.role_id)
        require_can_grant_company_role(self.request.user, company, role)
        email = User.objects.normalize_email(parsed_body.email)

        target_user = User.objects.filter(email__iexact=email).first()
        if target_user is None:
            try:
                validate_password(parsed_body.password)
            except DjangoValidationError as exc:
                raise APIError(
                    self.format_error(
                        " ".join(exc.messages),
                        loc=["password"],
                        error_type=ErrorType.value_error,
                    ),
                    status_code=HTTPStatus.BAD_REQUEST,
                ) from exc
            target_user = User.objects.create_user(
                email=email,
                password=parsed_body.password,
                first_name=parsed_body.first_name,
                last_name=parsed_body.last_name,
                must_change_password=True,
            )
        elif CompanyMembership.objects.filter(
            company=company, user=target_user
        ).exists():
            raise APIError(
                self.format_error(
                    "This person is already a member of the company.",
                    loc=["email"],
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )

        membership = CompanyMembership.objects.create(
            user=target_user,
            company=company,
            role=role,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        return _serialize_member(self.request, membership)


class CompanyMemberDetailController(AuthenticatedController[PydanticSerializer]):
    """`PATCH/DELETE /api/v1/companies/<id>/members/<user_id>/` - manage a member."""

    @modify(
        summary="Update a company member's role",
        description=(
            "Change the role of an existing company member. Needs the "
            "`company.members` permission."
        ),
        response_description="The updated membership.",
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.BAD_REQUEST),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Companies"],
    )
    def patch(
        self,
        parsed_path: Path[CompanyMemberPath],
        parsed_body: Body[CompanyMemberUpdateIn],
    ) -> CompanyMemberOut:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_MEMBERS)
        membership = _get_membership_or_404(company, parsed_path.user_id)
        role = _get_role_or_400(self, company, parsed_body.role_id)
        require_can_grant_company_role(self.request.user, company, membership.role)
        require_can_grant_company_role(self.request.user, company, role)

        if role_manager_would_vanish(company, move=(membership.user_id, role)):
            raise _last_role_manager_error()

        membership.role = role
        membership.updated_by = self.request.user
        membership.save(update_fields=["role", "updated_by"])

        return _serialize_member(self.request, membership)

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        summary="Remove a company member",
        description=(
            "Remove a member from the company, and from all of its projects. "
            "Needs the `company.members` permission."
        ),
        extra_responses=[
            ResponseSpec(dict, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(dict, status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict, status_code=HTTPStatus.FORBIDDEN),
        ],
        tags=["Companies"],
    )
    def delete(self, parsed_path: Path[CompanyMemberPath]) -> None:
        company = _get_company_or_404(self.request.user, parsed_path.company_id)
        require_company_perm(self.request.user, company, P.COMPANY_MEMBERS)
        membership = _get_membership_or_404(company, parsed_path.user_id)
        require_can_grant_company_role(self.request.user, company, membership.role)
        if role_manager_would_vanish(company, remove_user_id=membership.user_id):
            raise _last_role_manager_error()
        membership.delete()
        return None
