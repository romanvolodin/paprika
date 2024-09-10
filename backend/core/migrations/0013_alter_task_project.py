# Generated by Django 5.0.8 on 2024-09-10 11:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_shot_project_task_project"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tasks",
                to="core.project",
                verbose_name="проект",
            ),
        ),
    ]
