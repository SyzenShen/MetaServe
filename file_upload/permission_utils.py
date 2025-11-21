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
        return user_in_same_organization(user, file.user)
    if access_level == 'restricted':
        return has_file_share_access(user, file)
    return False