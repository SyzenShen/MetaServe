from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Organization, Membership


class CustomUserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('storage_quota',)}),
    )
    list_display = ('email', 'username', 'is_staff', 'is_superuser', 'storage_quota')
    search_fields = ('email', 'username')


admin.site.register(CustomUser, CustomUserAdmin)

# Register your models here.


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at")
    search_fields = ("name", "owner__username", "owner__email")
    list_filter = ("created_at",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "user", "role", "joined_at")
    search_fields = ("organization__name", "user__username", "user__email")
    list_filter = ("role", "joined_at")
