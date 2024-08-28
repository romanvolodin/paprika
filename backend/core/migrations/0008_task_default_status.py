# Generated by Django 5.0.8 on 2024-08-26 12:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_tmpshotpreview"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="default_status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tasks",
                to="core.status",
                verbose_name="статус по умолчанию",
            ),
        ),
    ]