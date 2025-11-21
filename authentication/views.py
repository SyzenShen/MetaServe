from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer
from django.contrib.auth import get_user_model
from .models import Organization, Membership
from django.contrib.auth.hashers import check_password
from .validators import ComplexPasswordValidator
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings
import os


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def register(request):
    """用户注册"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def login_view(request):
    """用户登录"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def logout_view(request):
    """用户登出"""
    try:
        # 删除用户的token
        request.user.auth_token.delete()
    except:
        pass
    logout(request)
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def user_profile(request):
    """获取用户信息"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def update_profile(request):
    """更新用户信息"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([TokenAuthentication])
def set_user_quota(request, user_id):
    """管理员更新指定用户的存储限额（字节）"""
    User = get_user_model()
    try:
        target_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    quota = request.data.get('storage_quota')
    if quota is None:
        return Response({'detail': 'storage_quota is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        quota_int = int(quota)
        if quota_int <= 0:
            return Response({'detail': 'storage_quota must be positive'}, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({'detail': 'storage_quota must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

    target_user.storage_quota = quota_int
    target_user.save(update_fields=['storage_quota'])

    return Response({'message': 'Quota updated', 'user': UserSerializer(target_user).data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def change_password(request):
    """用户自行修改密码：校验旧密码与新密码复杂度"""
    old_password = request.data.get('old_password') or ''
    new_password = request.data.get('new_password') or ''
    confirm_password = request.data.get('confirm_password') or ''

    # 基本校验
    if not old_password or not new_password or not confirm_password:
        return Response({'detail': 'old_password/new_password/confirm_password are required'}, status=status.HTTP_400_BAD_REQUEST)

    if new_password != confirm_password:
        return Response({'detail': 'passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)

    # 旧密码校验
    if not check_password(old_password, request.user.password):
        return Response({'detail': 'old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

    # 新密码复杂度校验
    try:
        ComplexPasswordValidator().validate(new_password, user=request.user)
    except Exception as e:
        # e 可为 ValidationError，返回列表或字符串
        if hasattr(e, 'messages'):
            return Response(e.messages, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 设置新密码
    request.user.set_password(new_password)
    request.user.save()

    # 重新签发 token，避免旧 token 泄露风险（可选）
    try:
        # 删除旧 token
        request.user.auth_token.delete()
    except Exception:
        pass
    token, _ = Token.objects.get_or_create(user=request.user)

    return Response({'message': 'Password changed', 'token': token.key}, status=status.HTTP_200_OK)


# ---- 组织与成员管理 API ----

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def org_create(request):
    """创建组织，当前用户为 owner"""
    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'detail': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if Organization.objects.filter(name=name).exists():
        return Response({'detail': 'organization name exists'}, status=status.HTTP_400_BAD_REQUEST)
    org = Organization.objects.create(name=name, owner=request.user)
    Membership.objects.create(organization=org, user=request.user, role='owner')
    return Response({'id': org.id, 'name': org.name}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def org_list(request):
    """列出当前用户关联的组织"""
    qs = Organization.objects.filter(memberships__user=request.user).distinct()
    # 返回当前用户在各组织的角色，便于前端控制权限
    my_memberships = Membership.objects.filter(user=request.user, organization__in=qs).values('organization_id', 'role')
    role_map = {m['organization_id']: m['role'] for m in my_memberships}
    data = [{'id': o.id, 'name': o.name, 'role': role_map.get(o.id)} for o in qs]
    return Response({'organizations': data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def org_members(request, org_id):
    """列出组织成员"""
    try:
        org = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return Response({'detail': 'organization not found'}, status=status.HTTP_404_NOT_FOUND)
    # 需要是组织成员才允许查看
    if not Membership.objects.filter(organization=org, user=request.user).exists():
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    ms = Membership.objects.filter(organization=org).select_related('user')
    data = [{'id': m.id, 'user_id': m.user_id, 'email': m.user.email, 'role': m.role} for m in ms]
    return Response({'members': data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def org_member_add(request, org_id):
    """添加成员，需 owner/admin 权限"""
    try:
        org = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return Response({'detail': 'organization not found'}, status=status.HTTP_404_NOT_FOUND)
    me = Membership.objects.filter(organization=org, user=request.user).first()
    if not me or me.role not in ('owner', 'admin'):
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

    User = get_user_model()
    user_id = request.data.get('user_id')
    role = request.data.get('role', 'member')
    try:
        target = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
    Membership.objects.update_or_create(organization=org, user=target, defaults={'role': role})
    return Response({'message': 'member added'}, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def org_member_update(request, org_id, member_id):
    """更新成员角色，需 owner/admin 权限"""
    try:
        org = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return Response({'detail': 'organization not found'}, status=status.HTTP_404_NOT_FOUND)
    me = Membership.objects.filter(organization=org, user=request.user).first()
    if not me or me.role not in ('owner', 'admin'):
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    try:
        m = Membership.objects.get(id=member_id, organization=org)
    except Membership.DoesNotExist:
        return Response({'detail': 'member not found'}, status=status.HTTP_404_NOT_FOUND)
    role = request.data.get('role')
    if role not in ('owner', 'admin', 'member', 'viewer'):
        return Response({'detail': 'invalid role'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def logo_png(request):
    """直接返回项目中的 logo 图片，绕过 /static 路由问题"""
    candidate_paths = []
    # STATIC_ROOT
    if getattr(settings, 'STATIC_ROOT', None):
        candidate_paths.append(os.path.join(settings.STATIC_ROOT, 'logo.png'))
        candidate_paths.append(os.path.join(settings.STATIC_ROOT, 'file_upload', 'logo.png'))
    # STATICFILES_DIRS
    for d in getattr(settings, 'STATICFILES_DIRS', []):
        candidate_paths.append(os.path.join(d, 'logo.png'))
        candidate_paths.append(os.path.join(d, 'file_upload', 'logo.png'))
    # 项目根 static 及 app 内 static 作为兜底
    base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
    candidate_paths.append(os.path.join(base_dir, 'static', 'logo.png'))
    candidate_paths.append(os.path.join(base_dir, 'static', 'file_upload', 'logo.png'))
    candidate_paths.append(os.path.join(base_dir, 'file_upload', 'static', 'file_upload', 'logo.png'))

    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return FileResponse(open(p, 'rb'), content_type='image/png')
            except Exception:
                break
    return HttpResponseNotFound('logo not found')
    m.role = role
    m.save(update_fields=['role'])
    return Response({'message': 'member updated'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def org_member_remove(request, org_id, member_id):
    """移除成员，需 owner/admin 权限"""
    try:
        org = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return Response({'detail': 'organization not found'}, status=status.HTTP_404_NOT_FOUND)
    me = Membership.objects.filter(organization=org, user=request.user).first()
    if not me or me.role not in ('owner', 'admin'):
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    try:
        m = Membership.objects.get(id=member_id, organization=org)
    except Membership.DoesNotExist:
        return Response({'detail': 'member not found'}, status=status.HTTP_404_NOT_FOUND)
    m.delete()
    return Response({'message': 'member removed'}, status=status.HTTP_200_OK)
