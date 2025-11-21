from rest_framework.permissions import BasePermission
from .models import File, Folder
from .permission_utils import can_view_or_download_file


class IsFileReadable(BasePermission):
    """对象级文件读取/下载权限"""
    message = '无权访问该文件'

    def has_permission(self, request, view):
        # 在对象获取前先允许进入，实际控制在 has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, File):
            return can_view_or_download_file(request.user, obj)
        # 某些视图先拿不到 obj，则在视图里手动判定
        return True


class IsFolderReadable(BasePermission):
    """对象级文件夹读取权限
    当前策略：仅允许访问自己拥有的文件夹；
    如需开放组织内浏览，可在后续版本扩展。
    """
    message = '无权访问该文件夹'

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Folder):
            return getattr(obj, 'user_id', None) == getattr(request.user, 'id', None)
        return True