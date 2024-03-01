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
    task = models.ManyToManyField(
        "Task",
        through="ShotTask",
        related_name="shots",
        verbose_name="задача на шот",
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


class Task(models.Model):
    created_at = models.DateTimeField(
        "когда создана",
        auto_now_add=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
        verbose_name="кем создана",
    )
    description = models.TextField("описание")

    def __str__(self):
        return self.description


class Status(models.Model):
    created_at = models.DateTimeField(
        "когда создан",
        auto_now_add=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_statuses",
        verbose_name="кем создан",
    )
    title = models.CharField(
        "Статус задачи",
        max_length=50,
    )

    def __str__(self):
        return self.title


class ShotTask(models.Model):
    shot = models.ForeignKey(
        Shot,
        on_delete=models.CASCADE,
        related_name="task_statuses",
        verbose_name="шот",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="used_in_shots",
        verbose_name="задача",
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name="shot_tasks",
        verbose_name="статус",
    )

    def __str__(self):
        return f"{self.shot}: {self.task} ({self.status})"
