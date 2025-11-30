import os
import shlex
import subprocess
import tempfile
from pathlib import Path
import threading
import signal

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_str


def _safe_abs_path(base_dir: str, candidate: str) -> str:
    base = Path(base_dir).resolve()
    target = (base / candidate).resolve()
    if base not in target.parents and base != target:
        raise ValueError('Invalid path outside base dir')
    return str(target)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def downloads_start(request):
    """Start a background download using download_nd.py or route to NCBI importer.

    Request JSON:
    - url: source URL or share link (optional; script parses mail file as well)
    - outdir: output directory relative to a configured base (optional)
    - mail: path to mail.txt relative to base dir (optional; defaults to mail.txt)

    Response: { status: 'accepted', pid, log, cwd }
    """
    url = (request.data.get('url') or '').strip()
    rel_outdir = (request.data.get('outdir') or 'downloads').strip()
    rel_mail = (request.data.get('mail') or '').strip()
    folder_id_raw = request.data.get('folder_id')
    target_folder_id = None

    base_dir = getattr(settings, 'DOWNLOADS_BASE_DIR', os.path.join(settings.BASE_DIR, 'downloads'))
    os.makedirs(base_dir, exist_ok=True)

    try:
        outdir = _safe_abs_path(base_dir, rel_outdir)
    except ValueError:
        return Response({'detail': 'Invalid path'}, status=status.HTTP_400_BAD_REQUEST)

    os.makedirs(outdir, exist_ok=True)

    script_path = os.path.join(settings.BASE_DIR, 'download_nd.py')

    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = tempfile.NamedTemporaryFile(prefix='download_', suffix='.log', dir=log_dir, delete=False)
    log_file_path = log_file.name
    log_file.close()

    try:
        with open(log_file_path, 'a', encoding='utf-8', buffering=1) as lf_init:
            lf_init.write('[ND] Accepted\n')
            lf_init.write(f"[ND] Output: {outdir}\n")
            if rel_mail:
                lf_init.write(f"[ND] Mail param: {rel_mail}\n")
            elif url:
                lf_init.write(f"[ND] URL param: {url}\n")
            else:
                lf_init.write('[ND] Mail/URL params via body text\n')
    except Exception:
        pass

    # If URL is provided but mail file not specified, create a temp mail file
    mail_path = None
    if rel_mail:
        try:
            mail_path = _safe_abs_path(settings.BASE_DIR, rel_mail)
        except ValueError:
            return Response({'message': 'Invalid mail path'}, status=status.HTTP_400_BAD_REQUEST)
    elif url:
        temp_mail = tempfile.NamedTemporaryFile('w', prefix='mail_', suffix='.txt', dir=log_dir, delete=False)
        temp_mail.write(url + "\n")
        temp_mail.flush()
        temp_mail.close()
        mail_path = temp_mail.name

    # Auto-route: if URL looks like NCBI, forward to NCBI import API
    if url and _is_ncbi_url(url):
        # Start NCBI import in a background thread and immediately return log path
        from rest_framework.test import APIRequestFactory, force_authenticate

        def _run_ncbi_import_async(src_url: str, user_obj, log_path: str):
            try:
                with open(log_path, 'a', buffering=1) as lf:
                    lf.write(f"[NCBI] Start import: {src_url}\n")
                    factory = APIRequestFactory()
                    req = factory.post('/api/files/ncbi/import/', {'url': src_url}, format='json')
                    try:
                        force_authenticate(req, user=user_obj)
                    except Exception:
                        req.user = user_obj
                    try:
                        # inject env for ncbi_client to log progress and support cancellation
                        cancel_flag = f"{log_path}.cancel"
                        os.environ['PYTHONUNBUFFERED'] = os.environ.get('PYTHONUNBUFFERED', '1')
                        os.environ['NCBI_LOG_PATH'] = log_path
                        os.environ['NCBI_CANCEL_PATH'] = cancel_flag
                        # Import after setting env ensures ncbi_client sees the env
                        from file_upload.api_views import ncbi_import
                        resp = ncbi_import(req)
                        code = getattr(resp, 'status_code', 0)
                        data = getattr(resp, 'data', {})
                        lf.write(f"[NCBI] Status: {code}\n")
                        lf.write(f"[NCBI] Response: {data}\n")
                        lf.write("[NCBI] Completed 100%\n")
                    except Exception as exc:
                        lf.write(f"[NCBI] Error: {exc}\n")
                        lf.write("[NCBI] Completed 100%\n")
            except Exception:
                # Best-effort logging; avoid crashing the thread
                pass

        t = threading.Thread(target=_run_ncbi_import_async, args=(url, request.user, log_file_path), daemon=True)
        t.start()
        return Response({
            'status': 'accepted',
            'message': 'Submitted.',
            'provider': 'NCBI',
            'log': log_file_path,
        }, status=status.HTTP_202_ACCEPTED)

    def run_nd_task(mail_fp: str, out_dir: str, log_path: str, user_id: int | None, folder_id: int | None):
        lnd_path = getattr(settings, 'LND_PATH', os.environ.get('LND_PATH')) or '/home/mosserver/software/linuxnd'
        try:
            with open(log_path, 'a', encoding='utf-8', buffering=1) as lf:
                lf.write('[ND] Start\n')
                os.makedirs(out_dir, exist_ok=True)
                user = ''
                passwd = ''
                dirpath = ''
                try:
                    with open(mail_fp, 'r', encoding='utf-8', errors='ignore') as fi:
                        for line in fi:
                            s = line.strip()
                            if s.startswith('登录账号：'):
                                user = s[5:]
                            elif s.startswith('登录密码：'):
                                passwd = s[5:]
                            elif s.startswith('数据路径为：'):
                                dirpath = s[6:]
                except Exception as exc:
                    lf.write(f"[ND] ERROR: read mail failed: {exc}\n")
                    lf.write('[ND] Completed 100%\n')
                    return
                if dirpath.endswith('/'):
                    dirpath = dirpath[:-1]
                batch_dir = os.path.basename(dirpath) or 'batch'
                work_dir = os.path.join(out_dir, batch_dir)
                os.makedirs(work_dir, exist_ok=True)
                lf.write(f"[ND] Using lnd at {lnd_path}/lnd\n")
                lnd_bin = os.path.join(lnd_path, 'lnd')
                if not (os.path.exists(lnd_bin) and os.access(lnd_bin, os.X_OK)):
                    lf.write(f"[ND] ERROR: lnd not executable at {lnd_bin}\n")
                    lf.write('[ND] Completed 100%\n')
                    return
                try:
                    import subprocess
                    login_cmd = [lnd_bin, 'login', '-u', user, '-p', passwd]
                    lf.write(' '.join(login_cmd) + "\n")
                    try:
                        p = subprocess.run(login_cmd, cwd=work_dir, stdout=lf, stderr=lf, timeout=60)
                        lf.write(f"[ND] login rc={p.returncode}\n")
                        lf.write('progress: 15%\n')
                    except subprocess.TimeoutExpired:
                        lf.write('[ND] ERROR: login timeout\n')
                        lf.write('[ND] Completed 100%\n')
                        return
                    list_cmd = [lnd_bin, 'list', f"oss://{dirpath}"]
                    lf.write(' '.join(list_cmd) + "\n")
                    out = subprocess.run(list_cmd, cwd=work_dir, capture_output=True, timeout=120)
                    listing = ''
                    try:
                        listing = out.stdout.decode('utf-8', errors='ignore')
                    except Exception:
                        listing = ''
                    lf.write(f"[ND] list rc={out.returncode}\n")
                    with open(os.path.join(work_dir, 'file.list'), 'w', encoding='utf-8') as fl:
                        fl.write(listing)
                    lf.write('[ND] list fetched\n')
                    lf.write('progress: 20%\n')
                    files = []
                    md5s = ''
                    with open(os.path.join(work_dir, 'file.list'), 'r', encoding='utf-8', errors='ignore') as fl:
                        for ln in fl:
                            cols = ln.strip().split('\t')
                            last = cols[-1]
                            if last.endswith('fastq.gz') or last.endswith('fq.gz'):
                                if last.startswith('/'):
                                    last = last[1:]
                                files.append(last)
                            if ('md5' in last or 'MD5' in last) and last.endswith('txt'):
                                md5s = last
                    if not md5s:
                        lf.write('[ND] not find MD5 file, download with no MD5 checking\n')
                    else:
                        lf.write(f"[ND] found MD5 file: {md5s}\n")
                        try:
                            subprocess.run([lnd_bin, 'cp', f"oss://{dirpath}{md5s}", '.' ], cwd=work_dir, stdout=lf, stderr=lf, timeout=300)
                        except subprocess.TimeoutExpired:
                            lf.write('[ND] WARN: md5 copy timeout, continue\n')
                    if not files:
                        lf.write('[ND] WARN: no fastq/fq files found in list\n')
                    target_folder = None
                    if user_id:
                        try:
                            from django.contrib.auth import get_user_model
                            from file_upload.models import File as FileModel, Folder as FolderModel
                            U = get_user_model()
                            user_obj = U.objects.get(id=user_id)
                            if folder_id:
                                try:
                                    target_folder = FolderModel.objects.get(id=folder_id, user=user_obj)
                                except Exception:
                                    target_folder, _ = FolderModel.objects.get_or_create(user=user_obj, parent=None, name='Download')
                            else:
                                target_folder, _ = FolderModel.objects.get_or_create(user=user_obj, parent=None, name='Download')
                        except Exception as exc:
                            target_folder = None
                    for f in files:
                        subdir = os.path.dirname(f)
                        if subdir:
                            os.makedirs(os.path.join(work_dir, subdir), exist_ok=True)
                        lf.write(f"lnd cp oss://{dirpath}/{f} {subdir}\n")
                        try:
                            subprocess.run([lnd_bin, 'cp', f"oss://{dirpath}/{f}", subdir or '.' ], cwd=work_dir, stdout=lf, stderr=lf, timeout=3600)
                        except subprocess.TimeoutExpired:
                            lf.write(f"[ND] ERROR: timeout copying {f}\n")
                        lf.write(f"{f} is OK\n")
                        if user_id and target_folder:
                            try:
                                from django.core.files import File as DjangoFile
                                from django.contrib.auth import get_user_model
                                from file_upload.models import File as FileModel
                                U = get_user_model()
                                user_obj = U.objects.get(id=user_id)
                                abs_path = os.path.join(work_dir, f)
                                base_name = os.path.basename(f)
                                if os.path.exists(abs_path):
                                    exists = FileModel.objects.filter(user=user_obj, parent_folder=target_folder, original_filename=base_name).exists()
                                    if not exists:
                                        with open(abs_path, 'rb') as fh:
                                            djf = DjangoFile(fh, name=base_name)
                                            rec = FileModel(user=user_obj, upload_method='download', parent_folder=target_folder, original_filename=base_name, title=base_name, access_level='Internal', document_type='Dataset')
                                            rec.file = djf
                                            rec.save()
                                        lf.write(f"[ND] registered {base_name}\n")
                            except Exception as exc:
                                lf.write(f"[ND] ERROR: register failed for {f}: {exc}\n")
                    lf.write('[ND] Completed 100%\n')
                except Exception as exc:
                    lf.write(f"[ND] ERROR: {exc}\n")
                    lf.write('[ND] Completed 100%\n')
        except Exception:
            try:
                with open(log_path, 'a', encoding='utf-8', buffering=1) as lf:
                    lf.write('[ND] ERROR: unexpected failure\n')
                    lf.write('[ND] Completed 100%\n')
            except Exception:
                pass

    if not mail_path:
        default_mail = os.path.join(settings.BASE_DIR, 'mail.txt')
        if os.path.exists(default_mail):
            mail_path = default_mail
        else:
            mt = (request.data.get('mail_text') or '').strip()
            if mt:
                tmpm = tempfile.NamedTemporaryFile('w', prefix='mail_', suffix='.txt', dir=log_dir, delete=False)
                tmpm.write(mt + "\n")
                tmpm.flush()
                tmpm.close()
                mail_path = tmpm.name
            else:
                return Response({'message': 'mail not provided'}, status=status.HTTP_400_BAD_REQUEST)
    if folder_id_raw is not None:
        try:
            fid = int(folder_id_raw)
            from file_upload.models import Folder as FolderModel
            q = FolderModel.objects.filter(id=fid, user=request.user)
            if q.exists():
                target_folder_id = fid
        except Exception:
            target_folder_id = None
    try:
        with open(log_file_path, 'a', encoding='utf-8', buffering=1) as lf_init2:
            lf_init2.write(f"[ND] Thread scheduling with mail: {mail_path}\n")
            lf_init2.write(f"[ND] Target folder id: {target_folder_id if target_folder_id else 'auto'}\n")
    except Exception:
        pass
    t = threading.Thread(target=run_nd_task, args=(mail_path, outdir, log_file_path, getattr(request.user, 'id', None), target_folder_id), daemon=True)
    t.start()
    try:
        with open(log_file_path, 'a', encoding='utf-8', buffering=1) as lf_init3:
            lf_init3.write("[ND] Thread started\n")
    except Exception:
        pass
    return Response({
        'status': 'accepted',
        'message': 'Submitted.',
        'provider': 'Huawei/NovoCloud',
        'log': log_file_path,
        'cwd': outdir,
    }, status=status.HTTP_202_ACCEPTED)


