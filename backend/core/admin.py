from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Project, Shot, ShotGroup, Version


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


@admin.register(Shot)
class ShotAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "group",
        "created_by",
        "created_at",
        "get_latest_version",
    )
    list_filter = (
        "group__project",
        "group",
    )
    inlines = (VersionInline,)

    @admin.display(description="Latest version")
    def get_latest_version(self, obj):
        latest_version = obj.versions.latest("created_at")
        if latest_version:
            return mark_safe(f'<a href="{latest_version.video.url}">{latest_version.name}</a>')


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    pass
