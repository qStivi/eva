"""DeepSeek Harness executor — runs `dsh` (open-source, MIT, model-agnostic
agent framework, docs.mistral.ai's own comparison guide unrelated) headless
on the host, backed by a Mistral model, instead of `claude -p`. See
docs/2026-08-22-delegate-to-claude-spec.md (kept its old filename; content
covers this pivot) for the full design/rationale.

Two things this module owns that the spec calls out as non-obvious:

1. A tiny local stripping PROXY (`_StripProxy` below) sits between `dsh` and
   the real Mistral API. The bundled "DeepSeek" adapter dsh-mistral-patch.yml
   repoints at Mistral cannot be configured to omit a DeepSeek-specific
   `thinking`/`reasoning_effort` field from its request body — confirmed
   empirically, every config combination still emits one or the other.
   Mistral's schema is strict (`extra_forbidden`) and 422s on it — same bug
   class as the 2026-08-13 Letta/Mistral BYOK issue (see model_router.py's
   docstring). The proxy strips those two keys and forwards everything else
   (including the SSE stream) untouched. Runs only for the duration of one
   job, on 127.0.0.1 only.
2. The Mistral API key is pulled live from Letta's own provider store
   (same pattern research.py's `_mistral_key()` uses) and injected only into
   the `dsh` subprocess's environment — never written to disk here.
"""
import http.client
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LETTA_HOST = os.environ.get("LETTA_HOST", "http://localhost:8283").rstrip("/")
DSH_BIN = os.environ.get("DSH_BIN", "/home/linuxbrew/.linuxbrew/bin/dsh")
PATCH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dsh-mistral-patch.yml")
DEFAULT_WORKDIR = os.path.expanduser("~/eva-workspace")
STRIP_PROXY_PORT = 8998  # must match dsh-mistral-patch.yml's baseURL
JOB_TIMEOUT_S = int(os.environ.get("HARNESS_JOB_TIMEOUT_S", "900"))
STRIP_FIELDS = ("thinking", "reasoning_effort")  # see module docstring

_key_cache = {"key": None, "ts": 0}


def _mistral_key() -> str:
    """Same fetch-and-cache pattern as research.py's _mistral_key() — pulled
    from Letta's own provider store, cached in-process for an hour."""
    if _key_cache["key"] and time.time() - _key_cache["ts"] < 3600:
        return _key_cache["key"]
    with urllib.request.urlopen(LETTA_HOST + "/v1/providers/", timeout=10) as r:
        providers = json.loads(r.read().decode())
    for p in providers:
        if p.get("name") == "mistral" and p.get("api_key_enc"):
            _key_cache.update(key=p["api_key_enc"], ts=time.time())
            return p["api_key_enc"]
    raise RuntimeError("no 'mistral' provider with a key configured in Letta")


