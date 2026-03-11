import os
import sys
import time
import json
import csv
from datetime import datetime
from urllib.parse import urljoin

import requests

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(scripts_dir)
from utils import TestLogger, ResultSaver
sys.path.append(os.path.join(os.path.dirname(scripts_dir), "configs"))
from test_config import RESULTS_DIR


def now_iso():
    return datetime.now().isoformat()


def normalize_base_url(v):
    v = (v or "").strip()
    if not v:
        return "http://localhost:8080"
    return v[:-1] if v.endswith("/") else v


def make_headers(api_key):
    api_key = (api_key or "").strip()
    if not api_key:
        return {}
    return {"x-api-key": api_key}


def request_with_timing(session, method, url, *, headers=None, params=None, json_body=None, data=None, files=None, timeout=60):
    t0 = time.time()
    r = session.request(method, url, headers=headers, params=params, json=json_body, data=data, files=files, timeout=timeout)
    dt_ms = (time.time() - t0) * 1000.0
    return r, dt_ms


def wait_ready(session, base_url, headers, *, max_wait_s=300):
    url = urljoin(f"{base_url}/", "api/version")
    t0 = time.time()
    last_status = None
    while True:
        try:
            r, _ = request_with_timing(session, "GET", url, headers=headers, timeout=10)
            last_status = r.status_code
            if r.status_code == 200:
                return True, (time.time() - t0) * 1000.0, r
        except Exception:
            pass
        if (time.time() - t0) > max_wait_s:
            return False, (time.time() - t0) * 1000.0, last_status
        time.sleep(1)


def get_current_user(session, base_url, headers):
    url = urljoin(f"{base_url}/", "api/users/current")
    r, ms = request_with_timing(session, "GET", url, headers=headers, timeout=30)
    user_id = None
    if r.status_code == 200:
        try:
            user_id = r.json().get("id")
        except Exception:
            user_id = None
    return r, ms, user_id


def create_user_admin(session, base_url, master_headers, *, email, username, password):
    url = urljoin(f"{base_url}/", "api/users")
    payload = {"email": email, "username": username, "password": password}
    r, ms = request_with_timing(session, "POST", url, headers=master_headers, json_body=payload, timeout=60)
    user_id = None
    if r.status_code in (200, 201):
        try:
            user_id = r.json().get("id")
        except Exception:
            user_id = None
    return r, ms, user_id


def list_users_admin(session, base_url, master_headers, *, email=None):
    url = urljoin(f"{base_url}/", "api/users")
    tried = []
    if email:
        for params in ({"f_email": email}, {"email": email}):
            tried.append(params)
            r, ms = request_with_timing(session, "GET", url, headers=master_headers, params=params, timeout=60)
            if r.status_code == 200:
                try:
                    return r, ms, r.json(), params
                except Exception:
                    pass
    r, ms = request_with_timing(session, "GET", url, headers=master_headers, timeout=60)
    if r.status_code == 200:
        try:
            return r, ms, r.json(), None
        except Exception:
            return r, ms, None, None
    return r, ms, None, tried[-1] if tried else None


def pick_user_id_by_email(users_payload, email):
    if not isinstance(users_payload, list):
        return None
    for u in users_payload:
        if isinstance(u, dict) and u.get("email") == email:
            return u.get("id")
    return None


def create_api_key_admin(session, base_url, master_headers, user_id):
    url = urljoin(f"{base_url}/", f"api/users/{user_id}/api_key")
    r, ms = request_with_timing(session, "POST", url, headers=master_headers, timeout=60)
    api_key = None
    if r.status_code == 200:
        try:
            payload = r.json()
            if isinstance(payload, dict):
                api_key = payload.get("api_key")
            elif isinstance(payload, str):
                api_key = payload
        except Exception:
            api_key = None
    return r, ms, api_key


def _resp_text(r, limit=2000):
    try:
        return (r.text or "")[:limit]
    except Exception:
        return ""


def _has_err_fragment(r, fragment):
    t = _resp_text(r, limit=5000)
    return fragment in t


