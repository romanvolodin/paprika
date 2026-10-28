import django.db.models.deletion
from django.db import migrations, models

from apps.access.permissions import DEFAULT_ROLES


def give_companies_their_roles(apps, schema_editor):
    """Create the starter roles for existing companies and move the people to them."""
    Company = apps.get_model("companies", "Company")
    CompanyMembership = apps.get_model("companies", "CompanyMembership")
    Role = apps.get_model("access", "Role")

    for company in Company.objects.all():
        for key, template in DEFAULT_ROLES.items():
            role, _ = Role.objects.get_or_create(
                company=company,
                name=template.name,
                defaults={
                    "color": template.color,
                    "permissions": sorted(template.permissions),
                    "sees_all_projects": template.sees_all_projects,
                },
            )
            CompanyMembership.objects.filter(company=company, legacy_role=key).update(
                role=role
            )

    # Postgres refuses to alter a table that still has deferred foreign key
    # checks pending from the updates above; run them now.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0001_initial"),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="companymembership",
            old_name="role",
            new_name="legacy_role",
        ),
        migrations.AddField(
            model_name="companymembership",
            name="role",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="company_memberships",
                to="access.role",
                verbose_name="role",
            ),
        ),
        migrations.RunPython(give_companies_their_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="companymembership",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="company_memberships",
                to="access.role",
                verbose_name="role",
            ),
        ),
        migrations.RemoveField(
            model_name="companymembership",
            name="legacy_role",
        ),
    ]
