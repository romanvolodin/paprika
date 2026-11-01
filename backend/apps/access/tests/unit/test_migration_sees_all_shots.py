from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("access", "0001_initial")]
AFTER = [("access", "0002_role_sees_all_shots")]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


def test_existing_freelancers_lose_the_view_of_all_shots():
    apps = _migrate(BEFORE)
    Company = apps.get_model("companies", "Company")
    Role = apps.get_model("access", "Role")
    company = Company.objects.create(name="Студия", slug="studio")
    Role.objects.create(company=company, name="Фрилансер", color="#12B5CB")
    Role.objects.create(company=company, name="Исполнитель", color="#E971B8")

    apps = _migrate(AFTER)
    Role = apps.get_model("access", "Role")

    assert not Role.objects.get(name="Фрилансер").sees_all_shots
    assert Role.objects.get(name="Исполнитель").sees_all_shots

    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def test_existing_freelancers_get_the_feed_once():
    apps = _migrate([("access", "0002_role_sees_all_shots")])
    Company = apps.get_model("companies", "Company")
    Role = apps.get_model("access", "Role")
    first = Company.objects.create(name="Студия", slug="studio")
    second = Company.objects.create(name="Другая", slug="other")
    Role.objects.create(
        company=first, name="Фрилансер", color="#12B5CB", permissions=["chat.write"]
    )
    Role.objects.create(
        company=first, name="Свой", color="#E971B8", permissions=["chat.write"]
    )
    Role.objects.create(
        company=second,
        name="Фрилансер",
        color="#12B5CB",
        permissions=["chat.write", "feed.view"],
    )

    apps = _migrate([("access", "0003_freelancer_feed_view")])
    Role = apps.get_model("access", "Role")

    assert Role.objects.get(company_id=first.id, name="Фрилансер").permissions == [
        "chat.write",
        "feed.view",
    ]
    assert Role.objects.get(company_id=second.id, name="Фрилансер").permissions == [
        "chat.write",
        "feed.view",
    ]
    assert Role.objects.get(name="Свой").permissions == ["chat.write"]

    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