def ensure_user_api_key(session, base_url, *, user_api_key=None, master_api_key=None, email=None, username=None, password=None):
    if user_api_key:
        headers = make_headers(user_api_key)
        r, ms, user_id = get_current_user(session, base_url, headers)
        if r.status_code == 200 and user_id:
            return True, ms, user_api_key, {"mode": "provided_user_key", "user_id": user_id}

    if not master_api_key:
        return False, 0.0, None, {"mode": "missing_master_key"}

    master_headers = make_headers(master_api_key)
    if not email:
        email = "bench@example.com"
    if not username:
        username = email.split("@")[0] if "@" in email else "bench"
    if not password:
        password = "BenchPass123!"

    username_candidates = [
        username,
        f"{username}_{int(time.time())}",
        f"{username}_{datetime.now().strftime('%H%M%S')}",
    ]
    r_create = None
    ms_create = 0.0
    user_id = None
    for uname in username_candidates:
        r_try, ms_try, created_user_id = create_user_admin(session, base_url, master_headers, email=email, username=uname, password=password)
        r_create = r_try
        ms_create += ms_try or 0.0
        if created_user_id:
            user_id = created_user_id
            break
        if r_try.status_code == 400 and _has_err_fragment(r_try, "Public name is taken"):
            continue
        if r_try.status_code == 400 and (_has_err_fragment(r_try, "email") or _has_err_fragment(r_try, "Email")):
            break
        break

    used_params = None
    ms_list = 0.0
    r_list = None
    users_payload = None
    if not user_id:
        r_list, ms_list, users_payload, used_params = list_users_admin(session, base_url, master_headers, email=email)
        user_id = pick_user_id_by_email(users_payload, email) if users_payload else None
        if not user_id:
            r_list_all, ms_list_all, users_payload_all, used_params_all = list_users_admin(session, base_url, master_headers, email=None)
            users_payload = users_payload_all
            r_list = r_list_all
            ms_list += ms_list_all or 0.0
            used_params = used_params_all
            user_id = pick_user_id_by_email(users_payload, email) if users_payload else None

    if not user_id:
        return False, (ms_create or 0.0) + (ms_list or 0.0), None, {
            "mode": "cannot_resolve_user",
            "email": email,
            "username": username,
            "create_status": getattr(r_create, "status_code", None),
            "create_body": _resp_text(r_create) if r_create is not None else None,
            "list_status": getattr(r_list, "status_code", None),
            "list_params": used_params,
            "list_body": (_resp_text(r_list) if r_list is not None else None),
        }

    r_key, ms_key, new_key = create_api_key_admin(session, base_url, master_headers, user_id)
    if not new_key:
        return False, (ms_create or 0.0) + (ms_key or 0.0), None, {
            "mode": "cannot_create_api_key",
            "user_id": user_id,
            "status": r_key.status_code,
            "body": (r_key.text or "")[:2000],
        }

    headers = make_headers(new_key)
    r_cur, ms_cur, cur_user_id = get_current_user(session, base_url, headers)
    if r_cur.status_code != 200 or not cur_user_id:
        return False, (ms_create or 0.0) + (ms_key or 0.0) + (ms_cur or 0.0), None, {
            "mode": "new_key_not_working",
            "user_id": user_id,
            "status": r_cur.status_code,
            "body": (r_cur.text or "")[:2000],
        }

    return True, (ms_create or 0.0) + (ms_key or 0.0) + (ms_cur or 0.0), new_key, {"mode": "provisioned", "user_id": cur_user_id}


def create_history(session, base_url, headers, name):
    url = urljoin(f"{base_url}/", "api/histories")
    payload = {"name": name}
    r, ms = request_with_timing(session, "POST", url, headers=headers, json_body=payload, timeout=60)
    history_id = None
    if r.status_code in (200, 201):
        try:
            history_id = r.json().get("id")
        except Exception:
            history_id = None
    return r, ms, history_id


def upload_text_dataset(session, base_url, headers, history_id, *, name="bench.txt", content="hello\n"):
    url = urljoin(f"{base_url}/", "api/tools")
    payload = {
        "history_id": history_id,
        "tool_id": "upload1",
        "inputs": {
            "files_0|type": "upload_dataset",
            "files_0|NAME": name,
            "files_0|url_paste": content,
        },
    }
    r, ms = request_with_timing(session, "POST", url, headers=headers, json_body=payload, timeout=120)
    dataset_id = None
    if r.status_code == 200:
        try:
            outputs = r.json().get("outputs", [])
            if outputs:
                dataset_id = outputs[0].get("id")
        except Exception:
            dataset_id = None
    return r, ms, dataset_id


def wait_dataset_ok(session, base_url, headers, dataset_id, *, max_wait_s=300):
    url = urljoin(f"{base_url}/", f"api/datasets/{dataset_id}")
    t0 = time.time()
    last_state = None
    last_status = None
    while True:
        r, _ = request_with_timing(session, "GET", url, headers=headers, timeout=30)
        last_status = r.status_code
        if r.status_code == 200:
            try:
                last_state = r.json().get("state")
            except Exception:
                last_state = None
            if last_state == "ok":
                return True, (time.time() - t0) * 1000.0, last_state, r
            if last_state in ("error", "failed", "deleted"):
                return False, (time.time() - t0) * 1000.0, last_state, r
        if (time.time() - t0) > max_wait_s:
            return False, (time.time() - t0) * 1000.0, last_state or last_status, r
        time.sleep(1)


