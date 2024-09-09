from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.safestring import mark_safe

from .forms import AddShotsToGroupsForm
from .models import Project, Shot, ShotGroup, ShotTask, Status, Task, TmpShotPreview, Version


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    save_on_top = True
    readonly_fields = (
        "created_by",
        "created_at",
    )

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ShotGroup)
class ShotGroupAdmin(admin.ModelAdmin):
    save_on_top = True
    ordering = ("-name",)
    readonly_fields = (
        "created_by",
        "created_at",
    )

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


class VersionInline(admin.TabularInline):
    model = Version
    show_change_link = True
    extra = 0


class ShotTaskInline(admin.TabularInline):
    model = ShotTask
    show_change_link = True
    extra = 0


class ShotStatusListFilter(admin.SimpleListFilter):
    title = "shot status"
    parameter_name = "shot_status"

    def lookups(self, request, model_admin):
        return [
            ("no_tasks", "Нет задач"),
            ("canceled", "Отмена"),
            ("not_started", "Не начат"),
            ("in_progress", "В работе"),
            ("done", "Готов"),
            ("commented", "Есть комментарий"),
            ("approved", "Принят"),
            ("delivered", "Отдан"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "no_tasks":
            return queryset.filter(task_statuses=None)

        if self.value() == "canceled":
            return queryset.filter(task_statuses__status__title="Отмена")

        if self.value() == "not_started":
            return queryset.filter(task_statuses__status__title="Не начата")

        if self.value() == "in_progress":
            return queryset.filter(task_statuses__status__title="В работе")

        if self.value() == "done":
            return queryset.filter(task_statuses__status__title="Готова")

        if self.value() == "commented":
            return queryset.filter(task_statuses__status__title="Есть комментарий")

        if self.value() == "approved":
            return queryset.filter(task_statuses__status__title="Принята")

        if self.value() == "delivered":
            return queryset.filter(task_statuses__status__title="Отдано")


@admin.register(Shot)
class ShotAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = (
        "get_tmp_preview",
        "name",
        "get_rec_timecode",
        "get_shot_status",
        "get_shot_tasks",
        "comment",
        # "get_latest_version",
        "get_shot_groups",
    )
    list_filter = (
        "group__project",
        ShotStatusListFilter,
        "task",
        "group",
        "pixel_aspect",
    )
    inlines = (
        ShotTaskInline,
        VersionInline,
    )
    ordering = ("rec_timecode",)
    readonly_fields = (
        "created_by",
        "created_at",
    )

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
                    ("comment",),
                )
            },
        ),
    )

    @admin.display(description="TC")
    def get_rec_timecode(self, obj):
        return obj.rec_timecode

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
                "aspect-ratio:2.39/0.2;"
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
            return mark_safe(template.format("#099", "Принят"))

        if set(("Готова",)) == set(statuses) or set(("Отмена", "Готова")) == set(statuses):
            return mark_safe(template.format("#090", "Готов"))

        if set(("Отдано",)) == set(statuses) or set(("Отмена", "Отдано")) == set(statuses):
            return mark_safe(template.format("#7700BE", "Отдан"))

        if "Есть комментарий" in statuses:
            return mark_safe(template.format("#FF6600", "Есть комментарий"))

        return mark_safe(template.format("#fa0", "В работе"))

    actions = ["add_shots_to_groups", "download_shots_as_xlsx"]

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

    @admin.action(description="Скачать шоты в виде Excel таблицы")
    def download_shots_as_xlsx(modeladmin, request, queryset):
        from datetime import datetime

        from openpyxl import Workbook
        from openpyxl.styles import Alignment
        from openpyxl.utils import get_column_letter

        project_code = queryset[0].group.first().project.code
        date = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{project_code}_shots_{date}.xlsx"

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"

        wb = Workbook()
        ws = wb.active
        ws.append(("№", "Название шота", "Задачи"))
        for counter, shot in enumerate(queryset, start=1):
            counter_cell = ws.cell(row=counter + 1, column=1, value=counter)
            counter_cell.alignment = Alignment(vertical="top", horizontal="left")

            name_cell = ws.cell(row=counter + 1, column=2, value=shot.name)
            name_cell.alignment = Alignment(vertical="top", horizontal="left")

            ws.cell(
                row=counter + 1,
                column=3,
                value="\n".join([task.description for task in shot.task.all()]),
            )

        for i, column in enumerate(ws.columns, 1):
            lengths = (
                len(max(str(cell.value).split("\n"))) for cell in column if cell.value is not None
            )
            ws.column_dimensions[get_column_letter(i)].width = max(lengths) + 2

        wb.save(response)
        return response

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    save_on_top = True
    readonly_fields = (
        "created_by",
        "created_at",
    )

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = (
        "description",
        "default_status",
    )
    readonly_fields = (
        "created_by",
        "created_at",
    )
    ordering = ("description",)
    inlines = (ShotTaskInline,)

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = (
        "title",
        "get_color",
    )
    readonly_fields = (
        "created_by",
        "created_at",
    )

    @admin.display(description="цвет")
    def get_color(self, obj):
        return mark_safe(f"<div style='background-color:{obj.color};color:#fff'>{obj.color}</div>")

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ShotTask)
class ShotTaskAdmin(admin.ModelAdmin):
    save_on_top = True


@admin.register(TmpShotPreview)
class TmpShotPreview(admin.ModelAdmin):
    save_on_top = True
