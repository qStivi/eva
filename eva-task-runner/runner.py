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

Loopback-only by design (127.0.0.1) — never put this on the LAN. Stdlib only,
matching eva-web/toolset_router.py's posture. Config via environment (see
~/.config/eva-task-runner/eva-task-runner.env):
  EVA_RUNNER_PORT    default 8286
  LETTA_HOST         default http://localhost:8283
  EVA_AGENT_ID       Letta agent id results get injected into
  NTFY_URL           optional; a fixed self-hosted ntfy topic to also push to,
                     e.g. https://ntfy.qstivi.com/eva-jobs-xxxx. The Flutter
                     app's own UnifiedPush endpoints (registered live via
                     POST /push/register) are pushed to regardless of this.
  NTFY_TOKEN         optional; ntfy access token sent as a Bearer header on
                     every push (our ntfy denies anonymous access; the same
                     eva-runner user is granted both NTFY_URL's topic and the
                     "up*" wildcard the UnifiedPush endpoints live under)
  RETENTION_DAYS     default 30; finished (done/failed) jobs older than this
                     get pruned on startup and every 6h thereafter
"""
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from executors import EXECUTORS  # noqa: E402

PORT = int(os.environ.get("EVA_RUNNER_PORT", "8286"))
HOST = "127.0.0.1"  # loopback only, always — see module docstring
LETTA_HOST = os.environ.get("LETTA_HOST", "http://localhost:8283").rstrip("/")
AGENT_ID = os.environ.get("EVA_AGENT_ID", "")
NTFY_URL = os.environ.get("NTFY_URL", "")
NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")
# Push targets (NTFY_URL and anything registered via /push/register) must
# resolve to our own ntfy host — the runner holds a real Bearer token and
# will send it to whatever URL is on this list, so an unpinned host here
# would be an SSRF + credential-leak path straight out of client input.
PUSH_HOST = os.environ.get("NTFY_HOST", "ntfy.qstivi.com")


def _is_trusted_push_url(url: str) -> bool:
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    return p.scheme == "https" and p.hostname == PUSH_HOST
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
        # UnifiedPush endpoints registered by the Flutter app (one row per
        # device/install — the ntfy-app-as-distributor mints a fresh, unguessable
        # per-app URL on our own ntfy server, so no shared topic/token needed here).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS push_endpoints (
                endpoint TEXT PRIMARY KEY,
                added_at REAL NOT NULL
            )
        """)


def add_push_endpoint(endpoint: str):
    with _db_lock, _db() as conn:
        conn.execute(
            "INSERT INTO push_endpoints (endpoint, added_at) VALUES (?, ?) "
            "ON CONFLICT(endpoint) DO NOTHING", (endpoint, time.time()))


def remove_push_endpoint(endpoint: str):
    with _db_lock, _db() as conn:
        conn.execute("DELETE FROM push_endpoints WHERE endpoint = ?", (endpoint,))


def list_push_endpoints():
    with _db_lock, _db() as conn:
        rows = conn.execute("SELECT endpoint FROM push_endpoints").fetchall()
    return [r["endpoint"] for r in rows]


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
    """Best-effort: inject the result into Eva's conversation, fire an ntfy push.
    Runs after every terminal state (done or failed) — a failed job still gets a
    system-role note so Eva can mention it went wrong instead of going silent."""
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
        sys.stderr.write("eva-task-runner: ntfy failed: %s\n" % e)


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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Used for outbound pushes only — a redirect off PUSH_HOST must not be
    silently followed with our Bearer token still attached."""
    def redirect_request(self, *a, **k):
        return None


def _notify(job: dict, text: str):
    """Push via our self-hosted ntfy (ntfy.qstivi.com, behind the eva Cloudflare
    tunnel) — fans out to the fixed NTFY_URL topic (if set) plus every UnifiedPush
    endpoint the Flutter app has registered. Each target is best-effort and
    independent: a stale/revoked endpoint just gets logged and skipped, never
    blocks the others or the job's own completion."""
    title = "Eva finished: " + job["kind"]
    targets = list_push_endpoints()
    if NTFY_URL:
        targets = [NTFY_URL] + targets
    # No-redirect opener: a 3xx off our ntfy host must not carry the Bearer
    # token anywhere else. Registered endpoints are already host-pinned at
    # /push/register time, but this stays enforced here too in case NTFY_URL
    # is ever hand-set wrong, or ntfy itself is compromised/misconfigured.
    opener = urllib.request.build_opener(_NoRedirect)
    for url in targets:
        if not _is_trusted_push_url(url):
            sys.stderr.write("eva-task-runner: refusing to push to untrusted URL %s\n" % url)
            continue
        headers = {"Title": title}
        if NTFY_TOKEN:
            headers["Authorization"] = "Bearer " + NTFY_TOKEN
        req = urllib.request.Request(url, data=text[:400].encode(), method="POST",
                                     headers=headers)
        try:
            with opener.open(req, timeout=10):
                pass
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("eva-task-runner: ntfy push to %s failed: %s\n" % (url, e))


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
        """The Flutter app's UnifiedPush endpoint, registered/dropped as it
        (re)subscribes with its distributor. Reached remotely via the eva
        Cloudflare tunnel's /push/* route (Access-gated, same as the rest of
        eva.qstivi.com) — this process itself stays loopback-only."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            endpoint = (payload.get("endpoint") or "").strip()
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "bad request body"})
        if not endpoint:
            return self._json(400, {"error": "missing 'endpoint'"})
        if self.path == "/push/register":
            if not _is_trusted_push_url(endpoint):
                return self._json(400, {"error": "endpoint must be an https URL on " + PUSH_HOST})
            add_push_endpoint(endpoint)
        else:
            remove_push_endpoint(endpoint)
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