class _StripProxyHandler(BaseHTTPRequestHandler):
    """Forwards everything to https://api.mistral.ai/v1, stripping
    STRIP_FIELDS from a JSON request body first. Streams the (SSE) response
    back chunk-by-chunk rather than buffering it whole, since dsh expects a
    live event stream, not a delayed one."""

    def log_message(self, *a):  # quiet — this runs inside a background job thread
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw)
            for f in STRIP_FIELDS:
                body.pop(f, None)
            raw = json.dumps(body).encode()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # not JSON (e.g. /files uploads) — forward as-is, untouched

        conn = http.client.HTTPSConnection("api.mistral.ai", timeout=300)
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length")}
        headers["Content-Length"] = str(len(raw))
        # dsh's adapter fetches `${baseURL}/chat/completions` — baseURL here is
        # just this proxy's bare origin, so the real Mistral API's own `/v1`
        # prefix has to be added back on the way out.
        try:
            conn.request("POST", "/v1" + self.path, body=raw, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ("content-length", "transfer-encoding", "connection"):
                    self.send_header(k, v)
            self.end_headers()
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
        finally:
            conn.close()

    def do_GET(self):
        self.do_POST()  # not expected to be hit (chat-completions is POST-only), but harmless if it is


def _run_strip_proxy():
    server = ThreadingHTTPServer(("127.0.0.1", STRIP_PROXY_PORT), _StripProxyHandler)
    server.serve_forever()


_proxy_thread_lock = threading.Lock()
_proxy_thread = None


def _ensure_strip_proxy():
    """Idempotent — the proxy is stateless and job-agnostic, so one instance
    for the whole process is fine; no need to spin one up per job."""
    global _proxy_thread
    with _proxy_thread_lock:
        if _proxy_thread is None or not _proxy_thread.is_alive():
            _proxy_thread = threading.Thread(target=_run_strip_proxy, daemon=True)
            _proxy_thread.start()
            time.sleep(0.2)  # let the socket bind before dsh's first request


# Fixed catalog, matching dsh-mistral-patch.yml's own `models:` list — the
# ONLY two model ids this executor will ever pass through. `model` reaches
# here from the task spec, which a delegated task's own content (or a
# prompt-injected instruction inside it) can influence; validating against
# this allowlist rather than accepting any string closes two things at once
# (see the run() docstring's Security note): it's also the exact value that
# gets f-string-interpolated into the ad-hoc YAML override below, so a
# rejected model can never reach that interpolation either.
ALLOWED_MODELS = ("mistral-large-latest", "codestral-2508")


def _resolve_workdir(requested: str) -> str:
    """DEFAULT_WORKDIR itself, or a real subdirectory of it — nothing else.
    `os.path.realpath` resolves `..`/symlinks before the containment check,
    so this can't be escaped by either. Raises ValueError (not silently
    falling back) so a job that asked for somewhere out of scope fails
    loudly with a clear reason, rather than either running somewhere
    unintended or crashing on a raw OSError deep inside os.makedirs."""
    base = os.path.realpath(os.path.expanduser(DEFAULT_WORKDIR))
    if not requested:
        return base
    resolved = os.path.realpath(os.path.expanduser(requested))
    if resolved != base and not resolved.startswith(base + os.sep):
        raise ValueError(
            f"workdir {requested!r} is outside the allowed scratch directory "
            f"({DEFAULT_WORKDIR}) — leave workdir unset for the default, or use a "
            f"subdirectory under it, e.g. '{DEFAULT_WORKDIR}/some-project'")
    return resolved


def run(spec: dict) -> dict:
    """Entry point called by runner.py's executor dispatch. spec: {"task":
    str, "workdir": str?, "model": str? ("mistral-large-latest" default, or
    "codestral-2508" for code-focused work)}. Returns {"output": str,
    "exit_code": int}. Raises on setup failure (missing/malformed task, dsh
    not found) — a bad *run* still returns normally with a non-zero
    exit_code, since that's a real (if disappointing) result, not an
    executor bug.

    Security note: `task`/`model`/`workdir` all ultimately trace back to
    content Eva (an LLM) decided to put in a tool call — which can itself be
    steered by something a delegated task or fetched web page said, not
    just Stephan. Confirmed live during the build that `dsh` genuinely
    parses a task string starting with "-" as one of ITS OWN flags rather
    than erroring safely (`task="--dump-config"` really dumps the composed
    config instead of running as task text) — a `--` end-of-options marker
    does NOT protect against this for this particular CLI (tested; it makes
    the failure mode worse, not better). So a leading "-" is rejected
    outright below, and `model` is checked against ALLOWED_MODELS before it
    ever reaches the YAML override string, rather than trusting the caller
    not to hand back stray YAML syntax. `workdir` is constrained to
    DEFAULT_WORKDIR or a real subdirectory of it (confirmed live 2026-08-22:
    Eva guessed `/home/stephan/eva-workspace` — a plausible-sounding but
    nonexistent path, since the real account here is `qstivi` — and got a
    raw `PermissionError` trying to create `/home/stephan`; this both gives
    a clearer error for that case and closes the spec's open "fixed vs.
    free-text workdir" question in favor of fixed)."""
    task = (spec.get("task") or "").strip()
    if not task:
        raise ValueError("harness job spec needs a non-empty 'task'")
    if task.startswith("-"):
        raise ValueError("harness task text can't start with '-' — dsh's own CLI "
                          "parses a leading '-' as one of its own flags, not task text")
    if not shutil.which(DSH_BIN) and not os.path.isfile(DSH_BIN):
        raise RuntimeError(f"dsh binary not found at {DSH_BIN} — is DeepSeek Harness installed?")

    workdir = _resolve_workdir(spec.get("workdir"))
    os.makedirs(workdir, exist_ok=True)
    model = spec.get("model") or "mistral-large-latest"
    if model not in ALLOWED_MODELS:
        raise ValueError(f"unsupported model {model!r} — allowed: {ALLOWED_MODELS}")

    _ensure_strip_proxy()

    patches = [os.path.abspath(PATCH_FILE)]
    if model != "mistral-large-latest":
        # Small ad-hoc overlay applied on top of the base patch (--patch is
        # repeatable and applies in order) — just swaps the model id. `model`
        # is already validated against ALLOWED_MODELS above, so this
        # f-string can never carry attacker-controlled YAML syntax into the
        # patch (a colon, a newline, a second `- id:` entry, ...).
        override = f"- id: agent-default-model\n  config:\n    provider: deepseek-official\n    model: {model}\n"
        override_path = os.path.join(workdir, ".dsh-model-override.yml")
        with open(override_path, "w") as f:
            f.write(override)
        patches.append(override_path)

    cmd = [DSH_BIN, "--profile", "headless"]
    for p in patches:
        cmd += ["--patch", p]
    cmd.append(task)

    # `dsh` shebangs `#!/usr/bin/env node` — node needs to be on PATH at exec
    # time, but eva-task-runner.service's systemd PATH doesn't include
    # linuxbrew's bin dir (where both node and dsh live). Prepend it rather
    # than assume the caller's environment already has it.
    brew_bin = os.path.dirname(DSH_BIN)
    env = {**os.environ, "MISTRAL_API_KEY": _mistral_key(),
           "PATH": brew_bin + os.pathsep + os.environ.get("PATH", "")}
    proc = subprocess.run(
        cmd, cwd=workdir, env=env, capture_output=True, text=True,
        timeout=JOB_TIMEOUT_S,
    )
    output = (proc.stdout or "").strip()
    if proc.returncode != 0 and (proc.stderr or "").strip():
        output = (output + "\n\n" + proc.stderr.strip()).strip()
    return {"output": output or "(no output)", "exit_code": proc.returncode, "model": model, "workdir": workdir}
