from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout

from .models import Organization, Membership


@login_required
def org_list_page(request):
    orgs = Organization.objects.filter(memberships__user=request.user).distinct()
    # 为模板标注当前用户在每个组织的角色，便于控制显示“删除组织”按钮
    my_memberships = Membership.objects.filter(user=request.user, organization__in=orgs).values('organization_id', 'role')
    role_map = {m['organization_id']: m['role'] for m in my_memberships}
    for o in orgs:
        o.my_role = role_map.get(o.id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            org_id = request.POST.get('org_id')
            try:
                org = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                messages.error(request, 'Organization not found')
                return redirect('org_list_page')
            me = Membership.objects.filter(organization=org, user=request.user).first()
            # 允许组织所有者删除，即使成员记录缺失
            is_owner = (org.owner_id == request.user.id)
            if not (is_owner or (me and me.role == 'owner')):
                messages.error(request, 'Only owner can delete organization')
                return redirect('org_list_page')
            org.delete()
            messages.success(request, 'Organization deleted')
            return redirect('org_list_page')

    return render(request, 'authentication/org_list.html', {'orgs': orgs})


@login_required
def org_create_page(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if not name:
            messages.error(request, 'Organization name is required')
            return redirect('org_create_page')
        if Organization.objects.filter(name=name).exists():
            messages.error(request, 'Organization name already exists')
            return redirect('org_create_page')
        org = Organization.objects.create(name=name, owner=request.user)
        Membership.objects.create(organization=org, user=request.user, role='owner')
        messages.success(request, 'Organization created')
        return redirect('org_list_page')
    return render(request, 'authentication/org_create.html')


@login_required
def org_members_page(request, org_id):
    try:
        org = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        messages.error(request, 'Organization not found')
        return redirect('org_list_page')

    me = Membership.objects.filter(organization=org, user=request.user).first()
    if not me:
        messages.error(request, 'No permission to view this organization')
        return redirect('org_list_page')

    members = Membership.objects.filter(organization=org).select_related('user')
    User = get_user_model()
    all_users = User.objects.all().order_by('email')[:200]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            if me.role not in ('owner', 'admin'):
                messages.error(request, 'Only owner/admin can add members')
                return redirect('org_members_page', org_id=org.id)
            # 支持通过用户选择或邮箱邀请（邮箱不存在则创建用户）
            user_id = request.POST.get('user_id')
            email = (request.POST.get('email') or '').strip().lower()
            role = request.POST.get('role', 'member')

            target = None
            if email:
                try:
                    target = User.objects.get(email=email)
                except User.DoesNotExist:
                    # 创建一个新用户，使用临时密码，后续由用户自行重置
                    import secrets
                    temp_password = secrets.token_urlsafe(12)
                    target = User.objects.create_user(email=email, password=temp_password)
                    messages.info(request, f'New user created: {email}. Please notify to reset password')
            elif user_id:
                try:
                    target = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    messages.error(request, 'User not found')
                    return redirect('org_members_page', org_id=org.id)
            else:
                messages.error(request, 'Please select a user from list or provide email')
                return redirect('org_members_page', org_id=org.id)

            Membership.objects.update_or_create(organization=org, user=target, defaults={'role': role})
            messages.success(request, 'Member added')
            return redirect('org_members_page', org_id=org.id)
        elif action == 'update':
            if me.role not in ('owner', 'admin'):
                messages.error(request, 'Only owner/admin can update member role')
                return redirect('org_members_page', org_id=org.id)
            member_id = request.POST.get('member_id')
            role = request.POST.get('role')
            try:
                m = Membership.objects.get(id=member_id, organization=org)
            except Membership.DoesNotExist:
                messages.error(request, 'Member not found')
                return redirect('org_members_page', org_id=org.id)
            if role not in ('owner', 'admin', 'member', 'viewer'):
                messages.error(request, 'Invalid role')
                return redirect('org_members_page', org_id=org.id)
            m.role = role
            m.save(update_fields=['role'])
            messages.success(request, 'Member role updated')
            return redirect('org_members_page', org_id=org.id)
        elif action == 'remove':
            if me.role not in ('owner', 'admin'):
                messages.error(request, 'Only owner/admin can remove members')
                return redirect('org_members_page', org_id=org.id)
            member_id = request.POST.get('member_id')
            try:
                m = Membership.objects.get(id=member_id, organization=org)
            except Membership.DoesNotExist:
                messages.error(request, 'Member not found')
                return redirect('org_members_page', org_id=org.id)
            m.delete()
            messages.success(request, 'Member removed')
            return redirect('org_members_page', org_id=org.id)

    return render(request, 'authentication/org_members.html', {
        'org': org,
        'members': members,
        'me': me,
        'all_users': all_users,
    })


def login_page(request):
    """简单的会话登录页面（使用用户名或邮箱与密码）"""
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        # 支持用邮箱或用户名登录
        user = authenticate(request, username=username, password=password)
        if user is None:
            # 尝试邮箱登录：通过邮箱获取用户名再验证
            try:
                User = get_user_model()
                u = User.objects.get(email=username)
                user = authenticate(request, username=u.username, password=password)
            except Exception:
                user = None
        if user:
            login(request, user)
            return redirect('/file/')
        messages.error(request, 'Login failed, please check account or password')
    return render(request, 'authentication/login.html')


@login_required
def logout_page(request):
    logout(request)
    messages.success(request, 'Logged out')
    # 退出管理界面后，跳转到前端用户登录页而不是后端UI登录页
    return redirect('/login')