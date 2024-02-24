from django.conf import settings
from django.db import models


def version_upload_path(version, filename):
    shot = version.shot
    project = shot.group.project.code
    return f"{project}/{shot}/{filename}"


class Project(models.Model):
    name = models.CharField(
        "название",
        max_length=150,
    )
    code = models.CharField(
        "код проекта",
        max_length=5,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="projects",
        verbose_name="кем создан",
    )
    created_at = models.DateTimeField(
        "когда создан",
        auto_now_add=True,
    )

    def __str__(self):
        return self.name


class ShotGroup(models.Model):
    name = models.CharField(
        "название группы шотов",
        max_length=50,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="shot_groups",
        verbose_name="проект",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shot_groups",
        verbose_name="кем создан",
    )
    created_at = models.DateTimeField(
        "когда создан",
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.project.code}:{self.name}"


class Shot(models.Model):
    name = models.CharField(
        "Название шота",
        max_length=50,
    )
    group = models.ForeignKey(
        ShotGroup,
        on_delete=models.CASCADE,
        related_name="shots",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_shots",
        verbose_name="кем создан",
    )
    created_at = models.DateTimeField(
        "когда создан",
        auto_now_add=True,
    )

    def __str__(self):
        return self.name


class Version(models.Model):
    name = models.CharField(
        "Название версии",
        max_length=50,
    )
    shot = models.ForeignKey(
        Shot,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    video = models.FileField(upload_to=version_upload_path)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
