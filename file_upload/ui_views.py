from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import File, FileShare


@login_required
def share_list_page(request):
    """显示当前用户拥有文件的共享记录，并提供删除入口"""
    # 仅显示我拥有文件的共享
    shares = FileShare.objects.filter(file__user=request.user).select_related('file', 'shared_to_user', 'shared_to_organization')
    if request.method == 'POST':
        # 撤销共享
        share_id = request.POST.get('share_id')
        try:
            s = FileShare.objects.get(id=share_id, file__user=request.user)
            s.delete()
            messages.success(request, '共享已撤销')
        except FileShare.DoesNotExist:
            messages.error(request, '共享不存在或无权限')
        return redirect('file_upload:share_list_page')

    context = {'shares': shares}
    return render(request, 'file_upload/share_list.html', context)


@login_required
def share_create_page(request):
    """创建文件共享到用户或组织的简单表单页面"""
    from authentication.models import Organization, Membership
    User = get_user_model()

    my_files = File.objects.filter(user=request.user).order_by('-uploaded_at')
    my_orgs = Organization.objects.filter(memberships__user=request.user).distinct()
    users = User.objects.all().order_by('email')[:200]  # 简单选择器，后续可改为搜索

    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        user_id = request.POST.get('user_id')
        org_id = request.POST.get('organization_id')
        can_download = bool(request.POST.get('can_download', '1'))
        can_edit_metadata = bool(request.POST.get('can_edit_metadata', ''))
        expires_at = request.POST.get('expires_at')  # 可选

        try:
            f = File.objects.get(id=file_id, user=request.user)
        except File.DoesNotExist:
            messages.error(request, '文件不存在或无权限')
            return redirect('file_upload:share_create_page')

        if not user_id and not org_id:
            messages.error(request, '必须选择共享到的用户或组织')
            return redirect('file_upload:share_create_page')

        share_kwargs = {
            'file': f,
            'can_download': can_download,
            'can_edit_metadata': can_edit_metadata,
        }
        if expires_at:
            try:
                from django.utils.dateparse import parse_datetime
                dt = parse_datetime(expires_at)
                if dt:
                    share_kwargs['expires_at'] = dt
            except Exception:
                pass

        if user_id:
            share_kwargs['shared_to_user_id'] = int(user_id)
        if org_id:
            share_kwargs['shared_to_organization_id'] = int(org_id)

        FileShare.objects.create(**share_kwargs)
        messages.success(request, '共享创建成功')
        return redirect('file_upload:share_list_page')

    context = {
        'my_files': my_files,
        'my_orgs': my_orgs,
        'users': users,
    }
    return render(request, 'file_upload/share_create.html', context)