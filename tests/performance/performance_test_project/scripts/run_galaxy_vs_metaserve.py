import os
import sys
import json
import csv
import time
import subprocess
import glob
from datetime import datetime

scripts_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(scripts_dir)
sys.path.append(os.path.join(project_dir, "configs"))
from test_config import RESULTS_DIR, REPORTS_DIR


def run_py(script_name, *, env=None):
    script_path = os.path.join(scripts_dir, script_name)
    p = subprocess.run(
        [sys.executable, script_path],
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        env=env,
    )
    if p.returncode != 0:
        raise RuntimeError(f"{script_name} failed: {p.returncode}\n{p.stdout}\n{p.stderr}")
    last = ""
    for line in (p.stdout or "").splitlines()[::-1]:
        line = line.strip()
        if line:
            last = line
            break
    try:
        return json.loads(last)
    except Exception:
        raise RuntimeError(f"{script_name} did not output json. stdout tail: {last}")


def docker_compose(*args, env=None):
    compose_path = os.path.join(project_dir, "docker-compose.galaxy.yml")
    cmd = ["docker", "compose", "-f", compose_path, *args]
    p = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"docker compose failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p.stdout


def wait_galaxy_ready(base_url, api_key, *, max_wait_s=300):
    import requests

    base_url = base_url.rstrip("/")
    url = f"{base_url}/api/version"
    headers = {"x-api-key": api_key} if api_key else {}
    t0 = time.time()
    last = None
    while True:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            last = r.status_code
            if r.status_code == 200:
                return True
        except Exception:
            pass
        if (time.time() - t0) > max_wait_s:
            return False
        time.sleep(1)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(v):
    try:
        return float(v)
    except Exception:
        return None


def pick_latest_csv(pattern):
    paths = sorted(glob.glob(os.path.join(RESULTS_DIR, pattern)))
    return paths[-1] if paths else None


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    start_galaxy = os.environ.get("START_GALAXY_DOCKER", "1").strip() not in ("0", "false", "False")
    stop_galaxy = os.environ.get("STOP_GALAXY_DOCKER", "0").strip() in ("1", "true", "True")

    galaxy_url = os.environ.get("GALAXY_URL", "http://localhost:8080").rstrip("/")
    galaxy_api_key = os.environ.get("GALAXY_API_KEY", os.environ.get("GALAXY_MASTER_API_KEY", "bench-galaxy-key"))

    if start_galaxy:
        docker_compose("up", "-d")
        ok = wait_galaxy_ready(galaxy_url, galaxy_api_key, max_wait_s=600)
        if not ok:
            raise RuntimeError(f"Galaxy not ready: {galaxy_url}")

    env = dict(os.environ)

    metaserve_csv = os.environ.get("METASERVE_CSV", "").strip() or None
    galaxy_csv = os.environ.get("GALAXY_CSV", "").strip() or None

    if not metaserve_csv:
        try:
            metaserve_out = run_py("galaxy_benchmark_mvp.py", env=env)
            metaserve_csv = metaserve_out["csv"]
        except Exception:
            metaserve_csv = pick_latest_csv("galaxy_benchmark_mvp_*.csv")

    if not galaxy_csv:
        try:
            galaxy_out = run_py("galaxy_api_benchmark.py", env=env)
            galaxy_csv = galaxy_out["csv"]
        except Exception:
            galaxy_csv = pick_latest_csv("galaxy_api_benchmark_*.csv")

    if not metaserve_csv:
        raise RuntimeError("No MetaServe csv available (run failed and no results found)")
    if not galaxy_csv:
        raise RuntimeError("No Galaxy csv available (run failed and no results found)")

    metaserve_rows = load_csv(metaserve_csv)
    galaxy_rows = load_csv(galaxy_csv)

    summary_rows = []
    for r in metaserve_rows:
        task_key = f"{r.get('task')}:{r.get('dataset_label')}"
        summary_rows.append({
            "system": "metaserve",
            "task": task_key,
            "completion_time_ms": to_float(r.get("completion_time_ms")),
            "source_csv": os.path.basename(metaserve_csv),
        })
    for r in galaxy_rows:
        summary_rows.append({
            "system": "galaxy",
            "task": r.get("task"),
            "completion_time_ms": to_float(r.get("completion_time_ms")),
            "source_csv": os.path.basename(galaxy_csv),
        })

    summary_csv = os.path.join(REPORTS_DIR, f"galaxy_vs_metaserve_summary_{ts}.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["system", "task", "completion_time_ms", "source_csv"])
        w.writeheader()
        for r in summary_rows:
            w.writerow(r)

    import matplotlib.pyplot as plt

    def plot_one(ax, title, rows, *, max_bars=18):
        items = [(r["task"], r["completion_time_ms"]) for r in rows if r["completion_time_ms"] is not None]
        items = sorted(items, key=lambda x: (x[1] is None, x[1] if x[1] is not None else 0))
        items = items[:max_bars]
        labels = [k for k, _ in items]
        vals = [v for _, v in items]
        ax.barh(labels, vals)
        ax.set_title(title)
        ax.set_xlabel("completion time (ms)")
        ax.grid(True, axis="x", linestyle="--", linewidth=0.5, alpha=0.5)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    plot_one(axes[0], "MetaServe", [r for r in summary_rows if r["system"] == "metaserve"])
    plot_one(axes[1], "Galaxy", [r for r in summary_rows if r["system"] == "galaxy"])
    fig.tight_layout()

    png_path = os.path.join(REPORTS_DIR, f"galaxy_vs_metaserve_{ts}.png")
    pdf_path = os.path.join(REPORTS_DIR, f"galaxy_vs_metaserve_{ts}.pdf")
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")

    if stop_galaxy and start_galaxy:
        docker_compose("down")

    print(json.dumps({
        "summary_csv": summary_csv,
        "png": png_path,
        "pdf": pdf_path,
        "metaserve_csv": metaserve_csv,
        "galaxy_csv": galaxy_csv,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
