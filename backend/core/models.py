from colorfield.fields import ColorField
from django.conf import settings
from django.db import models


def version_upload_path(version, filename):
    shot = version.shot
    project = shot.project.code
    return f"{project}/{shot}/{filename}"


def shot_preview_upload_path(preview, filename):
    shot = preview.shot
    project = shot.group.all()[0].project.code
    return f"{project}/{shot}/preview/{filename}"


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
        blank=True,
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
        blank=True,
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
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="shots",
        verbose_name="проект",
        null=True,
        blank=True,
    )
    group = models.ManyToManyField(
        ShotGroup,
        related_name="shots",
        verbose_name="группа, которой принадлежит шот",
    )
    rec_timecode = models.CharField(
        "Начальный таймкод в монтаже",
        max_length=11,
        blank=True,
        help_text="Задается в виде 00:00:00:00",
    )
    source_name = models.CharField(
        "имя исходника",
        max_length=50,
        blank=True,
    )
    source_start_timecode = models.CharField(
        "Начальный таймкод по исходнику",
        max_length=11,
        blank=True,
        help_text="Задается в виде 00:00:00:00",
    )
    source_end_timecode = models.CharField(
        "Конечный таймкод по исходнику",
        max_length=11,
        blank=True,
        help_text="Задается в виде 00:00:00:00",
    )
    pixel_aspect = models.FloatField(
        "Аспект пикселя",
        default=1.0,
    )
    retime_speed = models.FloatField(
        "скорость ретайма",
        default=100,
        help_text=(
            "100% - скорость без изменений, 200% - в 2 раза быстрее, 50% - в 2 раза медленнее"
        ),
    )
    scene = models.CharField(
        "Номер сцены",
        max_length=15,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_shots",
        verbose_name="кем создан",
        blank=True,
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
    comment = models.TextField(
        verbose_name="Комментарий",
        null=True,
        blank=True,
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
    preview = models.ImageField(upload_to=version_upload_path, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_versions",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = "created_at"

    def __str__(self):
        return self.name


class Task(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="tasks",
        verbose_name="проект",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        "когда создана",
        auto_now_add=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
        verbose_name="кем создана",
        blank=True,
    )
    description = models.TextField("описание")
    default_status = models.ForeignKey(
        "Status",
        on_delete=models.PROTECT,
        related_name="tasks",
        verbose_name="статус по умолчанию",
        null=True,
        blank=True,
        help_text=(
            "Будет установлен при добавлении задачи в шот. "
            "Prepopulated_fields здесь не работает, нужна самописная вьюха"
        ),
    )

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
        blank=True,
    )
    title = models.CharField(
        "Статус задачи",
        max_length=50,
    )
    color = ColorField(
        "цвет метки",
        default="#ffffff",
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


class TmpShotPreview(models.Model):
    shot = models.OneToOneField(
        Shot,
        on_delete=models.PROTECT,
        related_name="tmp_preview",
    )
    image = models.FileField(upload_to=shot_preview_upload_path)

    def __str__(self):
        return self.shot.name


class ChatMessage(models.Model):
    shot = models.ForeignKey(
        Shot,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name="шот",
    )
    created_at = models.DateTimeField(
        "когда создано",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chat_messages",
        verbose_name="кем создано",
        blank=True,
    )
    reply_to = models.ForeignKey(
        "ChatMessage",
        on_delete=models.CASCADE,
        related_name="replies",
        verbose_name="ответ на сообщение",
        blank=True,
        null=True,
    )
    text = models.TextField()

    def __str__(self):
        return f"{self.shot}:{self.created_by.first_name}:{self.text[:15]}"
