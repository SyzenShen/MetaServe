import os
import mimetypes
import shutil
import re
import logging
import signal
import subprocess
import textwrap
import time
import requests
from pathlib import Path

from rest_framework import status
from django.db import models
from django.db.models import Q
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.authtoken.models import Token

class QueryTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        auth = super().authenticate(request)
        if auth:
            return auth
        key = request.query_params.get('token')
        if not key:
            return None
        try:
            t = Token.objects.get(key=key)
        except Token.DoesNotExist:
            return None
        return (t.user, t)
from rest_framework.decorators import api_view, permission_classes, parser_classes, authentication_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.http import Http404, StreamingHttpResponse, FileResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from django.core.files import File as DjangoFile

from .models import File, Folder
from .permission_utils import can_view_or_download_file, can_delete_file, can_view_folder
from .serializers import FileSerializer, FileUploadSerializer, FolderSerializer, FolderCreateSerializer
from .ncbi_client import (
    NCBIDownloadError,
    NCBIDownloadResult,
    NCBIDownloadTooLarge,
    download_ncbi_resource,
)

logger = logging.getLogger(__name__)


def _resolve_cellxgene_command():
    """根据配置或 PATH 查找 cellxgene 可执行文件，并验证可执行性。

    解析顺序：
    1. 若 `CELLXGENE_CMD` 为绝对路径且存在且可执行，直接返回；
    2. 尝试在 PATH 中解析 `CELLXGENE_CMD` 字符串；
    3. 回退到在 PATH 中查找 `cellxgene`；
    4. 若找不到，返回 None。

    注意：仅返回可执行的文件路径，避免将不可执行的占位路径作为结果。
    """
    configured = getattr(settings, 'CELLXGENE_CMD', None)
    candidates = []

    def _is_executable(path: str) -> bool:
        return os.path.isfile(path) and os.access(path, os.X_OK)

    if configured:
        # 绝对路径优先且必须可执行
        if os.path.isabs(configured) and _is_executable(configured):
            return configured
        # 若是相对路径或不可执行，允许交给 PATH 解析
        candidates.append(configured)

    # 标准命令名
    candidates.append('cellxgene')

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved and _is_executable(resolved):
            return resolved
    return None


def _is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _stop_existing_cellxgene(pid_path: Path):
    if not pid_path.exists():
        return
    try:
        pid = int(pid_path.read_text().strip())
    except (ValueError, OSError):
        pid_path.unlink(missing_ok=True)
        return

    if not _is_pid_running(pid):
        pid_path.unlink(missing_ok=True)
        return

    logger.info(f"Stopping existing Cellxgene process pid={pid}")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pid_path.unlink(missing_ok=True)
        return

    for _ in range(20):
        if not _is_pid_running(pid):
            break
        time.sleep(0.25)
    else:
        logger.warning("Cellxgene process did not terminate after SIGTERM, sending SIGKILL")
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    pid_path.unlink(missing_ok=True)


def prepare_h5ad_for_cellxgene(dataset_path: str):
    """确保 .h5ad 文件包含 Cellxgene 需要的二维布局"""
    # 优先使用配置的 Python 解释器；若不存在，尝试使用系统 python3/python
    configured_python = getattr(
        settings,
        'CELLXGENE_PYTHON',
        os.path.join(os.path.dirname(getattr(settings, 'CELLXGENE_CMD', 'cellxgene')), 'python'),
    )
    python_bin = None
    if configured_python and os.path.exists(configured_python):
        python_bin = configured_python
    else:
        python_bin = shutil.which('python3') or shutil.which('python')

    if not python_bin:
        return {
            'status': 'skipped',
            'message': '未找到 Python 解释器用于布局生成。请设置 CELLXGENE_PYTHON 或确保系统 PATH 中存在 python3/python'
        }

    script = textwrap.dedent(f"""
        import sys
        import numpy as np
        from pathlib import Path
        import anndata as ad
        try:
            from sklearn.decomposition import TruncatedSVD
        except Exception as exc:
            print(f"Failed to import TruncatedSVD: {{exc}}", file=sys.stderr)
            raise

        path = Path(r\"{dataset_path}\")
        adata = ad.read_h5ad(path)
        needs_layout = "X_umap" not in adata.obsm or adata.obsm["X_umap"].shape[1] < 2
        if not needs_layout:
            sys.exit(0)

        matrix = adata.X
        if hasattr(matrix, "tocsr"):
            matrix = matrix.tocsr()
        svd = TruncatedSVD(n_components=2, random_state=0)
        coords = svd.fit_transform(matrix)
        adata.obsm["X_umap"] = coords.astype("float32")
        adata.uns["umap"] = {{"params": {{"method": "TruncatedSVD", "n_components": 2}}}}
        adata.uns["default_embedding"] = "umap"
        adata.write(path)
    """)

    env = os.environ.copy()
    env.setdefault('PYTHONUNBUFFERED', '1')

    try:
        result = subprocess.run(
            [python_bin, '-c', script],
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR,
            env=env,
            check=False,
        )
    except OSError as exc:
        logger.error("Failed to invoke Cellxgene python for layout generation: %s", exc)
        return {'status': 'error', 'message': f'无法生成布局：{exc}'}

    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.error(
            "Cellxgene layout script failed (code=%s): stdout=%s stderr=%s",
            result.returncode,
            result.stdout.strip(),
            stderr,
        )
        # 友好提示缺少依赖
        dep_hint = None
        for mod, label in [('numpy', 'numpy'), ('anndata', 'anndata'), ('sklearn', 'scikit-learn'), ('h5py', 'h5py')]:
            if f"No module named '{mod}'" in stderr or f"No module named \"{mod}\"" in stderr:
                dep_hint = label
                break
        if dep_hint:
            return {
                'status': 'error',
                'message': f"缺少依赖：{dep_hint}。请在 CELLXGENE_PYTHON 指定的 Python 环境安装：pip install numpy anndata scikit-learn h5py"
            }
        return {
            'status': 'error',
            'message': stderr or 'Cellxgene 布局生成失败'
        }

    if result.stdout:
        logger.info("Cellxgene layout script output: %s", result.stdout.strip())
    return {'status': 'prepared', 'message': '已生成默认二维布局'}


