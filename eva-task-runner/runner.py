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

Also owns scheduled/triggered "check-ins" — Eva starting a conversation
instead of only answering one (see persona/eva.md's "How I check in on my
own" section). Same injection + push mechanism as job reports, just fired by
a timer or an external trigger (Home Assistant) instead of a finished job.
Config (on/off, interval, quiet hours) lives in the DB, editable via
GET/POST /checkin/config (the Flutter app, through eva-web's proxy). An
immediate check-in — from Home Assistant, or anything else — goes through
POST /checkin/trigger with an optional {"reason": "..."} free-text context
string (e.g. "Stephan just got home"); also reached only through eva-web's
proxy, never directly, same as the rest of this process.

Also owns one-off reminders/timers — a real alarm, set by Eva
(tools/create_timer.py, POSTing to /timers directly against this loopback
service the same way research_task does) or, later, the app. Unlike
check-ins, firing one always pushes (an alarm that might silently not go off
isn't an alarm) and always injects a nudge so Eva remembers it happened, even
if she has nothing to add. See docs/2026-08-22-timers-reminders-spec.md.
"""
import datetime
import json
import os
import re
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
import moderation  # noqa: E402
from executors import EXECUTORS  # noqa: E402

# Job kinds that must sit at pending_approval (not dispatch immediately) —
# anything that can act on the host with real effect. See
# docs/2026-08-22-delegate-to-claude-spec.md's "pending_approval gate".
APPROVAL_REQUIRED_KINDS = {"harness"}

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
                updated_at REAL NOT NULL,
                moderation_flags TEXT
            )
        """)
        # ALTER TABLE ADD COLUMN for anyone with an existing DB from before
        # pending_approval (harness jobs) existed — see checkin_config's
        # identical pattern above.
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN moderation_flags TEXT")
        except sqlite3.OperationalError:
            pass  # already has it
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
        # Single-row config for scheduled check-ins. quiet_start/quiet_end/
        # daily_time are "HH:MM" 24h local time; quiet hours wrap midnight if
        # start > end. mode picks which of interval_minutes/daily_time is used.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkin_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL DEFAULT 0,
                mode TEXT NOT NULL DEFAULT 'interval' CHECK (mode IN ('interval', 'daily')),
                interval_minutes INTEGER NOT NULL DEFAULT 240,
                daily_time TEXT NOT NULL DEFAULT '18:00',
                quiet_start TEXT NOT NULL DEFAULT '22:00',
                quiet_end TEXT NOT NULL DEFAULT '08:00',
                last_checkin_at REAL NOT NULL DEFAULT 0
            )
        """)
        # ALTER TABLE ADD COLUMN for anyone with an existing DB from before mode/
        # daily_time existed — CREATE TABLE IF NOT EXISTS doesn't retrofit columns.
        for col_sql in ("mode TEXT NOT NULL DEFAULT 'interval'", "daily_time TEXT NOT NULL DEFAULT '18:00'"):
            try:
                conn.execute(f"ALTER TABLE checkin_config ADD COLUMN {col_sql}")
            except sqlite3.OperationalError:
                pass  # already has it
        conn.execute("INSERT OR IGNORE INTO checkin_config (id) VALUES (1)")
        # One-off reminders/timers (an "alarm", not a recurring thing — see
        # docs/2026-08-22-timers-reminders-spec.md). fired_at is the poll
        # loop's dedupe key: NULL until fired, set the instant it's picked up
        # so a slow tick or a near-simultaneous second tick can't double-fire.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS timers (
                id TEXT PRIMARY KEY,
                reminder TEXT NOT NULL,
                due_at REAL NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'eva',
                created_at REAL NOT NULL,
                fired_at REAL
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


def get_checkin_config() -> dict:
    with _db_lock, _db() as conn:
        row = conn.execute("SELECT * FROM checkin_config WHERE id = 1").fetchone()
    cfg = dict(row)
    cfg["next_due_at"] = _next_due_at(cfg)
    return cfg


def _next_due_at(cfg: dict) -> float:
    """When the next check-in is due, epoch seconds. Interval mode is simple
    arithmetic; daily mode anchors to a wall-clock time — "today's slot" if
    it hasn't happened yet (or was due but hasn't fired — e.g. the service was
    down at 18:00), otherwise tomorrow's."""
    if cfg["mode"] != "daily":
        return cfg["last_checkin_at"] + cfg["interval_minutes"] * 60
    try:
        hh, mm = (int(x) for x in cfg["daily_time"].split(":"))
    except (ValueError, AttributeError):
        hh, mm = 18, 0
    now = datetime.datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    last = cfg["last_checkin_at"]
    last_dt = datetime.datetime.fromtimestamp(last) if last else None
    fired_today_at_or_after_target = (
        last_dt is not None and last_dt.date() == now.date() and last_dt >= target)
    if now < target or fired_today_at_or_after_target:
        return (target if now < target else target + datetime.timedelta(days=1)).timestamp()
    return target.timestamp()  # target already passed today and hasn't fired yet — due now


