from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Project, Shot, ShotGroup, ShotTask, Status, Task, Version


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at",)


@admin.register(ShotGroup)
class ShotGroupAdmin(admin.ModelAdmin):
    pass


class VersionInline(admin.TabularInline):
    model = Version
    show_change_link = True
    extra = 0


class ShotTaskInline(admin.TabularInline):
    model = ShotTask
    show_change_link = True
    extra = 0


@admin.register(Shot)
class ShotAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "created_at",
        "get_shot_status",
        "get_latest_version",
    )
    list_filter = (
        "group__project",
        "group",
    )
    inlines = (
        ShotTaskInline,
        VersionInline,
    )
    readonly_fields = ("created_at",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name", "group"),
                    ("rec_timecode", "scene"),
                )
            },
        ),
        (
            "Информация об исходнике",
            {
                "fields": (
                    (
                        "source_name",
                        "source_start_timecode",
                        "source_end_timecode",
                    ),
                )
            },
        ),
        (
            "Дополнительная информация",
            {
                "fields": (
                    (
                        "pixel_aspect",
                        "retime_speed",
                        "created_by",
                        "created_at",
                    ),
                )
            },
        ),
    )

    @admin.display(description="Latest version")
    def get_latest_version(self, obj):
        latest_version = obj.versions.latest("created_at")
        if latest_version:
            return mark_safe(f'<a href="{latest_version.video.url}">{latest_version.name}</a>')

    @admin.display(description="Shot status")
    def get_shot_status(self, obj):
        statuses = [task.status.title for task in obj.task_statuses.all()]
        template = "<span style='background-color:{};color:#fff;padding:3px 7px'>{}</span>"

        if set() == set(statuses):
            return mark_safe(template.format("#ccc", "Нет задач"))

        if set(("Не начата",)) == set(statuses):
            return mark_safe(template.format("#900", "Не начат"))

        if set(("Отмена",)) == set(statuses):
            return mark_safe(template.format("#999", "Отмена"))

        if set(("Принята",)) == set(statuses) or set(("Отмена", "Принята")) == set(statuses):
            return mark_safe(template.format("#090", "Принят"))

        return mark_safe(template.format("#fa0", "В работе"))


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    pass


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    pass


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    pass


@admin.register(ShotTask)
class ShotTaskAdmin(admin.ModelAdmin):
    pass
