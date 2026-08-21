#!/usr/bin/env python3
"""eva-task-runner — the async spine for Eva's background work (Phase 1 of the
"with hands" plan, docs/2026-07-22-EVA-WITH-HANDS-PLAN.md).

Letta tool calls are synchronous inside a turn: if a tool blocked on a multi-
minute job, the whole chat turn would hang and trip Letta's timeout. So a tool
like research_task submits a job here and returns immediately with a job_id;
this service does the slow work out-of-band, then reports back into Eva's
Letta conversation (and, later, an ntfy push) when it's done.

Job kind implemented so far: "research" (see executors/research.py). The
job-store/HTTP/dispatch machinery is generic — a "claude" kind (Phase 2, with
its HITL approval gate) plugs into the same EXECUTORS registry without
changing anything in this file except the state machine gaining
"pending_approval".

Loopback-only by design (127.0.0.1) — never put this on the LAN. Stdlib only
(plus `cryptography`, already on this host, for fcm.py's JWT signing), matching
eva-web/toolset_router.py's posture. Config via environment (see
~/.config/eva-task-runner/eva-task-runner.env):
  EVA_RUNNER_PORT            default 8286
  LETTA_HOST                 default http://localhost:8283
  EVA_AGENT_ID               Letta agent id results get injected into
  FCM_SERVICE_ACCOUNT_FILE   path to the Firebase service-account JSON used to
                             push job-completion notifications to the Flutter
                             app (see fcm.py). If unset/missing, push is a
                             no-op — chat and job execution work regardless.
  RETENTION_DAYS             default 30; finished (done/failed) jobs older
                             than this get pruned on startup and every 6h after
"""
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fcm  # noqa: E402
from executors import EXECUTORS  # noqa: E402

PORT = int(os.environ.get("EVA_RUNNER_PORT", "8286"))
HOST = "127.0.0.1"  # loopback only, always — see module docstring
LETTA_HOST = os.environ.get("LETTA_HOST", "http://localhost:8283").rstrip("/")
AGENT_ID = os.environ.get("EVA_AGENT_ID", "")
RETENTION_DAYS = float(os.environ.get("RETENTION_DAYS", "30"))
PRUNE_INTERVAL_S = 6 * 3600

DB_PATH = os.path.expanduser("~/.local/share/eva/tasks.db")
_db_lock = threading.Lock()


def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _db_lock, _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                spec TEXT NOT NULL,
                state TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        # FCM device tokens registered by the Flutter app (one row per
        # device/install; opaque strings from Firebase, not URLs — the runner
        # never sends anything directly to client-supplied addresses, only to
        # Google's fixed FCM endpoint with the token as a payload field, so
        # there's no SSRF surface here the way a client-chosen URL would be).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fcm_tokens (
                token TEXT PRIMARY KEY,
                added_at REAL NOT NULL
            )
        """)


def add_fcm_token(token: str):
    with _db_lock, _db() as conn:
        conn.execute(
            "INSERT INTO fcm_tokens (token, added_at) VALUES (?, ?) "
            "ON CONFLICT(token) DO NOTHING", (token, time.time()))


def remove_fcm_token(token: str):
    with _db_lock, _db() as conn:
        conn.execute("DELETE FROM fcm_tokens WHERE token = ?", (token,))


def list_fcm_tokens():
    with _db_lock, _db() as conn:
        rows = conn.execute("SELECT token FROM fcm_tokens").fetchall()
    return [r["token"] for r in rows]


def create_job(kind: str, spec: dict) -> str:
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    with _db_lock, _db() as conn:
        conn.execute(
            "INSERT INTO jobs (id, kind, spec, state, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?)",
            (job_id, kind, json.dumps(spec), now, now))
    return job_id


def get_job(job_id: str):
    with _db_lock, _db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def prune_old_jobs():
    """Delete finished jobs (done/failed) older than RETENTION_DAYS. Never touches
    pending/running rows regardless of age — an in-flight job is never pruned out
    from under itself. Best-effort; a prune failure shouldn't take the service down."""
    cutoff = time.time() - RETENTION_DAYS * 86400
    try:
        with _db_lock, _db() as conn:
            n = conn.execute(
                "DELETE FROM jobs WHERE state IN ('done','failed') AND updated_at < ?",
                (cutoff,)).rowcount
        if n:
            print(f"eva-task-runner: pruned {n} job(s) older than {RETENTION_DAYS:.0f}d")
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("eva-task-runner: prune failed: %s\n" % e)


def _prune_loop():
    while True:
        time.sleep(PRUNE_INTERVAL_S)
        prune_old_jobs()


