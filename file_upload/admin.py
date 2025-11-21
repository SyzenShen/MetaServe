from django.contrib import admin
from .models import File, Folder, FileShare


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "original_filename", "user", "uploaded_at", "access_level", "file_size")
    search_fields = ("title", "original_filename", "user__username", "project", "uploader")
    list_filter = ("access_level", "document_type", "file_format", "uploaded_at")


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "parent", "created_at")
    search_fields = ("name", "user__username")
    list_filter = ("created_at",)


@admin.register(FileShare)
class FileShareAdmin(admin.ModelAdmin):
    list_display = ("id", "file", "shared_to_user", "shared_to_organization", "can_download", "can_edit_metadata", "expires_at", "created_at")
    search_fields = ("file__title", "file__original_filename", "shared_to_user__username", "shared_to_organization__name")
    list_filter = ("can_download", "can_edit_metadata", "expires_at", "created_at")