def _is_ncbi_url(url: str) -> bool:
    u = (url or '').lower()
    if not u:
        return False
    return ('ncbi.nlm.nih.gov' in u) or ('sra-' in u and 'ncbi' in u) or ('ebi.ac.uk' in u) or ('ena' in u)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def downloads_status(request):
    """Return tail of a log file for progress polling.

    Query params:
      - log: absolute path of log file under BASE_DIR/logs
      - n: number of lines (default 50)
    """
    log = (request.query_params.get('log') or '').strip()
    n = int(request.query_params.get('n') or '50')
    if n <= 0:
        n = 50
    base_logs = os.path.join(settings.BASE_DIR, 'logs')
    if not log:
        return Response({'message': 'log parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    # security: only allow files inside logs dir
    log_path = os.path.abspath(log)
    if not log_path.startswith(os.path.abspath(base_logs)):
        return Response({'message': 'invalid log path'}, status=status.HTTP_400_BAD_REQUEST)
    if not os.path.exists(log_path):
        return Response({'message': 'log not found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        # read last n lines efficiently
        lines = _tail_lines(log_path, n)
        # basic progress heuristics + speed/ETA estimation
        text = '\n'.join(lines)
        heuristic_percent = _heuristic_progress(text)
        downloaded_bytes, total_bytes, speed_bps, eta_seconds = _estimate_stats(lines)
        # If we have byte counts, compute percent from them to improve accuracy
        percent_from_bytes = 0
        try:
            if total_bytes and downloaded_bytes:
                percent_from_bytes = int((downloaded_bytes * 100) / total_bytes)
        except Exception:
            percent_from_bytes = 0
        # Choose the best available percent
        percent = heuristic_percent
        if percent == 0 and percent_from_bytes > 0:
            percent = percent_from_bytes
        # Clamp percent to [0, 99] unless total is complete
        if percent < 0:
            percent = 0
        if percent > 100:
            percent = 100
        if (total_bytes and downloaded_bytes and downloaded_bytes < total_bytes) and percent >= 100:
            percent = 99
        try:
            if 'Completed 100%' in text:
                percent = 100
        except Exception:
            pass
        return Response({
            'lines': lines,
            'text': text,
            'percent': percent,
            'downloaded_bytes': downloaded_bytes,
            'total_bytes': total_bytes,
            'speed_bps': speed_bps,
            'eta_seconds': eta_seconds,
        })
    except Exception as exc:
        return Response({'message': f'failed to read log: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _tail_lines(path: str, n: int):
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 1024
            data = b''
            while size > 0 and data.count(b'\n') <= n:
                read_size = min(block, size)
                f.seek(size - read_size)
                data = f.read(read_size) + data
                size -= read_size
            lines = data.splitlines()[-n:]
            return [smart_str(l) for l in lines]
    except Exception:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().splitlines()[-n:]


def _heuristic_progress(text: str) -> int:
    """Heuristically infer overall percent from mixed logs.

    Supports:
    - Huawei obsutil and lnd commands (count commands vs. OK lines)
    - Generic percent hints like "progress: 35.5%" or "35%" anywhere in text
    - Falls back to 0 if nothing useful is present
    """
    total = 0
    done = 0
    for line in text.splitlines():
        if 'lnd cp oss://' in line or 'obsutil share-cp' in line:
            total += 1
        if line.strip().endswith('is OK') or ('already found' in line):
            done += 1

    import re
    if total > 0:
        current_pct = None
        lines = text.splitlines()
        for ln in reversed(lines):
            if ('MB/' in ln) or ('GB/' in ln) or ('fastq.gz' in ln) or ('fq.gz' in ln):
                m = re.search(r"(\d{1,3})(?:\.\d+)?\s*%", ln)
                if m:
                    try:
                        current_pct = int(float(m.group(1)))
                        break
                    except Exception:
                        current_pct = None
        try:
            base = int((done * 100) / total)
        except Exception:
            base = 0
        if current_pct is not None:
            try:
                p = int(((done + (current_pct / 100.0)) * 100) / total)
            except Exception:
                p = base
        else:
            p = base
        if done >= total and total > 0:
            return 100
        return max(0, min(p, 99))

    percents = []
    for m in re.finditer(r"(\d{1,3})(?:\.\d+)?\s*%", text, re.IGNORECASE):
        try:
            percents.append(int(m.group(1)))
        except Exception:
            pass
    if percents:
        p = percents[-1]
        return max(0, min(p, 100))
    return 0


def _estimate_stats(lines: list[str]):
    """Estimate downloaded bytes, total bytes, speed(bps) and ETA from log tail.

    - Recognizes lines like "Content-Length: N bytes" and "Progress X%" or "Downloaded M MB".
    - Returns a tuple: (downloaded_bytes, total_bytes, speed_bps, eta_seconds)
    """
    import re
    import datetime
    total = None
    downloaded = 0
    # parse total bytes
    for ln in lines:
        m = re.search(r"Content-Length:\s*(\d+)\s*bytes", ln)
        if m:
            try:
                total = int(m.group(1))
                break
            except Exception:
                pass
    # find last progress indication
    last_ts = None
    last_prog = None
    last_bytes = None
    ts_prog = []
    for ln in lines:
        # timestamp at beginning: "YYYY-mm-dd HH:MM:SS [NCBI] ..."
        tm = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*", ln)
        ts = None
        if tm:
            try:
                ts = datetime.datetime.strptime(tm.group(1), "%Y-%m-%d %H:%M:%S")
            except Exception:
                ts = None
        # progress percent like "Progress 35%", "progress: 35.5%" or "... 35% complete"
        pm = re.search(r"(Progress\s+|progress:\s*|)\s*(\d{1,3})(?:\.\d+)?%", ln)
        if pm:
            try:
                # number may be in group(1) or group(2) depending on regex branch
                p_str = pm.group(2) if pm.lastindex and pm.lastindex >= 2 else pm.group(1)
                p = int(p_str)
                if total:
                    b = int((p * total) / 100)
                    ts_prog.append((ts, b))
                    last_prog = p
                    last_bytes = b
                else:
                    last_prog = p
            except Exception:
                pass
        # bytes hints like "Downloaded 123 MB" or "123.4 MB/s"
        dm = re.search(r"Downloaded\s+(\d+)(?:\.\d+)?\s+(KB|MB|GB)", ln)
        if dm:
            try:
                val = float(dm.group(1))
                unit = (dm.group(2) or 'MB').upper()
                mult = 1024
                if unit == 'KB':
                    b = int(val * mult)
                elif unit == 'MB':
                    b = int(val * mult * mult)
                else:  # GB
                    b = int(val * mult * mult * mult)
                ts_prog.append((ts, b))
                last_bytes = b
            except Exception:
                pass
        # speed lines like "Average Speed: 12.3 MB/s" or "Speed 1234 KB/s"
        sm = re.search(r"(Speed|Average Speed)[:\s]+(\d+(?:\.\d+)?)\s*(KB|MB|GB)/s", ln, re.IGNORECASE)
        if sm:
            try:
                sval = float(sm.group(2))
                sunit = (sm.group(3) or 'MB').upper()
                mult = 1024
                if sunit == 'KB':
                    sbytes = int(sval * mult)
                elif sunit == 'MB':
                    sbytes = int(sval * mult * mult)
                else:  # GB
                    sbytes = int(sval * mult * mult * mult)
                # prefer the parsed speed if we cannot compute later
                speed = sbytes
            except Exception:
                pass
        if ts:
            last_ts = ts
    # infer downloaded
    if last_bytes is not None:
        downloaded = last_bytes
    elif last_prog is not None and total:
        downloaded = int((last_prog * total) / 100)
    # compute speed using last two points (prefer last 3 and average for stability)
    speed = None
    eta = None
    if len(ts_prog) >= 2:
        pairs = ts_prog[-3:] if len(ts_prog) >= 3 else ts_prog[-2:]
        deltas = []
        for i in range(1, len(pairs)):
            t1, b1 = pairs[i-1]
            t2, b2 = pairs[i]
            if t1 and t2 and (t2 > t1):
                dt = (t2 - t1).total_seconds()
                db = max(0, b2 - b1)
                if dt > 0:
                    deltas.append(db / dt)
        if deltas:
            speed = int(sum(deltas) / len(deltas))
    # ETA
    if total and downloaded and (total > downloaded):
        if speed and speed > 0:
            eta = int((total - downloaded) / speed)
        else:
            eta = None
    return downloaded or 0, total or 0, speed or 0, eta or None


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def downloads_cancel(request):
    """Cancel a running download.

    Request JSON:
      - log: absolute path to the log file under BASE_DIR/logs (optional)
      - pid: process id to terminate for Huawei/NovoCloud (optional)
    """
    log = (request.data.get('log') or '').strip()
    pid_val = request.data.get('pid')
    base_logs = os.path.join(settings.BASE_DIR, 'logs')
    messages = []
    canceled = False

    # Try kill process if pid provided
    if pid_val is not None:
        try:
            pid = int(pid_val)
            os.kill(pid, signal.SIGTERM)
            canceled = True
            messages.append(f'PID {pid} terminated')
        except Exception as exc:
            messages.append(f'Failed to terminate PID: {exc}')

    # Create cancel flag file for NCBI-threaded downloads
    if log:
        log_path = os.path.abspath(log)
        if not log_path.startswith(os.path.abspath(base_logs)):
            return Response({'message': 'invalid log path'}, status=status.HTTP_400_BAD_REQUEST)
        cancel_path = f"{log_path}.cancel"
        try:
            # touch cancel flag
            with open(cancel_path, 'a'):
                pass
            canceled = True
            # best-effort write into log
            try:
                with open(log_path, 'a', buffering=1) as lf:
                    lf.write('[Cancel] User requested cancellation\n')
            except Exception:
                pass
        except Exception as exc:
            messages.append(f'Failed to set cancel flag: {exc}')

    status_text = 'ok' if canceled else 'noop'
    return Response({'status': status_text, 'message': '; '.join(messages)}, status=status.HTTP_200_OK)