def list_history_contents(session, base_url, headers, history_id):
    url = urljoin(f"{base_url}/", f"api/histories/{history_id}/contents")
    r, ms = request_with_timing(session, "GET", url, headers=headers, timeout=60)
    item_count = None
    if r.status_code == 200:
        try:
            item_count = len(r.json())
        except Exception:
            item_count = None
    return r, ms, item_count


def request_history_export(session, base_url, headers, history_id, *, gzip=True, include_hidden=False, include_deleted=False, max_wait_s=600):
    url = urljoin(f"{base_url}/", f"api/histories/{history_id}/exports")
    params = {
        "gzip": "true" if gzip else "false",
        "include_hidden": "true" if include_hidden else "false",
        "include_deleted": "true" if include_deleted else "false",
    }
    t0 = time.time()
    last_status = None
    last_body = None
    while True:
        r, _ = request_with_timing(session, "PUT", url, headers=headers, params=params, timeout=60)
        last_status = r.status_code
        try:
            last_body = r.json()
        except Exception:
            last_body = None
        if r.status_code == 200 and isinstance(last_body, dict) and last_body.get("download_url"):
            return True, (time.time() - t0) * 1000.0, last_body, r
        if r.status_code not in (200, 202):
            return False, (time.time() - t0) * 1000.0, last_body or r.text, r
        if (time.time() - t0) > max_wait_s:
            return False, (time.time() - t0) * 1000.0, last_body or last_status, r
        time.sleep(1)


def download_export(session, base_url, headers, download_url, out_path):
    if download_url.startswith("/"):
        url = urljoin(f"{base_url}/", download_url.lstrip("/"))
    else:
        url = download_url
    t0 = time.time()
    r = session.get(url, headers=headers, stream=True, timeout=600)
    if r.status_code != 200:
        return r, (time.time() - t0) * 1000.0, 0
    size = 0
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)
                size += len(chunk)
    return r, (time.time() - t0) * 1000.0, size


