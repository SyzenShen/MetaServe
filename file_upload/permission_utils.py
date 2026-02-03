from typing import Optional
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import File, FileShare

User = get_user_model()


def user_in_same_organization(user: User, owner: User) -> bool:
    """
    判断两个用户是否存在共同组织。
    依赖 authentication.Membership 进行交叉判断。
    """
    try:
        from authentication.models import Membership
    except Exception:
        return False

    user_org_ids = set(Membership.objects.filter(user=user).values_list('organization_id', flat=True))
    owner_org_ids = set(Membership.objects.filter(user=owner).values_list('organization_id', flat=True))
    return len(user_org_ids & owner_org_ids) > 0


def has_file_share_access(user: User, file: File) -> bool:
    """检查用户是否通过 FileShare 获得访问权限"""
    qs = FileShare.objects.filter(file=file)
    if not qs.exists():
        return False

    active_shares = [s for s in qs if s.is_active()]
    if not active_shares:
        return False

    # 直接共享给用户
    if any(s.shared_to_user_id == user.id and s.can_download for s in active_shares):
        return True

    # 共享给组织
    try:
        from authentication.models import Membership
    except Exception:
        return False

    user_org_ids = set(Membership.objects.filter(user=user).values_list('organization_id', flat=True))
    for s in active_shares:
        if s.shared_to_organization_id and s.can_download and s.shared_to_organization_id in user_org_ids:
            return True
    return False


def can_edit_file_metadata(user: User, file: File) -> bool:
    """检查用户是否具有编辑文件元数据的权限（Owner/Superuser/Shared with Edit）"""
    if getattr(user, 'is_superuser', False):
        return True
    if file.user_id == user.id:
        return True
    
    # 检查共享权限
    qs = FileShare.objects.filter(file=file)
    if not qs.exists():
        return False
        
    active_shares = [s for s in qs if s.is_active()]
    if not active_shares:
        return False

    # 直接共享给用户
    if any(s.shared_to_user_id == user.id and s.can_edit_metadata for s in active_shares):
        return True

    # 共享给组织
    try:
        from authentication.models import Membership
        user_org_ids = set(Membership.objects.filter(user=user).values_list('organization_id', flat=True))
        for s in active_shares:
            if s.shared_to_organization_id and s.can_edit_metadata and s.shared_to_organization_id in user_org_ids:
                return True
    except Exception:
        pass
        
    return False


def can_view_or_download_file(user: User, file: File) -> bool:
    """统一的文件访问判定"""
    if user.is_superuser:
        return True
    if file.user_id == user.id:
        return True

    access_level = (file.access_level or '').lower()
    if access_level == 'public':
        # 已登录用户允许；如需完全公开可扩展匿名
        return True
    if access_level == 'internal':
        # 若位于公开文件夹：允许（随父级公开）
        try:
            if file.parent_folder and getattr(file.parent_folder, 'is_public', False):
                return True
        except Exception:
            pass
        return user_in_same_organization(user, file.user)
    if access_level == 'restricted':
        return has_file_share_access(user, file)
    return False


def can_view_folder(user: User, folder) -> bool:
    """文件夹可见性判定。
    规则：
    - 超级用户可见
    - 文件夹创建者可见
    - 若文件夹设置为公开：所有已登录用户可见
    - 若文件夹关联到某组织：成员均可见；仅允许 owner/admin 创建关联组织的文件夹
    - 否则：仅本人
    """
    try:
        if getattr(user, 'is_superuser', False):
            return True
        if getattr(folder, 'user_id', None) == user.id:
            return True
        # 公开文件夹
        if getattr(folder, 'is_public', False):
            return True
        org = getattr(folder, 'organization', None)
        if org is None:
            return False
        from authentication.models import Membership
        return Membership.objects.filter(organization_id=org.id, user=user).exists()
    except Exception:
        return False


def can_delete_file(user: User, file: File) -> bool:
    """删除权限判定。

    规则：
    - 超级用户可删
    - 文件上传者可删
    - 若文件通过 FileShare 共享到某组织，且用户在该组织为 owner/admin，则可删
    """
    if getattr(user, 'is_superuser', False):
        return True
    if file.user_id == user.id:
        return True

    # 检查是否共享到组织，且用户在该组织为 owner/admin
    try:
        # 仅考虑有效共享记录
        shares = FileShare.objects.filter(file=file, shared_to_organization__isnull=False)
        if shares.exists():
            from authentication.models import Membership
            privileged_org_ids = set(
                Membership.objects.filter(user=user, role__in=['owner', 'admin']).values_list('organization_id', flat=True)
            )
            shared_org_ids = set(shares.values_list('shared_to_organization_id', flat=True))
            if privileged_org_ids & shared_org_ids:
                return True
    except Exception:
        # 任意错误时不授予权限
        pass

    return False
