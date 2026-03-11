import os
import sys
import time
import json
import csv
from datetime import datetime
import requests

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(scripts_dir)
from utils import TestLogger, AuthManager, ResultSaver, StatisticsCalculator
sys.path.append(os.path.join(os.path.dirname(scripts_dir), "configs"))
from test_config import API_BASE_URL, TEST_USERS, RESULTS_DIR


def ensure_login(auth):
    user = TEST_USERS[0]
    email = user["email"]
    password = user["password"]
    if not auth.get_token(email):
        auth.register_user(email, password)
        auth.login_user(email, password)
    return email


def run_once(session, headers, params):
    t0 = time.time()
    r = session.get(f"{API_BASE_URL}/files/search/", params=params, headers=headers, timeout=60)
    dt = (time.time() - t0) * 1000.0
    ok = r.status_code == 200
    return ok, dt, r.status_code


def main():
    logger = TestLogger("QueryLatencyBenchmark")
    saver = ResultSaver()
    auth = AuthManager()
    email = ensure_login(auth)
    headers = auth.get_auth_headers(email)
    session = requests.Session()

    datasets = {
        "small": [{"document_type": "Dataset"}],
        "medium": [{"document_type": "Dataset", "access_level": "Internal"}],
        "large": [{"document_type": "Dataset", "access_level": "Internal", "experiment_type": "RNA-seq"}],
    }
    filters_counts = [1, 3, 5]
    iterations = 7

    rows = []
    for size_label, base_filters_list in datasets.items():
        for base_filters in base_filters_list:
            for k in filters_counts:
                params = dict(base_filters)
                params.setdefault("page_size", "50")
                latencies = []
                successes = 0
                for _ in range(iterations):
                    ok, ms, code = run_once(session, headers, params)
                    if ok:
                        successes += 1
                        latencies.append(ms)
                avg = StatisticsCalculator.calculate_average(latencies)
                p50 = StatisticsCalculator.calculate_percentile(latencies, 50)
                p95 = StatisticsCalculator.calculate_percentile(latencies, 95)
                success_rate = StatisticsCalculator.calculate_success_rate(iterations, successes)
                rows.append({
                    "dataset_size": size_label,
                    "filters_count": k,
                    "filters": json.dumps(base_filters, ensure_ascii=False),
                    "iterations": iterations,
                    "success_rate": round(success_rate, 3),
                    "latency_avg_ms": round(avg, 2),
                    "latency_p50_ms": round(p50, 2),
                    "latency_p95_ms": round(p95, 2),
                    "timestamp": datetime.now().isoformat(),
                })
                logger.info(f"{size_label} k={k} success={successes}/{iterations} p50={p50:.2f} p95={p95:.2f}")

    csv_path = os.path.join(RESULTS_DIR, f"query_latency_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    fieldnames = ["dataset_size", "filters_count", "filters", "iterations", "success_rate", "latency_avg_ms", "latency_p50_ms", "latency_p95_ms", "timestamp"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    logger.info(f"CSV saved: {csv_path}")
    saver.save_test_result("query_latency_benchmark", {"rows": rows, "csv": csv_path})
    print(json.dumps({"csv": csv_path, "count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

