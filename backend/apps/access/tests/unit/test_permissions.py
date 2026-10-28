import pytest

from apps.access.models import Role
from apps.access.permissions import (
    ALL_CODES,
    COMPANY_CODES,
    DEFAULT_ROLES,
    PERMISSIONS,
    PROJECT_CODES,
)


pytestmark = pytest.mark.django_db


class TestRegistry:
    def test_codes_are_unique(self):
        codes = [p.code for p in PERMISSIONS]

        assert len(codes) == len(set(codes))

    def test_every_permission_is_a_company_or_a_project_one(self):
        assert COMPANY_CODES | PROJECT_CODES == ALL_CODES
        assert not COMPANY_CODES & PROJECT_CODES

    def test_the_starter_roles_use_only_known_permissions(self):
        for template in DEFAULT_ROLES.values():
            assert template.permissions <= ALL_CODES

    def test_the_admin_has_everything(self):
        assert DEFAULT_ROLES["admin"].permissions == ALL_CODES

    def test_the_producer_cannot_delete_the_company_or_edit_roles(self):
        producer = DEFAULT_ROLES["producer"].permissions

        assert "company.delete" not in producer
        assert "company.roles" not in producer
        assert "company.members" in producer

    def test_only_the_admin_and_the_producer_see_all_projects(self):
        wide = {key for key, t in DEFAULT_ROLES.items() if t.sees_all_projects}

        assert wide == {"admin", "producer"}

    @pytest.mark.parametrize("key", ["executor", "freelancer"])
    def test_executors_delete_only_their_own_versions(self, key):
        permissions = DEFAULT_ROLES[key].permissions

        assert "version.delete_own" in permissions
        assert "version.delete" not in permissions

    def test_the_client_can_only_write_in_the_chat(self):
        assert DEFAULT_ROLES["client"].permissions == {"chat.write"}


class TestSeeding:
    def test_a_new_company_gets_the_starter_roles(self, company):
        names = set(Role.objects.filter(company=company).values_list("name", flat=True))

        assert names == {t.name for t in DEFAULT_ROLES.values()}

    def test_the_starter_roles_carry_their_permissions(self, company):
        admin = Role.objects.get(company=company, name=DEFAULT_ROLES["admin"].name)

        assert set(admin.permissions) == ALL_CODES
        assert admin.sees_all_projects

    def test_roles_of_different_companies_are_separate(self, company_factory):
        first, second = company_factory(), company_factory()

        assert not set(first.roles.values_list("pk", flat=True)) & set(
            second.roles.values_list("pk", flat=True)
        )
