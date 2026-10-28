from django.db import IntegrityError
from django.db.models import RestrictedError
import pytest

from apps.companies.models import CompanyMembership


pytestmark = pytest.mark.django_db


class TestCompanyMembershipModel:
    def test_str_contains_user_company_and_role(
        self, company_membership_factory, user_factory, company_factory
    ):
        user = user_factory(email="someone@example.com")
        company = company_factory(name="Acme Studio")
        membership = company_membership_factory(
            user=user, company=company, role="admin"
        )

        text = str(membership)

        assert "someone@example.com" in text
        assert "Acme Studio" in text
        assert "Админ" in text

    def test_repr_contains_id_user_id_company_id_and_role(
        self, company_membership_factory
    ):
        membership = company_membership_factory()

        text = repr(membership)

        assert f"id={membership.id}" in text
        assert f"user_id={membership.user_id}" in text
        assert f"company_id={membership.company_id}" in text
        assert f"role_id={membership.role_id}" in text

    def test_role_is_a_role_of_the_same_company(self, company_membership_factory):
        membership = company_membership_factory(role="executor")

        assert membership.role.company_id == membership.company_id
        assert membership.role.name == "Исполнитель"

    def test_a_role_that_is_in_use_cannot_be_deleted(self, company_membership_factory):
        membership = company_membership_factory()

        with pytest.raises(RestrictedError):
            membership.role.delete()

    def test_user_and_company_pair_must_be_unique(
        self, company_membership_factory, user_factory, company_factory
    ):
        user = user_factory()
        company = company_factory()
        company_membership_factory(user=user, company=company)

        with pytest.raises(IntegrityError):
            company_membership_factory(user=user, company=company)

    def test_same_user_can_belong_to_multiple_companies(
        self, company_membership_factory, user_factory, company_factory
    ):
        user = user_factory()
        first_company = company_factory()
        second_company = company_factory()

        company_membership_factory(user=user, company=first_company)
        company_membership_factory(user=user, company=second_company)

        assert user.company_memberships.count() == 2

    def test_company_can_have_multiple_members(
        self, company_membership_factory, company_factory, user_factory
    ):
        company = company_factory()
        first_user = user_factory()
        second_user = user_factory()

        company_membership_factory(user=first_user, company=company)
        company_membership_factory(user=second_user, company=company)

        assert company.memberships.count() == 2

    def test_membership_is_deleted_when_company_is_deleted(
        self, company_membership_factory
    ):
        membership = company_membership_factory()
        membership_id = membership.id
        company = membership.company

        company.delete()

        assert not CompanyMembership.objects.filter(id=membership_id).exists()

    def test_membership_is_deleted_when_user_is_deleted(
        self, company_membership_factory
    ):
        membership = company_membership_factory()
        membership_id = membership.id
        user = membership.user

        user.delete()

        assert not CompanyMembership.objects.filter(id=membership_id).exists()