def list_jobs(state: str = None):
    with _db_lock, _db() as conn:
        if state:
            rows = conn.execute("SELECT * FROM jobs WHERE state = ? ORDER BY created_at DESC",
                                 (state,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def set_state(job_id: str, state: str, result: dict = None, error: str = None):
    with _db_lock, _db() as conn:
        conn.execute(
            "UPDATE jobs SET state = ?, result = ?, error = ?, updated_at = ? WHERE id = ?",
            (state, json.dumps(result) if result is not None else None, error, time.time(),
             job_id))


def _report(job_id: str):
    """Best-effort: inject the result into Eva's conversation, push to any
    registered phones. Runs after every terminal state (done or failed) — a
    failed job still gets a system-role note so Eva can mention it went wrong
    instead of going silent."""
    job = get_job(job_id)
    if not job:
        return
    text = _format_report(job)
    try:
        _inject(text)
    except Exception as e:  # noqa: BLE001 — reporting must never crash the executor thread
        sys.stderr.write("eva-task-runner: inject failed: %s\n" % e)
    try:
        _notify(job, text)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("eva-task-runner: push failed: %s\n" % e)


def _format_report(job: dict) -> str:
    spec = json.loads(job["spec"])
    if job["state"] == "failed":
        label = spec.get("topic") or job["kind"]
        return f"The {job['kind']} job you kicked off (\"{label}\") failed: {job['error']}"
    result = json.loads(job["result"] or "{}")
    if job["kind"] == "research":
        topic = spec.get("topic", "?")
        summary = result.get("summary", "(no summary)")
        sources = result.get("sources") or []
        src_lines = "\n".join(f"- {s.get('title')} ({s.get('url')})" for s in sources)
        return (f"The research you kicked off on \"{topic}\" finished.\n\n"
                f"Summary: {summary}" + (f"\n\nSources:\n{src_lines}" if src_lines else ""))
    return f"The {job['kind']} job finished: {json.dumps(result)}"


def _inject(text: str):
    """POST a system-role message into Eva's Letta conversation. Not something
    the user said — a background event she reacts to and turns into a normal
    reply, per the plan's Phase-1 verification note on system-role handling."""
    if not AGENT_ID:
        return
    body = json.dumps({"messages": [{"role": "system", "content": text}]}).encode()
    req = urllib.request.Request(
        f"{LETTA_HOST}/v1/agents/{AGENT_ID}/messages",
        data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300):
        pass


def _notify(job: dict, text: str):
    """Push via FCM to every device the Flutter app has registered. Each
    target is best-effort and independent: a stale/revoked token just gets
    logged and skipped (fcm.py doesn't try to prune it — Firebase will report
    it invalid on send, worth revisiting if that gets noisy), never blocks
    the others or the job's own completion."""
    if not fcm.available():
        return
    title = "Eva finished: " + job["kind"]
    for token in list_fcm_tokens():
        try:
            fcm.send(token, title, text)
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("eva-task-runner: fcm push failed: %s\n" % e)


def _run_job(job_id: str, kind: str, spec: dict):
    set_state(job_id, "running")
    try:
        fn = EXECUTORS.get(kind)
        if fn is None:
            raise ValueError("unknown job kind: %r" % kind)
        result = fn(spec)
        set_state(job_id, "done", result=result)
    except Exception as e:  # noqa: BLE001 — a bad job must not take down the runner
        set_state(job_id, "failed", error=str(e))
    _report(job_id)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code: int, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path in ("/push/register", "/push/unregister"):
            return self._handle_push_registration()
        if self.path != "/jobs":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "bad request body"})
        kind = payload.get("kind")
        spec = payload.get("spec") or {}
        if kind not in EXECUTORS:
            return self._json(400, {"error": "unknown kind %r, have: %s" %
                                     (kind, ", ".join(EXECUTORS))})
        job_id = create_job(kind, spec)
        threading.Thread(target=_run_job, args=(job_id, kind, spec), daemon=True).start()
        self._json(201, {"job_id": job_id, "state": "pending"})

    def _handle_push_registration(self):
        """The Flutter app's FCM device token, registered/dropped as it
        (re)registers with Firebase. Reached remotely via the eva Cloudflare
        tunnel's /push/* route (Access-gated, same as the rest of
        eva.qstivi.com) — this process itself stays loopback-only. Just an
        opaque string, stored as-is — no URL/SSRF surface to validate against,
        since the runner only ever talks to Google's fixed FCM endpoint."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            token = (payload.get("token") or "").strip()
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "bad request body"})
        if not token:
            return self._json(400, {"error": "missing 'token'"})
        if self.path == "/push/register":
            add_fcm_token(token)
        else:
            remove_fcm_token(token)
        self._json(200, {"ok": True})

    def do_GET(self):
        if self.path == "/jobs":
            return self._json(200, list_jobs())
        if self.path.startswith("/jobs?state="):
            return self._json(200, list_jobs(self.path.split("=", 1)[1]))
        if self.path.startswith("/jobs/"):
            job = get_job(self.path[len("/jobs/"):])
            if not job:
                return self._json(404, {"error": "no such job"})
            for key in ("spec", "result"):
                if job.get(key):
                    job[key] = json.loads(job[key])
            return self._json(200, job)
        self._json(404, {"error": "not found"})


def main():
    init_db()
    prune_old_jobs()
    threading.Thread(target=_prune_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"eva-task-runner listening on {HOST}:{PORT} (agent={AGENT_ID or '?'})")
    server.serve_forever()


if __name__ == "__main__":
    main()
