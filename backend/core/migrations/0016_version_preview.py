# Generated by Django 5.1.5 on 2025-01-30 21:22

import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='version',
            name='preview',
            field=models.ImageField(blank=True, null=True, upload_to=core.models.version_upload_path),
        ),
    ]
