import django.db.models.deletion
from django.db import migrations, models

from apps.access.permissions import DEFAULT_ROLES


def move_project_members_to_roles(apps, schema_editor):
    """Point every project membership at the company's matching starter role."""
    Company = apps.get_model("companies", "Company")
    ProjectMembership = apps.get_model("projects", "ProjectMembership")
    Role = apps.get_model("access", "Role")

    for company in Company.objects.all():
        for key, template in DEFAULT_ROLES.items():
            role = Role.objects.get(company=company, name=template.name)
            ProjectMembership.objects.filter(
                project__company=company, legacy_role=key
            ).update(role=role)

    # Postgres refuses to alter a table that still has deferred foreign key
    # checks pending from the updates above; run them now.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0001_initial"),
        ("companies", "0002_membership_role_foreign_key"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="projectmembership",
            old_name="role",
            new_name="legacy_role",
        ),
        migrations.AddField(
            model_name="projectmembership",
            name="role",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="project_memberships",
                to="access.role",
                verbose_name="role",
            ),
        ),
        migrations.RunPython(move_project_members_to_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="projectmembership",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="project_memberships",
                to="access.role",
                verbose_name="role",
            ),
        ),
        migrations.RemoveField(
            model_name="projectmembership",
            name="legacy_role",
        ),
    ]