def main():
    logger = TestLogger("GalaxyApiBenchmark")
    saver = ResultSaver()
    session = requests.Session()

    base_url = normalize_base_url(os.environ.get("GALAXY_URL", "http://localhost:8080"))
    user_api_key = os.environ.get("GALAXY_API_KEY")
    master_api_key = os.environ.get("GALAXY_MASTER_API_KEY", "bench-galaxy-key")
    bench_email = os.environ.get("GALAXY_BENCH_EMAIL", os.environ.get("GALAXY_ADMIN_EMAIL", "bench@example.com"))
    bench_username = os.environ.get("GALAXY_BENCH_USERNAME", os.environ.get("GALAXY_ADMIN_USERNAME", "bench"))
    bench_password = os.environ.get("GALAXY_BENCH_PASSWORD", os.environ.get("GALAXY_ADMIN_PASSWORD", "BenchPass123!"))
    headers = {}
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    rows = []

    ok_ready, ready_ms, ready_meta = wait_ready(session, base_url, headers)
    rows.append({
        "system": "galaxy",
        "task": "wait_ready",
        "status": "success" if ok_ready else "fail",
        "http_status": getattr(ready_meta, "status_code", ready_meta),
        "completion_time_ms": round(ready_ms, 2),
        "detail": json.dumps({"base_url": base_url}, ensure_ascii=False),
        "timestamp": now_iso(),
    })
    if not ok_ready:
        csv_path = os.path.join(RESULTS_DIR, f"galaxy_api_benchmark_{run_id}.csv")
        fieldnames = ["system", "task", "status", "http_status", "completion_time_ms", "detail", "timestamp"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        saver.save_test_result("galaxy_api_benchmark", {"rows": rows, "csv": csv_path})
        raise SystemExit(f"Galaxy not ready: {base_url}")

    ok_key, key_ms, api_key, key_meta = ensure_user_api_key(
        session,
        base_url,
        user_api_key=user_api_key,
        master_api_key=master_api_key,
        email=bench_email,
        username=bench_username,
        password=bench_password,
    )
    rows.append({
        "system": "galaxy",
        "task": "ensure_user_api_key",
        "status": "success" if ok_key and api_key else "fail",
        "http_status": 200 if ok_key else 500,
        "completion_time_ms": round(key_ms, 2),
        "detail": json.dumps(key_meta, ensure_ascii=False),
        "timestamp": now_iso(),
    })
    if not ok_key or not api_key:
        csv_path = os.path.join(RESULTS_DIR, f"galaxy_api_benchmark_{run_id}.csv")
        fieldnames = ["system", "task", "status", "http_status", "completion_time_ms", "detail", "timestamp"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        saver.save_test_result("galaxy_api_benchmark", {"rows": rows, "csv": csv_path})
        raise SystemExit("Galaxy API key provisioning failed")

    headers = make_headers(api_key)

    history_name = f"bench_history_{run_id}"
    r_h, ms_h, history_id = create_history(session, base_url, headers, history_name)
    rows.append({
        "system": "galaxy",
        "task": "create_history",
        "status": "success" if history_id else "fail",
        "http_status": r_h.status_code,
        "completion_time_ms": round(ms_h, 2),
        "detail": json.dumps({"history_id": history_id, "name": history_name}, ensure_ascii=False),
        "timestamp": now_iso(),
    })
    if not history_id:
        csv_path = os.path.join(RESULTS_DIR, f"galaxy_api_benchmark_{run_id}.csv")
        fieldnames = ["system", "task", "status", "http_status", "completion_time_ms", "detail", "timestamp"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        saver.save_test_result("galaxy_api_benchmark", {"rows": rows, "csv": csv_path})
        raise SystemExit(f"create_history failed: {r_h.status_code} {r_h.text[:2000]}")

    r_u, ms_u, dataset_id = upload_text_dataset(session, base_url, headers, history_id)
    rows.append({
        "system": "galaxy",
        "task": "upload_text_dataset",
        "status": "success" if dataset_id else "fail",
        "http_status": r_u.status_code,
        "completion_time_ms": round(ms_u, 2),
        "detail": json.dumps({"dataset_id": dataset_id}, ensure_ascii=False),
        "timestamp": now_iso(),
    })

    if dataset_id:
        ok_d, ms_d, state_d, _ = wait_dataset_ok(session, base_url, headers, dataset_id)
        rows.append({
            "system": "galaxy",
            "task": "wait_dataset_ok",
            "status": "success" if ok_d else "fail",
            "http_status": 200 if ok_d else 500,
            "completion_time_ms": round(ms_d, 2),
            "detail": json.dumps({"dataset_id": dataset_id, "state": state_d}, ensure_ascii=False),
            "timestamp": now_iso(),
        })

    r_l, ms_l, item_count = list_history_contents(session, base_url, headers, history_id)
    rows.append({
        "system": "galaxy",
        "task": "list_history_contents",
        "status": "success" if r_l.status_code == 200 else "fail",
        "http_status": r_l.status_code,
        "completion_time_ms": round(ms_l, 2),
        "detail": json.dumps({"history_id": history_id, "items": item_count}, ensure_ascii=False),
        "timestamp": now_iso(),
    })

    ok_e, ms_e, export_body, _ = request_history_export(session, base_url, headers, history_id)
    download_url = export_body.get("download_url") if isinstance(export_body, dict) else None
    rows.append({
        "system": "galaxy",
        "task": "export_history_ready",
        "status": "success" if ok_e and download_url else "fail",
        "http_status": 200 if ok_e else 500,
        "completion_time_ms": round(ms_e, 2),
        "detail": json.dumps({"history_id": history_id, "download_url": download_url}, ensure_ascii=False),
        "timestamp": now_iso(),
    })

    export_size = 0
    if ok_e and download_url:
        out_path = os.path.join(RESULTS_DIR, f"galaxy_history_export_{run_id}.tgz")
        r_dl, ms_dl, export_size = download_export(session, base_url, headers, download_url, out_path)
        rows.append({
            "system": "galaxy",
            "task": "download_export",
            "status": "success" if r_dl.status_code == 200 else "fail",
            "http_status": r_dl.status_code,
            "completion_time_ms": round(ms_dl, 2),
            "detail": json.dumps({"path": out_path, "bytes": export_size}, ensure_ascii=False),
            "timestamp": now_iso(),
        })

    csv_path = os.path.join(RESULTS_DIR, f"galaxy_api_benchmark_{run_id}.csv")
    fieldnames = ["system", "task", "status", "http_status", "completion_time_ms", "detail", "timestamp"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    saver.save_test_result("galaxy_api_benchmark", {"rows": rows, "csv": csv_path})
    print(json.dumps({"csv": csv_path, "count": len(rows), "export_bytes": export_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