def _kill_processes_on_port(port: int):
    try:
        result = subprocess.run(
            ['lsof', '-t', f'-iTCP:{port}', '-sTCP:LISTEN'],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return

    if result.returncode != 0 or not result.stdout:
        return

    for line in result.stdout.strip().splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if _is_pid_running(pid):
            logger.warning("Killing process %s occupying port %s", pid, port)
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                continue
            # give it a moment
            for _ in range(10):
                if not _is_pid_running(pid):
                    break
                time.sleep(0.1)
            if _is_pid_running(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def restart_cellxgene_process(dataset_path: str):
    """尝试使用新的数据集重新启动 Cellxgene 服务"""
    if not getattr(settings, 'CELLXGENE_AUTO_RESTART', True):
        return {'status': 'skipped', 'message': 'Cellxgene 自动重启已关闭，请手动启动服务'}

    command = _resolve_cellxgene_command()
    python_bin = getattr(settings, 'CELLXGENE_PYTHON', None)
    if not command and python_bin and os.path.exists(python_bin):
        # 回退方案：使用 python -m cellxgene 启动
        fallback = [python_bin, '-m', 'cellxgene']
    else:
        fallback = None
    if not command and not fallback:
        return {
            'status': 'error',
            'message': '未找到 cellxgene 命令。请安装 cellxgene 或设置环境变量 CELLXGENE_CMD 指向可执行文件，或设置 CELLXGENE_PYTHON 以使用 "python -m cellxgene" 启动。'
        }

    log_path = Path(getattr(settings, 'CELLXGENE_LOG_FILE', os.path.join(settings.BASE_DIR, 'logs', 'cellxgene.log')))
    pid_path = Path(getattr(settings, 'CELLXGENE_PID_FILE', os.path.join(settings.BASE_DIR, '.pids', 'cellxgene.pid')))
    host = getattr(settings, 'CELLXGENE_HOST', '0.0.0.0')
    port = str(getattr(settings, 'CELLXGENE_PORT', 5005))

    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    _stop_existing_cellxgene(pid_path)
    try:
        _kill_processes_on_port(int(port))
    except ValueError:
        pass

    env = os.environ.copy()
    env.setdefault('PYTHONUNBUFFERED', '1')

    try:
        with open(log_path, 'a', buffering=1) as log_file:
            args = [command, 'launch', dataset_path, '--host', host, '--port', port] if command else [*fallback, 'launch', dataset_path, '--host', host, '--port', port]
            proc = subprocess.Popen(
                args,
                stdout=log_file,
                stderr=log_file,
                cwd=settings.BASE_DIR,
                env=env,
            )
    except OSError as exc:
        logger.error("Failed to start Cellxgene: %s", exc)
        return {'status': 'error', 'message': f'无法启动 Cellxgene：{exc}'}

    pid_path.write_text(str(proc.pid))
    logger.info("Cellxgene restarted with dataset %s (pid=%s)", dataset_path, proc.pid)
    return {'status': 'started', 'message': 'Cellxgene 已重新加载数据，请稍候页面刷新', 'pid': proc.pid}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_list(request):
    """获取当前用户的文件列表，支持按文件夹过滤"""
    folder_id = request.GET.get('folder_id')
    
    # 获取文件夹信息（本人或组织文件夹）
    current_folder = None
    base_folder_qs = Folder.objects.filter(models.Q(user=request.user) | models.Q(organization__memberships__user=request.user)).distinct()
    if folder_id:
        try:
            current_folder = base_folder_qs.get(id=folder_id)
        except Folder.DoesNotExist:
            return Response({'error': '文件夹不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    # 获取当前文件夹下的子文件夹（本人或组织）
    if current_folder:
        folders = base_folder_qs.filter(parent=current_folder).order_by('name')
        files_qs = File.objects.filter(parent_folder=current_folder).order_by('-uploaded_at')
        from .permission_utils import can_view_or_download_file
        files = [f for f in files_qs if can_view_or_download_file(request.user, f)]
    else:
        # 根目录：本人或组织的根文件夹
        folders = base_folder_qs.filter(parent=None).order_by('name')
        # 根文件：仅显示本人，不在此处合并组织文件
        files = File.objects.filter(user=request.user, parent_folder=None).order_by('-uploaded_at')

        # 额外合并：共享给当前用户或其所在组织的文件（不再合并同组织的 Internal 文件）
        try:
            from authentication.models import Membership
            from .models import FileShare

            now = timezone.now()

            # 当前用户所在组织ID集合
            user_org_ids = set(Membership.objects.filter(user=request.user).values_list('organization_id', flat=True))

            # 有效（未过期）并允许下载的共享到当前用户
            shares_to_user = FileShare.objects.filter(
                shared_to_user_id=request.user.id,
                can_download=True,
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))

            # 有效并允许下载的共享到当前用户所在的组织
            shares_to_org = FileShare.objects.filter(
                shared_to_organization_id__in=list(user_org_ids) if user_org_ids else [],
                can_download=True,
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))

            shared_file_ids = set(shares_to_user.values_list('file_id', flat=True)) | set(shares_to_org.values_list('file_id', flat=True))

            # 合并并去重（保持时间倒序）。注意：不合并 Internal 可见范围，只显示自己的 Internal 文件
            base_ids = set(files.values_list('id', flat=True))
            all_ids = base_ids | shared_file_ids
            if all_ids:
                files = File.objects.filter(id__in=list(all_ids)).order_by('-uploaded_at')
        except Exception as e:
            logger.exception("Failed to augment file_list with shared/internal: %s", e)
    
    folder_serializer = FolderSerializer(folders, many=True, context={'request': request})
    file_serializer = FileSerializer(files, many=True, context={'request': request})
    
    return Response({
        'current_folder': FolderSerializer(current_folder, context={'request': request}).data if current_folder else None,
        'folders': folder_serializer.data,
        'files': file_serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_list_shared_to_me(request):
    """列出共享给当前用户的文件（未过期且允许下载）"""
    from .models import FileShare
    shares = FileShare.objects.filter(shared_to_user=request.user)
    shares = [s for s in shares if s.is_active() and s.can_download]
    file_ids = [s.file_id for s in shares]
    files = File.objects.filter(id__in=file_ids).order_by('-uploaded_at')
    serializer = FileSerializer(files, many=True, context={'request': request})
    return Response({'files': serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_list_org_internal(request):
    """列出同组织内可访问的 Internal 文件（包含自己与同组织成员）"""
    try:
        from authentication.models import Membership
    except Exception:
        return Response({'files': []})

    # 当前用户组织集合
    user_org_ids = set(Membership.objects.filter(user=request.user).values_list('organization_id', flat=True))
    if not user_org_ids:
        return Response({'files': []})

    # 找到同组织成员的用户ID
    member_user_ids = set(Membership.objects.filter(organization_id__in=user_org_ids).values_list('user_id', flat=True))

    files = File.objects.filter(user_id__in=member_user_ids, access_level__iexact='Internal').order_by('-uploaded_at')
    serializer = FileSerializer(files, many=True, context={'request': request})
    return Response({'files': serializer.data})


# ---- 文件共享管理 API ----

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def file_share_create(request):
    """创建文件共享到用户或组织，仅文件拥有者可操作"""
    # 延迟导入避免循环引用
    from .models import FileShare
    file_id = request.data.get('file_id')
    user_id = request.data.get('user_id') or request.data.get('shared_to_user_id')
    organization_id = request.data.get('organization_id') or request.data.get('shared_to_organization_id')
    can_download = bool(request.data.get('can_download', True))
    can_edit_metadata = bool(request.data.get('can_edit_metadata', False))
    expires_at = request.data.get('expires_at')  # ISO8601，可为空

    try:
        f = File.objects.get(id=file_id)
    except File.DoesNotExist:
        return Response({'detail': 'file not found'}, status=status.HTTP_404_NOT_FOUND)

    if f.user_id != request.user.id and not request.user.is_superuser:
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

    if not user_id and not organization_id:
        return Response({'detail': 'must provide user_id or organization_id'}, status=status.HTTP_400_BAD_REQUEST)

    share_kwargs = {
        'file': f,
        'can_download': can_download,
        'can_edit_metadata': can_edit_metadata,
    }
    if expires_at:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(expires_at)
        if not dt:
            return Response({'detail': 'invalid expires_at'}, status=status.HTTP_400_BAD_REQUEST)
        share_kwargs['expires_at'] = dt

    if user_id:
        share_kwargs['shared_to_user_id'] = int(user_id)
    if organization_id:
        share_kwargs['shared_to_organization_id'] = int(organization_id)

    share, _ = FileShare.objects.update_or_create(
        file=f,
        shared_to_user_id=share_kwargs.get('shared_to_user_id'),
        shared_to_organization_id=share_kwargs.get('shared_to_organization_id'),
        defaults=share_kwargs,
    )
    return Response({'id': share.id}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def file_share_list(request):
    """列出当前用户拥有文件的共享记录"""
    from .models import FileShare
    shares = FileShare.objects.filter(file__user=request.user).select_related('file')
    now = timezone.now()
    data = []
    for s in shares:
        expired = bool(s.expires_at and s.expires_at < now)
        data.append({
            'id': s.id,
            'file_id': s.file_id,
            'shared_to_user_id': s.shared_to_user_id,
            'shared_to_organization_id': s.shared_to_organization_id,
            'can_download': s.can_download,
            'can_edit_metadata': s.can_edit_metadata,
            'expires_at': s.expires_at.isoformat() if s.expires_at else None,
            'expired': expired,
        })
    return Response({'shares': data}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def file_share_delete(request, share_id):
    """删除共享记录，仅文件拥有者可删"""
    from .models import FileShare
    try:
        s = FileShare.objects.select_related('file').get(id=share_id)
    except FileShare.DoesNotExist:
        return Response({'detail': 'share not found'}, status=status.HTTP_404_NOT_FOUND)
    if s.file.user_id != request.user.id and not request.user.is_superuser:
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    s.delete()
    return Response({'message': 'share deleted'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def accept_shared_file(request):
    """接受共享的文件：复制到当前用户的 Files 中（默认为 Download 根目录）"""
    file_id = request.data.get('file_id')
    target_folder_id = request.data.get('target_folder_id') or request.data.get('folder_id')
    try:
        src = File.objects.get(id=file_id)
    except File.DoesNotExist:
        return Response({'detail': 'file not found'}, status=status.HTTP_404_NOT_FOUND)
    if not can_view_or_download_file(request.user, src):
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    if not src.file or not os.path.exists(src.file.path):
        return Response({'detail': 'source file not found'}, status=status.HTTP_404_NOT_FOUND)

    dest_parent = None
    if target_folder_id:
        try:
            dest_parent = Folder.objects.get(id=int(target_folder_id), user=request.user)
        except Folder.DoesNotExist:
            dest_parent = None
    if not dest_parent:
        dest_parent, _ = Folder.objects.get_or_create(user=request.user, parent=None, name='Download')

    try:
        with open(src.file.path, 'rb') as fp:
            django_file = DjangoFile(fp, name=src.original_filename or os.path.basename(src.file.name))
            new = File(
                user=request.user,
                upload_method='Shared Accept',
                parent_folder=dest_parent,
                original_filename=src.original_filename or os.path.basename(src.file.name),
                title=src.title or (src.original_filename or ''),
                project=src.project,
                document_type=src.document_type,
                file_format=src.file_format,
                access_level='Internal',
                organism=src.organism,
                experiment_type=src.experiment_type,
                tags=src.tags,
                description=src.description,
            )
            new.file.save(new.original_filename, django_file, save=True)
        try:
            new.extracted_metadata = getattr(src, 'extracted_metadata', {})
            new.save(update_fields=['extracted_metadata'])
        except Exception:
            pass
    except Exception:
        return Response({'detail': 'copy failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = FileSerializer(new, context={'request': request})
    return Response({'file': serializer.data}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def accept_shared_folder(request):
    """接受共享的文件夹：递归复制到当前用户的 Files 中（默认为 Download 根目录）"""
    folder_id = request.data.get('folder_id')
    target_folder_id = request.data.get('target_folder_id') or request.data.get('dest_parent_id')
    try:
        src_root = Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return Response({'detail': 'folder not found'}, status=status.HTTP_404_NOT_FOUND)
    if not can_view_folder(request.user, src_root):
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

    dest_parent = None
    if target_folder_id:
        try:
            dest_parent = Folder.objects.get(id=int(target_folder_id), user=request.user)
        except Folder.DoesNotExist:
            dest_parent = None
    if not dest_parent:
        dest_parent, _ = Folder.objects.get_or_create(user=request.user, parent=None, name='Download')

    def _copy_folder(src_folder, dst_parent):
        dst_folder, _ = Folder.objects.get_or_create(user=request.user, parent=dst_parent, name=src_folder.name)
        files_qs = list(getattr(src_folder, 'files', []).all()) if hasattr(src_folder, 'files') else []
        for f in files_qs:
            if not can_view_or_download_file(request.user, f):
                continue
            if not f.file or not os.path.exists(f.file.path):
                continue
            try:
                with open(f.file.path, 'rb') as fp:
                    djf = DjangoFile(fp, name=f.original_filename or os.path.basename(f.file.name))
                    nf = File(
                        user=request.user,
                        upload_method='Shared Accept',
                        parent_folder=dst_folder,
                        original_filename=f.original_filename or os.path.basename(f.file.name),
                        title=f.title or (f.original_filename or ''),
                        project=f.project,
                        document_type=f.document_type,
                        file_format=f.file_format,
                        access_level='Internal',
                        organism=f.organism,
                        experiment_type=f.experiment_type,
                        tags=f.tags,
                        description=f.description,
                    )
                    nf.file.save(nf.original_filename, djf, save=True)
                try:
                    nf.extracted_metadata = getattr(f, 'extracted_metadata', {})
                    nf.save(update_fields=['extracted_metadata'])
                except Exception:
                    pass
            except Exception:
                continue
        for sub in src_folder.subfolders.all():
            if can_view_folder(request.user, sub):
                _copy_folder(sub, dst_folder)
        return dst_folder

    dst_root = _copy_folder(src_root, dest_parent)
    serializer = FolderSerializer(dst_root, context={'request': request})
    return Response({'folder': serializer.data}, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def file_upload(request):
    """文件上传"""
    # 记录请求数据
    logger.error(f"Upload request data: {dict(request.data)}")
    logger.error(f"Upload request files: {dict(request.FILES)}")
    logger.error(f"Upload request user: {request.user}")
    
    serializer = FileUploadSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        file_obj = serializer.save()

        # 父文件夹组织继承与强制可见性
        try:
            parent_id = request.data.get('parent_folder')
            if parent_id:
                from .models import Folder
                parent_folder = Folder.objects.filter(id=parent_id).first()
                if parent_folder and getattr(parent_folder, 'organization', None):
                    # 强制 Restricted 并继承组织
                    file_obj.access_level = 'Restricted'
                    file_obj.parent_folder = parent_folder
                    file_obj.save(update_fields=['access_level', 'parent_folder'])
        except Exception:
            pass

        # 如果是受限访问并且提供了组织ID，则创建文件共享记录（仅 owner/admin 允许）
        try:
            access_level = (file_obj.access_level or '').strip()
            org_id = request.data.get('organization_id')
            if access_level == 'Restricted' and org_id:
                from .models import FileShare
                from authentication.models import Organization, Membership
                try:
                    organization = Organization.objects.get(id=org_id)
                    # 权限：只有该组织的 owner/admin 才能在上传时共享到组织
                    me = Membership.objects.filter(organization_id=org_id, user=request.user).first()
                    if not me or me.role not in ('owner', 'admin'):
                        return Response({'detail': 'only owner/admin can upload to organization'}, status=status.HTTP_403_FORBIDDEN)
                    FileShare.objects.create(
                        file=file_obj,
                        shared_to_organization=organization,
                        can_download=True,
                        can_edit_metadata=False,
                    )
                except Organization.DoesNotExist:
                    logger.warning(f"organization_id {org_id} not found; skip FileShare creation")
            elif access_level == 'Restricted' and not org_id:
                # 未选择组织但选择了 Restricted：仅当用户在任一组织中为 owner/admin 才允许
                from authentication.models import Membership
                has_privileged_role = Membership.objects.filter(user=request.user, role__in=['owner', 'admin']).exists()
                if not has_privileged_role:
                    return Response({'detail': 'only owner/admin can set Restricted access'}, status=status.HTTP_403_FORBIDDEN)
            else:
                # 禁止在组织文件夹中上传 Internal/Public
                try:
                    parent_id = request.data.get('parent_folder')
                    if parent_id:
                        from .models import Folder
                        pf = Folder.objects.filter(id=parent_id).first()
                        if pf and getattr(pf, 'organization', None):
                            if (access_level or '').lower() in ('internal', 'public'):
                                return Response({'detail': 'cannot upload Internal/Public in organization folder; use Restricted'}, status=status.HTTP_403_FORBIDDEN)
                except Exception:
                    pass
        except Exception as e:
            logger.exception("Failed to create FileShare on restricted upload: %s", e)

        response_serializer = FileSerializer(file_obj, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    # 记录详细的验证错误
    logger.error(f"Serializer validation errors: {serializer.errors}")
    
    # 统一错误消息格式，便于前端展示
    errors = serializer.errors
    message = None
    if isinstance(errors, dict):
        # 优先返回 file 字段的错误
        file_errors = errors.get('file')
        if isinstance(file_errors, list) and file_errors:
            message = str(file_errors[0])
    if not message:
        message = '文件上传失败'
    return Response({'message': message, 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ncbi_import(request):
    """从 NCBI 链接下载文件并保存到当前用户空间。"""
    url = request.data.get('url')
    parent_folder_id = request.data.get('parent_folder')
    project = request.data.get('project') or 'NCBI Import'
    access_level = request.data.get('access_level') or 'Internal'

    if not url:
        return Response({'message': '请提供 NCBI 链接'}, status=status.HTTP_400_BAD_REQUEST)

    parent_folder = None
    if parent_folder_id is not None:
        try:
            parent_folder = Folder.objects.get(id=parent_folder_id, user=request.user)
        except Folder.DoesNotExist:
            return Response({'message': '指定的文件夹不存在或无权限访问'}, status=status.HTTP_404_NOT_FOUND)

    try:
        download_result: NCBIDownloadResult = download_ncbi_resource(url)
    except NCBIDownloadTooLarge as exc:
        return Response({'message': str(exc)}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    except NCBIDownloadError as exc:
        return Response({'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except requests.RequestException as exc:
        logger.exception("NCBI request failed: %s", exc)
        return Response({'message': f'无法连接 NCBI 服务：{exc}'}, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as exc:
        logger.exception("Unexpected NCBI import failure: %s", exc)
        return Response({'message': f'下载失败：{exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    file_obj = None
    try:
        with open(download_result.file_path, 'rb') as handle:
            django_file = DjangoFile(handle, name=download_result.filename)

            raw_tags = request.data.get('tags')
            user_tags = []
            if isinstance(raw_tags, list):
                user_tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
            elif isinstance(raw_tags, str):
                user_tags = [tag.strip() for tag in raw_tags.split(',') if tag.strip()]
            base_tags = ['NCBI', download_result.db.upper()]
            combined_tags = []
            for tag in base_tags + user_tags:
                if tag and tag not in combined_tags:
                    combined_tags.append(tag)
            tag_string = ','.join(combined_tags)

            metadata = download_result.metadata or {}
            description = metadata.get('title') or metadata.get('extra') or ''
            if metadata.get('summary'):
                description = f"{description}\n{metadata['summary']}".strip()

            file_obj = File.objects.create(
                user=request.user,
                file=django_file,
                upload_method='NCBI Import',
                parent_folder=parent_folder,
                title=metadata.get('title') or download_result.filename,
                project=project,
                original_filename=download_result.filename,
                file_format=download_result.file_format,
                document_type=download_result.document_type,
                access_level=access_level,
                organism=metadata.get('organism') or '',
                experiment_type=metadata.get('experiment_type') or '',
                tags=tag_string,
                description=description,
            )
            file_obj.extracted_metadata = metadata
            file_obj.save()
    finally:
        if os.path.exists(download_result.file_path):
            os.remove(download_result.file_path)

    serializer = FileSerializer(file_obj, context={'request': request})
    return Response({'file': serializer.data, 'metadata': download_result.metadata}, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def file_delete(request, file_id):
    """删除文件"""
    try:
        # 允许跨用户查找对象，但随后做对象级删除权限校验
        file_obj = File.objects.get(id=file_id)

        if not can_delete_file(request.user, file_obj):
            # 与下载保持一致，隐藏资源存在性，防止信息泄露
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        # 删除物理文件
        if file_obj.file and os.path.exists(file_obj.file.path):
            try:
                os.remove(file_obj.file.path)
            except Exception:
                # 即使物理删除失败，仍继续删除数据库记录，避免悬挂数据
                pass
        file_obj.delete()
        return Response({'message': 'File deleted successfully'}, status=status.HTTP_200_OK)
    except File.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([QueryTokenAuthentication, TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def file_download(request, file_id):
    """文件下载"""
    try:
        # 获取文件对象（不再限定为当前用户），改为对象级权限校验
        try:
            file_obj = File.objects.get(id=file_id)
        except File.DoesNotExist:
            logger.warning(f"File not found: id={file_id}")
            raise Http404("File not found")

        # 权限校验
        if not can_view_or_download_file(request.user, file_obj):
            logger.info(f"Forbidden download: file_id={file_id}, user={request.user.id}")
            raise Http404("File not found")

        # 验证文件是否存在
        if not file_obj.file:
            logger.error(f"File object has no file: id={file_id}")
            raise Http404("File not found")
            
        file_path = file_obj.file.path
        if not os.path.exists(file_path):
            logger.error(f"Physical file not found: path={file_path}, id={file_id}")
            raise Http404("File not found")

        # 验证文件可读性
        try:
            with open(file_path, 'rb') as test_file:
                test_file.read(1)  # 尝试读取1字节
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Cannot read file: path={file_path}, error={str(e)}")
            raise Http404("File not accessible")

        file_name = file_obj.original_filename or os.path.basename(file_path)
        
        # 安全的文件名处理
        import urllib.parse
        safe_filename = urllib.parse.quote(file_name.encode('utf-8'))

        # MIME类型
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'

        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            logger.error(f"Cannot get file size: path={file_path}, error={str(e)}")
            raise Http404("File not accessible")

        range_header = request.headers.get('Range') or request.META.get('HTTP_RANGE')
        
        logger.info(f"Download request: file_id={file_id}, user={request.user.id}, "
                   f"size={file_size}, range={range_header}")

        if range_header:
            # 解析 Range: bytes=start-end
            try:
                units, rng = range_header.split('=')
                if units.strip() != 'bytes':
                    raise ValueError('Invalid units')
                start_str, end_str = rng.split('-')
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                
                # 验证范围
                if start < 0 or end >= file_size or start > end:
                    logger.warning(f"Invalid range: start={start}, end={end}, size={file_size}")
                    start = 0
                    end = file_size - 1
            except Exception as e:
                logger.warning(f"Range parsing error: {str(e)}")
                start = 0
                end = file_size - 1

            length = end - start + 1

            def file_iterator(path, offset, length, chunk_size=8192):
                try:
                    with open(path, 'rb') as f:
                        f.seek(offset)
                        remaining = length
                        while remaining > 0:
                            chunk_to_read = min(chunk_size, remaining)
                            chunk = f.read(chunk_to_read)
                            if not chunk:
                                logger.warning(f"Unexpected EOF: path={path}, offset={offset}, remaining={remaining}")
                                break
                            remaining -= len(chunk)
                            yield chunk
                except (IOError, OSError) as e:
                    logger.error(f"Error reading file during streaming: path={path}, error={str(e)}")
                    raise

            response = StreamingHttpResponse(
                file_iterator(file_path, start, length), content_type=content_type, status=206
            )
            response['Content-Length'] = str(length)
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            response['Content-Disposition'] = f'attachment; filename="{file_name}"; filename*=UTF-8\'\'{safe_filename}'
            
            logger.info(f"Partial download started: file_id={file_id}, range={start}-{end}")
            return response
        else:
            # 全量下载，流式传输
            try:
                file_handle = open(file_path, 'rb')
                response = FileResponse(file_handle, content_type=content_type)
                response['Content-Length'] = str(file_size)
                response['Accept-Ranges'] = 'bytes'
                response['Content-Disposition'] = f'attachment; filename="{file_name}"; filename*=UTF-8\'\'{safe_filename}'
                
                logger.info(f"Full download started: file_id={file_id}, size={file_size}")
                return response
            except (IOError, OSError) as e:
                logger.error(f"Error opening file for download: path={file_path}, error={str(e)}")
                raise Http404("File not accessible")
            
    except Http404:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in file download: file_id={file_id}, error={str(e)}")
        raise Http404("Download failed")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_cellxgene(request, file_id):
    """将指定文件发布到 Cellxgene 数据目录以便预览

    要求：文件为 .h5ad 格式；将物理文件复制到 settings.CELLXGENE_DATA_DIR 下，
    避免破坏用户原始文件结构。返回发布后的目标文件名及目录。
    """
    try:
        # 获取文件对象（仅限当前用户）
        try:
            file_obj = File.objects.get(id=file_id, user=request.user)
        except File.DoesNotExist:
            return Response({'message': '文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 验证物理文件存在
        if not file_obj.file or not os.path.exists(file_obj.file.path):
            return Response({'message': '物理文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 校验扩展名为 .h5ad
        original = file_obj.original_filename or os.path.basename(file_obj.file.name)
        if not str(original).lower().endswith('.h5ad'):
            return Response({'message': '仅支持 .h5ad 文件发布到 Cellxgene'}, status=status.HTTP_400_BAD_REQUEST)

        # 目标目录（可通过环境变量 CELLXGENE_DATA_DIR 配置）
        from django.conf import settings
        target_dir = getattr(settings, 'CELLXGENE_DATA_DIR', os.path.join(settings.BASE_DIR, 'cellxgene_data'))
        os.makedirs(target_dir, exist_ok=True)

        # 安全文件名：避免特殊字符与路径穿越
        safe_basename = re.sub(r'[^A-Za-z0-9\._-]', '_', os.path.basename(original))
        target_filename = f"{file_obj.id}__{safe_basename}"
        target_path = os.path.join(target_dir, target_filename)

        try:
            shutil.copy2(file_obj.file.path, target_path)
        except Exception as e:
            return Response({'message': f'复制文件失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        prepare_info = prepare_h5ad_for_cellxgene(target_path)
        if prepare_info.get('status') == 'error':
            message = f"已复制到 Cellxgene 数据目录，但无法生成可视化布局：{prepare_info.get('message')}"
            logger.error("Cellxgene layout preparation failed for %s: %s", target_filename, prepare_info)
            return Response(
                {
                    'message': message,
                    'published_file': target_filename,
                    'target_dir': target_dir,
                    'cellxgene': {'status': 'error', 'message': prepare_info.get('message')},
                    'layout': prepare_info,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        restart_info = restart_cellxgene_process(target_path)
        message = '已发布到 Cellxgene 数据目录'

        status_text = restart_info.get('status')
        if status_text == 'started':
            message += '，Cellxgene 正在重新加载该文件，请稍候片刻。'
        elif status_text == 'skipped':
            message += '。自动重启已关闭，请手动启动 Cellxgene 服务。'
        elif status_text == 'error':
            detail = restart_info.get('message') or 'Cellxgene 启动失败'
            message += f'，但无法自动启动 Cellxgene：{detail}'
            logger.error("Cellxgene restart failed for file %s: %s", target_filename, detail)

        response_payload = {
            'message': message,
            'published_file': target_filename,
            'target_dir': target_dir,
            'layout': prepare_info,
            'cellxgene': restart_info,
            'cellxgene_port': getattr(settings, 'CELLXGENE_PORT', 5005),
        }
        return Response(response_payload, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'message': f'发布过程中发生错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """获取用户文件统计信息"""
    user_files = File.objects.filter(user=request.user)
    user_folders = Folder.objects.filter(user=request.user)
    total_files = user_files.count()
    total_folders = user_folders.count()
    total_size = sum(f.file_size for f in user_files)
    
    return Response({
        'total_files': total_files,
        'total_folders': total_folders,
        'total_size': total_size,
        'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size > 0 else 0
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def folder_list_create(request):
    """获取文件夹列表或创建新文件夹"""
    if request.method == 'GET':
        parent_id = request.GET.get('parent_id')
        from .permission_utils import can_view_folder
        # 查询范围：属于本人或关联到任一我所在组织的文件夹
        base_qs = Folder.objects.filter(models.Q(user=request.user) | models.Q(organization__memberships__user=request.user)).distinct()
        if parent_id:
            try:
                parent_folder = base_qs.get(id=parent_id)
            except Folder.DoesNotExist:
                return Response({'error': '父文件夹不存在或无权限访问'}, status=status.HTTP_404_NOT_FOUND)
            folders = base_qs.filter(parent=parent_folder).order_by('name')
        else:
            folders = base_qs.filter(parent=None).order_by('name')
        folders = [f for f in folders if can_view_folder(request.user, f)]
        serializer = FolderSerializer(folders, many=True, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = FolderCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # 验证父文件夹权限
            parent_folder = serializer.validated_data.get('parent')
            if parent_folder:
                # 父文件夹需具备可见性
                from .permission_utils import can_view_folder
                if not can_view_folder(request.user, parent_folder):
                    return Response({'error': '无权限在此文件夹下创建子文件夹'}, status=status.HTTP_403_FORBIDDEN)
            # 组织创建权限：仅 owner/admin 可创建关联组织的文件夹
            org = serializer.validated_data.get('organization')
            if not org and parent_folder and getattr(parent_folder, 'organization', None):
                org = parent_folder.organization
            if org is not None:
                try:
                    from authentication.models import Membership
                    me = Membership.objects.filter(organization_id=getattr(org, 'id', org), user=request.user).first()
                    if not me or me.role not in ('owner', 'admin'):
                        return Response({'error': '仅 owner/admin 可在组织下创建文件夹'}, status=status.HTTP_403_FORBIDDEN)
                except Exception:
                    return Response({'error': '组织信息错误'}, status=status.HTTP_400_BAD_REQUEST)
            if org is not None:
                folder = serializer.save(organization=org)
            else:
                folder = serializer.save()
            response_serializer = FolderSerializer(folder, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def folder_detail(request, folder_id):
    """获取、更新或删除文件夹"""
    try:
        folder = Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return Response({'error': '文件夹不存在'}, status=status.HTTP_404_NOT_FOUND)
    from .permission_utils import can_view_folder
    if not can_view_folder(request.user, folder):
        return Response({'error': '文件夹不存在'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        serializer = FolderSerializer(folder, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = FolderCreateSerializer(folder, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            # 验证父文件夹权限
            parent_folder = serializer.validated_data.get('parent')
            if parent_folder:
                if not can_view_folder(request.user, parent_folder):
                    return Response({'error': '无权限移动到此文件夹'}, status=status.HTTP_403_FORBIDDEN)
            # 组织更新权限：仅 owner/admin 可设置组织字段
            org = serializer.validated_data.get('organization')
            if not org and parent_folder and getattr(parent_folder, 'organization', None):
                org = parent_folder.organization
            # 公开设置：仅根文件夹且拥有者或组织 owner/admin 才允许切换公开状态
            is_public = serializer.validated_data.get('is_public', None)
            if is_public is not None:
                # 仅根文件夹
                if folder.parent_id is not None:
                    return Response({'error': '仅最上级文件夹可设置公开'}, status=status.HTTP_403_FORBIDDEN)
                # 个人根：仅本人可改；组织根：仅组织 owner/admin 可改
                if folder.organization_id is None:
                    if folder.user_id != request.user.id and not getattr(request.user, 'is_superuser', False):
                        return Response({'error': '无权限设置公开'}, status=status.HTTP_403_FORBIDDEN)
                    # 公开优先：清除组织（个人根）
                    serializer.validated_data['organization'] = None
                else:
                    # 允许文件夹拥有者或组织 owner/admin 切换公开
                    if folder.user_id != request.user.id and not getattr(request.user, 'is_superuser', False):
                        try:
                            from authentication.models import Membership
                            me = Membership.objects.filter(organization_id=folder.organization_id, user=request.user).first()
                            if not me or me.role not in ('owner', 'admin'):
                                return Response({'error': '仅组织 owner/admin 或文件夹拥有者可设置公开'}, status=status.HTTP_403_FORBIDDEN)
                        except Exception:
                            return Response({'error': '组织信息错误'}, status=status.HTTP_400_BAD_REQUEST)
            if org is not None:
                try:
                    from authentication.models import Membership
                    me = Membership.objects.filter(organization_id=getattr(org, 'id', org), user=request.user).first()
                    if not me or me.role not in ('owner', 'admin'):
                        return Response({'error': '仅 owner/admin 可设置组织关联'}, status=status.HTTP_403_FORBIDDEN)
                except Exception:
                    return Response({'error': '组织信息错误'}, status=status.HTTP_400_BAD_REQUEST)
            if org is not None:
                folder = serializer.save(organization=org, is_public=bool(is_public) if is_public is not None else folder.is_public)
            else:
                folder = serializer.save(is_public=bool(is_public) if is_public is not None else folder.is_public)
            response_serializer = FolderSerializer(folder, context={'request': request})
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        try:
            orphan_ids = []
            for f in folder.files.all():
                fp_missing = (not getattr(f, 'file', None)) or (getattr(f, 'file', None) and not os.path.exists(f.file.path))
                zero_size = (getattr(f, 'file_size', 0) or 0) == 0
                if fp_missing or zero_size:
                    orphan_ids.append(f.id)
            if orphan_ids:
                from .models import File as FileModel
                FileModel.objects.filter(id__in=orphan_ids).delete()
        except Exception:
            pass
        # 只有拥有者或组织 owner/admin 可删除
        if folder.user_id != request.user.id:
            try:
                from authentication.models import Membership
                if not folder.organization:
                    return Response({'error': '无权限删除该文件夹'}, status=status.HTTP_403_FORBIDDEN)
                me = Membership.objects.filter(organization_id=folder.organization_id, user=request.user).first()
                if not me or me.role not in ('owner', 'admin'):
                    return Response({'error': '无权限删除该文件夹'}, status=status.HTTP_403_FORBIDDEN)
            except Exception:
                return Response({'error': '无权限删除该文件夹'}, status=status.HTTP_403_FORBIDDEN)
        to_visit = [folder]
        folders = []
        files = []
        while to_visit:
            cur = to_visit.pop()
            folders.append(cur)
            for sf in cur.subfolders.all():
                to_visit.append(sf)
            for fl in cur.files.all():
                files.append(fl)
        for fl in files:
            try:
                if getattr(fl, 'file', None) and os.path.exists(fl.file.path):
                    try:
                        os.remove(fl.file.path)
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                fl.delete()
            except Exception:
                pass
        for fd in reversed(folders):
            try:
                fd.delete()
            except Exception:
                pass
        return Response({'message': '文件夹删除成功'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def folder_breadcrumb(request, folder_id):
    """获取文件夹的面包屑导航路径"""
    try:
        folder = Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return Response({'error': '文件夹不存在'}, status=status.HTTP_404_NOT_FOUND)
    from .permission_utils import can_view_folder
    if not can_view_folder(request.user, folder):
        return Response({'error': '文件夹不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    breadcrumb = []
    current = folder
    while current:
        breadcrumb.insert(0, {
            'id': current.id,
            'name': current.name,
            'path': current.get_path()
        })
        current = current.parent
    
    return Response(breadcrumb)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def folder_all(request):
    """获取当前用户的所有文件夹"""
    folders = Folder.objects.filter(models.Q(user=request.user) | models.Q(organization__memberships__user=request.user)).distinct().order_by('name')
    folder_serializer = FolderSerializer(folders, many=True, context={'request': request})
    
    return Response({
        'folders': folder_serializer.data
    })
# ---- 文件详情更新（权限/组织/访问级别） ----

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def file_detail(request, file_id):
    """获取或更新文件的基础信息与访问控制

    更新允许的字段：
    - access_level: Public/Internal/Restricted
    - parent_folder: 可移动到有权限访问的文件夹
    - 组织关联：通过父文件夹的 organization 继承；不直接在 File 上设置组织
      若移动到一个有关联组织的文件夹，则该文件视为组织内部文件（通常 access_level=Internal）
    权限：仅文件拥有者可修改；管理员可读取但不修改。
    """
    try:
        f = File.objects.get(id=file_id)
    except File.DoesNotExist:
        return Response({'error': '文件不存在'}, status=status.HTTP_404_NOT_FOUND)

    # 仅拥有者允许更新
    is_owner = getattr(f, 'user_id', None) == getattr(request.user, 'id', None)

    if request.method == 'GET':
        ser = FileSerializer(f, context={'request': request})
        return Response(ser.data)

    # PUT
    if not is_owner and not getattr(request.user, 'is_superuser', False):
        # 与删除策略保持一致：隐藏资源存在性
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

    payload = request.data or {}
    allowed_fields = {'access_level', 'parent_folder'}
    data = {k: v for k, v in payload.items() if k in allowed_fields}

    # 校验 parent_folder 可见性
    parent_folder_id = data.get('parent_folder')
    parent_folder = None
    if parent_folder_id:
        try:
            parent_folder = Folder.objects.get(id=parent_folder_id)
        except Folder.DoesNotExist:
            return Response({'error': '目标文件夹不存在'}, status=status.HTTP_404_NOT_FOUND)
        from .permission_utils import can_view_folder
        if not can_view_folder(request.user, parent_folder):
            return Response({'error': '无权限移动到此文件夹'}, status=status.HTTP_403_FORBIDDEN)

    # 访问级别规范化
    access_level = data.get('access_level')
    if access_level:
        access_level = str(access_level).strip()
        if access_level not in ('Public', 'Internal', 'Restricted'):
            return Response({'error': '无效的访问级别'}, status=status.HTTP_400_BAD_REQUEST)

    # 应用更新
    if parent_folder is not None:
        f.parent_folder = parent_folder
        # 若目标文件夹属于某组织，建议同步为 Internal（如未显式指定）
        try:
            if getattr(parent_folder, 'organization', None) and not access_level:
                access_level = 'Internal'
        except Exception:
            pass

    if access_level:
        f.access_level = access_level

    f.save(update_fields=['parent_folder', 'access_level'])
    ser = FileSerializer(f, context={'request': request})
    return Response(ser.data)
