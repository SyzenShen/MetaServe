import os
import sys
import time
import json
import csv
from datetime import datetime
import requests

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(scripts_dir)
from utils import TestLogger, AuthManager, ResultSaver
sys.path.append(os.path.join(os.path.dirname(scripts_dir), "configs"))
from test_config import API_BASE_URL, TEST_USERS, RESULTS_DIR


def now_iso():
    return datetime.now().isoformat()


def ensure_login(auth):
    user = TEST_USERS[0]
    email = user["email"]
    password = user["password"]
    if not auth.get_token(email):
        auth.register_user(email, password)
        auth.login_user(email, password)
    return email


def get_headers(auth, email):
    return auth.get_auth_headers(email)


def run_search(session, headers, params):
    t0 = time.time()
    r = session.get(f"{API_BASE_URL}/files/search/", params=params, headers=headers, timeout=60)
    dt = (time.time() - t0) * 1000.0
    ok = r.status_code == 200
    cnt = 0
    if ok:
        try:
            cnt = len(r.json().get("results", []))
        except Exception:
            ok = False
    return ok, dt, cnt, r.status_code


def run_manifest(session, headers, params):
    t0 = time.time()
    r = session.get(f"{API_BASE_URL}/files/manifest/", params=params, headers=headers, timeout=120)
    dt = (time.time() - t0) * 1000.0
    ok = r.status_code == 200
    lines = 0
    if ok:
        lines = len(r.text.strip().splitlines()) if r.text else 0
    return ok, dt, lines, r.status_code


def main():
    logger = TestLogger("GalaxyBenchmarkMVP")
    saver = ResultSaver()
    auth = AuthManager()
    email = ensure_login(auth)
    headers = get_headers(auth, email)
    session = requests.Session()

    tasks = []
    default_filters = [
        {"label": "baseline_none", "params": {}},
        {"label": "doc_dataset", "params": {"document_type": "Dataset"}},
        {"label": "doc_dataset_internal_rna", "params": {"document_type": "Dataset", "access_level": "Internal", "experiment_type": "RNA-seq"}},
    ]

    for spec in default_filters:
        label = spec["label"]
        params = dict(spec["params"])
        params.setdefault("page_size", "20")
        ok_s, q_ms, result_cnt, code_s = run_search(session, headers, params)
        steps = max(1, len([k for k, v in params.items() if k in ("document_type", "access_level", "experiment_type", "organism", "project") and v]))
        tasks.append({
            "task": "search",
            "dataset_label": label,
            "filters_count": steps,
            "filters": json.dumps(spec["params"], ensure_ascii=False),
            "completion_time_ms": round(q_ms, 2),
            "query_latency_ms": round(q_ms, 2),
            "result_items": result_cnt,
            "status": "success" if ok_s else "fail",
            "http_status": code_s,
            "timestamp": now_iso(),
            "user_actions": steps
        })
        ok_m, m_ms, line_cnt, code_m = run_manifest(session, headers, spec["params"])
        tasks.append({
            "task": "manifest",
            "dataset_label": label,
            "filters_count": steps,
            "filters": json.dumps(spec["params"], ensure_ascii=False),
            "completion_time_ms": round(m_ms, 2),
            "manifest_generation_ms": round(m_ms, 2),
            "lines": line_cnt,
            "status": "success" if ok_m else "fail",
            "http_status": code_m,
            "timestamp": now_iso(),
            "user_actions": steps
        })

    csv_path = os.path.join(RESULTS_DIR, f"galaxy_benchmark_mvp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    fieldnames = [
        "task",
        "dataset_label",
        "filters_count",
        "filters",
        "completion_time_ms",
        "query_latency_ms",
        "manifest_generation_ms",
        "result_items",
        "lines",
        "status",
        "http_status",
        "timestamp",
        "user_actions",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in tasks:
            writer.writerow(row)
    logger.info(f"CSV saved: {csv_path}")
    saver.save_test_result("galaxy_benchmark_mvp", {"rows": tasks, "csv": csv_path})
    print(json.dumps({"csv": csv_path, "count": len(tasks)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

