from django.db import migrations, models


def hide_shots_from_freelancers(apps, schema_editor):
    Role = apps.get_model("access", "Role")
    Role.objects.filter(name="Фрилансер").update(sees_all_shots=False)


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0001_initial"),
        ("companies", "0002_membership_role_foreign_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="sees_all_shots",
            field=models.BooleanField(
                default=True,
                help_text="Whether a member with this role sees every shot of the project, not only the ones with a task assigned to them.",
                verbose_name="sees all shots",
            ),
        ),
        migrations.RunPython(hide_shots_from_freelancers, migrations.RunPython.noop),
    ]
