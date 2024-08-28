from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.safestring import mark_safe

from .forms import AddShotsToGroupsForm
from .models import Project, Shot, ShotGroup, ShotTask, Status, Task, TmpShotPreview, Version


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
        "get_tmp_preview",
        "name",
        "get_shot_status",
        "pixel_aspect",
        "get_shot_tasks",
        "get_latest_version",
        "get_shot_groups",
    )
    list_filter = (
        "group__project",
        "group",
        "pixel_aspect",
    )
    inlines = (
        ShotTaskInline,
        VersionInline,
    )
    ordering = ("name",)
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

    @admin.display(description="группы")
    def get_shot_groups(self, obj):
        return mark_safe("<br>".join([group.name for group in obj.group.all()]))

    @admin.display(description="задачи")
    def get_shot_tasks(self, obj):
        return mark_safe("<br>".join([task.description for task in obj.task.all()]))

    @admin.display(description="превью")
    def get_tmp_preview(self, shot):
        try:
            preview = shot.tmp_preview.image.url
        except ObjectDoesNotExist:
            return mark_safe(
                "<div style='"
                "aspect-ratio:2.39/1;"
                "width:150px;"
                "background-color:#eee;"
                "display:flex;"
                "align-items:center;"
                "justify-content:center;"
                "' "
                ">Нет превью</div>"
            )

        return mark_safe(
            f"<img src='{preview}' style='aspect-ratio:2.39/1; width:150px; object-fit:cover'>"
        )

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

    actions = ["add_shots_to_groups"]

    @admin.action(description="Добавить шоты в группы")
    def add_shots_to_groups(modeladmin, request, queryset):
        if "apply" in request.POST:
            form = AddShotsToGroupsForm(request.POST)
            if form.is_valid():
                groups = form.cleaned_data["groups"]
                for shot in queryset:
                    shot.group.set(shot.group.all().union(groups))
                    shot.save()

            return HttpResponseRedirect(request.get_full_path())

        context = {
            "shots": queryset,
            "form": AddShotsToGroupsForm,
        }
        return render(request, "admin/add_shots_to_groups.html", context=context)


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    pass


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "default_status",
    )


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    pass


@admin.register(ShotTask)
class ShotTaskAdmin(admin.ModelAdmin):
    pass


@admin.register(TmpShotPreview)
class TmpShotPreview(admin.ModelAdmin):
    pass
