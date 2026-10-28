from django.contrib import admin

from .models import Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "sees_all_projects")
    list_filter = ("company",)
    search_fields = ("name",)
