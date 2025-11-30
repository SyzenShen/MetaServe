from .models import Membership, Organization


def management_visibility(request):
    """Provide `can_manage_orgs` to templates.

    Visible when the authenticated user is an `owner` of any organization.
    """
    user = getattr(request, 'user', None)
    can_manage = False
    if user and user.is_authenticated:
        try:
            # 兼容历史数据：既检查成员表中的 owner，也检查组织 owner 外键
            is_owner_member = Membership.objects.filter(user=user, role__iexact='owner').exists()
            is_org_owner = Organization.objects.filter(owner=user).exists()
            can_manage = bool(is_owner_member or is_org_owner)
        except Exception:
            can_manage = False
    return {
        'can_manage_orgs': can_manage,
    }