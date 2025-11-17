from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser


class CustomUserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('storage_quota',)}),
    )
    list_display = ('email', 'username', 'is_staff', 'is_superuser', 'storage_quota')
    search_fields = ('email', 'username')


admin.site.register(CustomUser, CustomUserAdmin)

# Register your models here.