def update_checkin_config(**fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with _db_lock, _db() as conn:
        conn.execute(f"UPDATE checkin_config SET {cols} WHERE id = 1", list(fields.values()))  # noqa: S608 — fields keys are our own fixed set below, never request input


def _in_quiet_hours(cfg: dict, now: datetime.datetime) -> bool:
    try:
        sh, sm = (int(x) for x in cfg["quiet_start"].split(":"))
        eh, em = (int(x) for x in cfg["quiet_end"].split(":"))
    except (ValueError, AttributeError):
        return False
    t, s, e = now.time(), datetime.time(sh, sm), datetime.time(eh, em)
    if s == e:
        return False
    if s < e:
        return s <= t < e
    return t >= s or t < e  # wraps past midnight, e.g. 22:00 -> 08:00


CHECKIN_POLL_S = 5 * 60


def _checkin_loop():
    while True:
        time.sleep(CHECKIN_POLL_S)
        try:
            cfg = get_checkin_config()
            if not cfg["enabled"]:
                continue
            if time.time() < cfg["next_due_at"]:
                continue
            if _in_quiet_hours(cfg, datetime.datetime.now()):
                continue
            _do_checkin("scheduled")
        except Exception as e:  # noqa: BLE001 — one bad tick must not kill the loop
            sys.stderr.write("eva-task-runner: checkin loop error: %s\n" % e)


def _checkin_nudge_text(reason: str) -> str:
    """The system-role nudge Eva sees — never something Stephan actually said.
    Framed so she treats it as a prompt to *consider* reaching out, not an
    instruction to always say something (see persona/eva.md)."""
    context = f" Context: {reason}." if reason and reason not in ("scheduled", "manual") else ""
    return ("(quiet background nudge, not something Stephan said.)" + context +
            " This might be a good moment to check in, if you actually have something worth "
            "saying — otherwise it's completely fine to stay quiet and let this pass.")


def _do_checkin(reason: str):
    """Fired by the scheduler or an external trigger (Home Assistant, etc.).
    Always marks the check-in as having happened (so a silent response doesn't
    cause an immediate retry) but only pushes/notifies if Eva actually replied
    with something — her restraint is the point, not a bug to work around."""
    try:
        reply = _inject_and_get_reply(_checkin_nudge_text(reason))
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("eva-task-runner: checkin inject failed: %s\n" % e)
        reply = ""
    update_checkin_config(last_checkin_at=time.time())
    if reply:
        try:
            _push(reply, "Eva")
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("eva-task-runner: checkin push failed: %s\n" % e)


def create_timer(minutes: float, reminder: str, created_by: str = "eva") -> dict:
    timer_id = uuid.uuid4().hex[:12]
    now = time.time()
    with _db_lock, _db() as conn:
        conn.execute(
            "INSERT INTO timers (id, reminder, due_at, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (timer_id, reminder, now + minutes * 60, created_by, now))
    return {"id": timer_id, "due_at": now + minutes * 60}


def list_pending_timers():
    with _db_lock, _db() as conn:
        rows = conn.execute(
            "SELECT * FROM timers WHERE fired_at IS NULL ORDER BY due_at").fetchall()
    return [dict(r) for r in rows]


def _due_timers():
    with _db_lock, _db() as conn:
        rows = conn.execute(
            "SELECT * FROM timers WHERE fired_at IS NULL AND due_at <= ?",
            (time.time(),)).fetchall()
    return [dict(r) for r in rows]


def _mark_timer_fired(timer_id: str):
    with _db_lock, _db() as conn:
        conn.execute("UPDATE timers SET fired_at = ? WHERE id = ?", (time.time(), timer_id))


TIMER_POLL_S = 30  # short — this is meant to feel like a real alarm, not check-ins' 5min


def _timer_loop():
    while True:
        time.sleep(TIMER_POLL_S)
        try:
            for t in _due_timers():
                # Mark fired first — a slow _fire_timer (the Letta inject can take a
                # while) must never let a second tick pick the same row up again.
                _mark_timer_fired(t["id"])
                _fire_timer(t)
        except Exception as e:  # noqa: BLE001 — one bad tick must not kill the loop
            sys.stderr.write("eva-task-runner: timer loop error: %s\n" % e)


def _fire_timer(t: dict):
    """Always pushes — unlike check-ins, an alarm that might silently not go
    off isn't an alarm. Also always injects a nudge (best-effort) so Eva
    remembers it happened even if she has nothing to add right now."""
    try:
        _push(t["reminder"], "Eva ⏰")
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("eva-task-runner: timer push failed: %s\n" % e)
    try:
        _inject(
            "(a reminder you set just fired: \"%s\". Bring it up if it's natural, "
            "otherwise it already reached him directly — no need to force it.)"
            % t["reminder"])
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("eva-task-runner: timer inject failed: %s\n" % e)


def create_job(kind: str, spec: dict, state: str = "pending") -> str:
    """state defaults to 'pending' (dispatches immediately); pass
    'pending_approval' for a kind that needs a human yes before it runs —
    see APPROVAL_REQUIRED_KINDS below."""
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    with _db_lock, _db() as conn:
        conn.execute(
            "INSERT INTO jobs (id, kind, spec, state, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, kind, json.dumps(spec), state, now, now))
    return job_id


def set_moderation_flags(job_id: str, flags: list):
    with _db_lock, _db() as conn:
        conn.execute("UPDATE jobs SET moderation_flags = ? WHERE id = ?",
                     (json.dumps(flags) if flags else None, job_id))


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
        _push(text, "Eva finished: " + job["kind"])
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("eva-task-runner: push failed: %s\n" % e)


def _format_report(job: dict) -> str:
    spec = json.loads(job["spec"])
    if job["state"] == "denied":
        label = spec.get("task") or spec.get("topic") or job["kind"]
        return f"Stephan didn't approve the {job['kind']} task you proposed (\"{label}\") — it never ran."
    if job["state"] == "failed":
        label = spec.get("topic") or spec.get("task") or job["kind"]
        return f"The {job['kind']} job you kicked off (\"{label}\") failed: {job['error']}"
    result = json.loads(job["result"] or "{}")
    if job["kind"] == "research":
        topic = spec.get("topic", "?")
        summary = result.get("summary", "(no summary)")
        sources = result.get("sources") or []
        src_lines = "\n".join(f"- {s.get('title')} ({s.get('url')})" for s in sources)
        return (f"The research you kicked off on \"{topic}\" finished.\n\n"
                f"Summary: {summary}" + (f"\n\nSources:\n{src_lines}" if src_lines else ""))
    if job["kind"] == "harness":
        task = spec.get("task", "?")
        output = result.get("output", "(no output)")
        exit_note = "" if result.get("exit_code") == 0 else f" (exit code {result.get('exit_code')})"
        return f"The task you delegated — \"{task}\" — finished{exit_note}.\n\n{output}"
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


def _inject_and_get_reply(text: str) -> str:
    """Like _inject, but parses the response for Eva's own reply text (empty
    string if she said nothing, or AGENT_ID isn't set). The /messages POST
    processes the turn synchronously and returns it same as a real user turn
    would — same parsing eva-web's letta_send() does, minus tool-call tracking
    since check-ins don't need it."""
    if not AGENT_ID:
        return ""
    body = json.dumps({"messages": [{"role": "system", "content": text}]}).encode()
    req = urllib.request.Request(
        f"{LETTA_HOST}/v1/agents/{AGENT_ID}/messages",
        data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode())
    msgs = data.get("messages", data if isinstance(data, list) else [])
    parts = [m["content"] for m in msgs
             if m.get("message_type") == "assistant_message" and m.get("content")]
    return "\n".join(p.strip() for p in parts).strip()


def _push(text: str, title: str, extra_data: dict = None):
    """Push via FCM to every device the Flutter app has registered. Each
    target is best-effort and independent: a stale/revoked token just gets
    logged and skipped (fcm.py doesn't try to prune it — Firebase will report
    it invalid on send, worth revisiting if that gets noisy), never blocks
    the others or whatever triggered this push."""
    if not fcm.available():
        return
    for token in list_fcm_tokens():
        try:
            fcm.send(token, title, text, extra_data=extra_data)
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("eva-task-runner: fcm push failed: %s\n" % e)


def _handle_pending_approval(job_id: str, spec: dict):
    """Runs the moderation pre-check (best-effort, see moderation.py) and
    fires the approval push. Does NOT dispatch the executor — that only
    happens via _handle_job_approve, once you've said yes."""
    flags = moderation.check(spec.get("task") or "")
    if flags:
        set_moderation_flags(job_id, flags)
    task = (spec.get("task") or "?")[:200]
    flag_note = f" [flagged: {', '.join(flags)}]" if flags else ""
    # type=approval — push_service.dart deep-links to eva-web's /jobs page on
    # tap for this one, instead of just opening the app (see
    # docs/2026-08-22-delegate-to-claude-spec.md's approval-surface section).
    _push(f"Eva wants to run: {task}{flag_note}", "Approval needed", extra_data={"type": "approval"})


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
        if self.path == "/checkin/config":
            return self._handle_checkin_config()
        if self.path == "/checkin/trigger":
            return self._handle_checkin_trigger()
        if self.path == "/timers":
            return self._handle_create_timer()
        if self.path.startswith("/jobs/") and self.path.endswith("/approve"):
            return self._handle_job_approve(self.path[len("/jobs/"):-len("/approve")])
        if self.path.startswith("/jobs/") and self.path.endswith("/deny"):
            return self._handle_job_deny(self.path[len("/jobs/"):-len("/deny")])
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
        if kind in APPROVAL_REQUIRED_KINDS:
            job_id = create_job(kind, spec, state="pending_approval")
            threading.Thread(target=_handle_pending_approval, args=(job_id, spec), daemon=True).start()
            return self._json(201, {"job_id": job_id, "state": "pending_approval"})
        job_id = create_job(kind, spec)
        threading.Thread(target=_run_job, args=(job_id, kind, spec), daemon=True).start()
        self._json(201, {"job_id": job_id, "state": "pending"})

    def _handle_job_approve(self, job_id: str):
        """Auth is the caller's job — this loopback endpoint trusts whoever can
        reach it, same as every other route here. eva-web is the only thing
        that's supposed to reach it (Cloudflare-Access-gated for the phone),
        never exposed on the LAN directly. See the spec's pending_approval
        gate section."""
        job = get_job(job_id)
        if not job or job["state"] != "pending_approval":
            return self._json(404, {"error": "no pending_approval job with that id"})
        set_state(job_id, "pending")
        spec = json.loads(job["spec"])
        threading.Thread(target=_run_job, args=(job_id, job["kind"], spec), daemon=True).start()
        self._json(200, {"ok": True, "state": "pending"})

    def _handle_job_deny(self, job_id: str):
        job = get_job(job_id)
        if not job or job["state"] != "pending_approval":
            return self._json(404, {"error": "no pending_approval job with that id"})
        set_state(job_id, "denied")
        threading.Thread(target=_report, args=(job_id,), daemon=True).start()
        self._json(200, {"ok": True, "state": "denied"})

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

    def _handle_checkin_config(self):
        """Read-modify-write of the single check-in config row. Only touches
        fields present in the request body; validated before anything's
        written so a bad request never leaves a half-updated config."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "bad request body"})
        fields = {}
        if "enabled" in payload:
            fields["enabled"] = 1 if payload["enabled"] else 0
        if "mode" in payload:
            if payload["mode"] not in ("interval", "daily"):
                return self._json(400, {"error": "mode must be 'interval' or 'daily'"})
            fields["mode"] = payload["mode"]
        if "interval_minutes" in payload:
            try:
                iv = int(payload["interval_minutes"])
            except (TypeError, ValueError):
                return self._json(400, {"error": "interval_minutes must be an integer"})
            if iv < 15:
                return self._json(400, {"error": "interval_minutes must be >= 15"})
            fields["interval_minutes"] = iv
        for key in ("quiet_start", "quiet_end", "daily_time"):
            if key in payload:
                v = payload[key]
                if not isinstance(v, str) or not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", v):
                    return self._json(400, {"error": f"{key} must be HH:MM (24h)"})
                fields[key] = v
        update_checkin_config(**fields)
        self._json(200, get_checkin_config())

    def _handle_checkin_trigger(self):
        """Fire one check-in now, outside the schedule — Home Assistant
        automations (or anything else) hit this. Dispatched on a thread and
        answered immediately, same shape as job submission: this can take as
        long as a full Letta turn, and callers like an HA rest_command
        shouldn't be left hanging on that."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except (ValueError, json.JSONDecodeError):
            payload = {}
        reason = (payload.get("reason") or "manual").strip()[:200]
        threading.Thread(target=_do_checkin, args=(reason,), daemon=True).start()
        self._json(202, {"ok": True, "dispatched": True})

    def _handle_create_timer(self):
        """Called by tools/create_timer.py — Eva setting a reminder, the way
        you'd set an alarm. Validated synchronously (this is cheap — no
        thread dispatch needed, unlike job submission or a check-in)."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "bad request body"})
        try:
            minutes = float(payload.get("minutes"))
        except (TypeError, ValueError):
            return self._json(400, {"error": "minutes must be a number"})
        if minutes <= 0:
            return self._json(400, {"error": "minutes must be > 0"})
        reminder = (payload.get("reminder") or "").strip()[:300]
        if not reminder:
            return self._json(400, {"error": "missing 'reminder'"})
        self._json(201, create_timer(minutes, reminder, created_by=payload.get("created_by", "eva")))

    def do_GET(self):
        if self.path == "/checkin/config":
            return self._json(200, get_checkin_config())
        if self.path == "/timers":
            return self._json(200, list_pending_timers())
        if self.path == "/jobs":
            return self._json(200, list_jobs())
        if self.path.startswith("/jobs?state="):
            return self._json(200, list_jobs(self.path.split("=", 1)[1]))
        if self.path.startswith("/jobs/"):
            job = get_job(self.path[len("/jobs/"):])
            if not job:
                return self._json(404, {"error": "no such job"})
            for key in ("spec", "result", "moderation_flags"):
                if job.get(key):
                    job[key] = json.loads(job[key])
            return self._json(200, job)
        self._json(404, {"error": "not found"})


def main():
    init_db()
    prune_old_jobs()
    threading.Thread(target=_prune_loop, daemon=True).start()
    threading.Thread(target=_checkin_loop, daemon=True).start()
    threading.Thread(target=_timer_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"eva-task-runner listening on {HOST}:{PORT} (agent={AGENT_ID or '?'})")
    server.serve_forever()


if __name__ == "__main__":
    main()
