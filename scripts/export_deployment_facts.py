import os
import sys
import json
import csv
import shutil
import platform
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
sys.path.append(PROJ)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "file_project.settings")

def try_import_psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None

def docker_version(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True).strip()
        return out
    except Exception:
        return "unknown"

def init_django():
    try:
        import django
        django.setup()
        return True
    except Exception:
        return False

def db_info():
    try:
        from django.conf import settings
        from django.db import connection
        engine = settings.DATABASES["default"]["ENGINE"]
        backend = "sqlite" if "sqlite" in engine else ("postgresql" if "postgresql" in engine or "psycopg2" in engine else engine)
        version = "unknown"
        with connection.cursor() as cur:
            if backend == "sqlite":
                cur.execute("select sqlite_version()")
                version = cur.fetchone()[0]
            elif backend == "postgresql":
                cur.execute("show server_version")
                version = cur.fetchone()[0]
        return backend, version
    except Exception:
        return "unknown", "unknown"

def counts():
    try:
        from django.conf import settings
        from django.contrib.auth import get_user_model
        from file_upload.models import File
        User = get_user_model()
        users = User.objects.count()
        files = File.objects.count()
        total_bytes = sum(f.file_size for f in File.objects.all())
        media_root = getattr(settings, "MEDIA_ROOT", None)
        return users, files, total_bytes, media_root
    except Exception:
        return None, None, None, None

def disk_usage(path):
    try:
        du = shutil.disk_usage(path)
        return du.total, du.used, du.free
    except Exception:
        return None, None, None

def main():
    psutil = try_import_psutil()
    init_django()
    backend, db_ver = db_info()
    users, files, total_bytes, media_root = counts()
    os_name = platform.system()
    os_release = platform.release()
    cpu = platform.processor() or "unknown"
    ram_gb = None
    if psutil:
        try:
            ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
        except Exception:
            ram_gb = None
    docker_ver = docker_version("docker --version")
    compose_ver = docker_version("docker compose version")
    media_total, media_used, media_free = (None, None, None)
    if media_root:
        media_total, media_used, media_free = disk_usage(media_root)
    facts = {
        "timestamp": datetime.now().isoformat(),
        "os": f"{os_name} {os_release}",
        "cpu": cpu,
        "ram_gb": ram_gb,
        "docker_version": docker_ver,
        "docker_compose_version": compose_ver,
        "db_backend": backend,
        "db_version": db_ver,
        "media_root": media_root,
        "media_total_bytes": media_total,
        "media_used_bytes": media_used,
        "media_free_bytes": media_free,
        "user_count": users,
        "file_count": files,
        "total_file_bytes": total_bytes,
        "single_node": "unknown",
        "shared_storage_with_viewer": "unknown",
        "query_log_timeframe": "unknown"
    }
    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "deployment_facts.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=2, ensure_ascii=False)
    csv_path = os.path.join(out_dir, "deployment_facts.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for k, v in facts.items():
            w.writerow([k, v])
    print(json.dumps({"json": json_path, "csv": csv_path}, ensure_ascii=False))

if __name__ == "__main__":
    main()

