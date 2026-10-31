from django.contrib import admin

from .models import Invitation, InvitationProject


class InvitationProjectInline(admin.TabularInline):
    model = InvitationProject
    extra = 0


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "company", "role", "expires_at", "accepted_at")
    list_filter = ("company",)
    search_fields = ("email",)
    inlines = [InvitationProjectInline]
