import os
import sys
import glob
import csv
from datetime import datetime

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(scripts_dir), "configs"))
from test_config import REPORTS_DIR, RESULTS_DIR


def load_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [r for r in reader]


def to_float(v):
    try:
        return float(v)
    except Exception:
        return None


def main():
    import matplotlib.pyplot as plt

    paths = sorted(glob.glob(os.path.join(RESULTS_DIR, "query_latency_benchmark_*.csv")))
    if not paths:
        raise SystemExit("no query_latency_benchmark_*.csv found")

    rows = []
    for p in paths:
        for r in load_rows(p):
            if "db_backend" not in r or not r["db_backend"]:
                r["db_backend"] = "sqlite"
            r["_source_csv"] = os.path.basename(p)
            rows.append(r)

    want_sizes = ["small", "medium", "large"]
    want_filters = [1, 3, 5]
    backends = sorted({r["db_backend"] for r in rows})

    def pick_latest(rows_in, size, backend, k):
        cand = [
            r
            for r in rows_in
            if r["dataset_size"] == size
            and r["db_backend"] == backend
            and int(r["filters_count"]) == int(k)
        ]
        return cand[-1] if cand else None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_csv = os.path.join(REPORTS_DIR, f"query_latency_summary_{ts}.csv")
    summary_fields = [
        "db_backend",
        "dataset_size",
        "filters_count",
        "success_rate",
        "latency_avg_ms",
        "latency_p50_ms",
        "latency_p95_ms",
        "source_csv",
    ]
    summary_rows = []
    for backend in backends:
        for size in want_sizes:
            for k in want_filters:
                r = pick_latest(rows, size, backend, k)
                if not r:
                    continue
                summary_rows.append({
                    "db_backend": backend,
                    "dataset_size": size,
                    "filters_count": int(k),
                    "success_rate": to_float(r.get("success_rate")),
                    "latency_avg_ms": to_float(r.get("latency_avg_ms")),
                    "latency_p50_ms": to_float(r.get("latency_p50_ms")),
                    "latency_p95_ms": to_float(r.get("latency_p95_ms")),
                    "source_csv": r.get("_source_csv"),
                })

    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=summary_fields)
        w.writeheader()
        for r in summary_rows:
            w.writerow(r)

    metrics = [
        ("p50", "latency_p50_ms", "p50 latency (ms)"),
        ("p95", "latency_p95_ms", "p95 latency (ms)"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(12, 6.8), sharey="row")
    for row_i, (_, metric_key, y_label) in enumerate(metrics):
        for col_i, size in enumerate(want_sizes):
            ax = axes[row_i][col_i]
            for backend in backends:
                xs = want_filters
                ys = []
                for k in want_filters:
                    r = pick_latest(rows, size, backend, k)
                    ys.append(to_float(r.get(metric_key)) if r else None)
                if any(v is not None for v in ys):
                    ax.plot(xs, ys, marker="o", linewidth=1.8, label=backend)
            ax.set_title(size if row_i == 0 else "")
            ax.set_xlabel("facet filters")
            ax.set_xticks(want_filters)
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
            if col_i == 0:
                ax.set_ylabel(y_label)

    handles, labels = axes[0][-1].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, bbox_to_anchor=(0.5, 1.02))

    fig.tight_layout()
    png_path = os.path.join(REPORTS_DIR, f"latency_vs_filters_backend_{ts}.png")
    pdf_path = os.path.join(REPORTS_DIR, f"latency_vs_filters_backend_{ts}.pdf")
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    print(summary_csv)
    print(png_path)
    print(pdf_path)


if __name__ == "__main__":
    main()
