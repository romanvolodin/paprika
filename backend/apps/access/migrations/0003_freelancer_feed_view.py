from django.db import migrations


def give_freelancers_the_feed(apps, schema_editor):
    Role = apps.get_model("access", "Role")
    for role in Role.objects.filter(name="Фрилансер"):
        if "feed.view" not in role.permissions:
            role.permissions = [*role.permissions, "feed.view"]
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0002_role_sees_all_shots"),
    ]

    operations = [
        migrations.RunPython(give_freelancers_the_feed, migrations.RunPython.noop),
    ]
