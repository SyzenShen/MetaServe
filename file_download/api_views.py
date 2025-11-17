import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings


def _safe_abs_path(base_dir: str, candidate: str) -> str:
    base = Path(base_dir).resolve()
    target = (base / candidate).resolve()
    if base not in target.parents and base != target:
        raise ValueError('Invalid path outside base dir')
    return str(target)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def downloads_start(request):
    """Start a background download using download_nd.py.

    Request JSON:
    - url: source URL or share link (optional; script parses mail file as well)
    - outdir: output directory relative to a configured base (optional)
    - mail: path to mail.txt relative to base dir (optional; defaults to mail.txt)

    Response: { status: 'accepted', pid, log, cwd }
    """
    url = (request.data.get('url') or '').strip()
    rel_outdir = (request.data.get('outdir') or 'downloads').strip()
    rel_mail = (request.data.get('mail') or 'mail.txt').strip()

    base_dir = getattr(settings, 'DOWNLOADS_BASE_DIR', os.path.join(settings.BASE_DIR, 'downloads'))
    os.makedirs(base_dir, exist_ok=True)

    try:
        outdir = _safe_abs_path(base_dir, rel_outdir)
        mail_path = _safe_abs_path(settings.BASE_DIR, rel_mail)
    except ValueError:
        return Response({'detail': 'Invalid path'}, status=status.HTTP_400_BAD_REQUEST)

    os.makedirs(outdir, exist_ok=True)

    script_path = os.path.join(settings.BASE_DIR, 'download_nd.py')
    if not os.path.exists(script_path):
        return Response({'detail': 'download_nd.py not found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = tempfile.NamedTemporaryFile(prefix='download_', suffix='.log', dir=log_dir, delete=False)
    log_file_path = log_file.name
    log_file.close()

    # Build command: python download_nd.py -o <outdir> -m <mail>
    python_bin = os.environ.get('PYTHON_BIN') or 'python3'
    cmd = [python_bin, script_path, '-o', outdir, '-m', mail_path]
    env = os.environ.copy()
    if url:
        env['DOWNLOAD_URL'] = url  # script currently reads mail; URL can be used in future

    try:
        with open(log_file_path, 'a', buffering=1) as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, cwd=settings.BASE_DIR, env=env)
    except OSError as exc:
        return Response({'detail': f'Failed to start download: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'status': 'accepted',
        'pid': proc.pid,
        'log': log_file_path,
        'cwd': outdir,
    }, status=status.HTTP_202_ACCEPTED)