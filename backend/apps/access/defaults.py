from apps.companies.models import Company

from .models import Role
from .permissions import DEFAULT_ROLES


def create_default_roles(company: Company) -> dict[str, Role]:
    """Give a company its starter roles, keyed like `DEFAULT_ROLES`."""
    return {
        key: Role.objects.create(
            company=company,
            name=template.name,
            color=template.color,
            permissions=sorted(template.permissions),
            sees_all_projects=template.sees_all_projects,
            created_by=company.created_by,
            updated_by=company.created_by,
        )
        for key, template in DEFAULT_ROLES.items()
    }


def get_default_role(company: Company, key: str) -> Role:
    """The company's starter role with the given key (`admin`, `executor`...)."""
    return Role.objects.get(company=company, name=DEFAULT_ROLES[key].name)
