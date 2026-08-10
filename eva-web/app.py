#!/usr/bin/env python3
"""eva-web — a tiny, dependency-free web UI + proxy for the local Eva (Letta) agent.

The browser only ever talks to this server; this server proxies to Letta. That
keeps Letta off the LAN and sidesteps CORS. Stdlib only (matches the atomic-OS,
no-venv approach used elsewhere in this home dir).

Config via environment (see ~/.config/eva-web/eva-web.env):
  EVA_WEB_PORT       default 8284
  EVA_WEB_HOST       default 0.0.0.0  (LAN-reachable)
  LETTA_HOST         default http://localhost:8283
  EVA_AGENT_ID       Letta agent id to talk to
  EVA_WEB_USER       Basic-auth username (default "eva")
  EVA_WEB_PASSWORD   Basic-auth password; if empty, auth is DISABLED (warns)
  EVA_API_KEY        Bearer key for the OpenAI-compatible /v1/* routes (Home
                     Assistant's Assist conversation agent talks to those); if
                     empty, the /v1 routes are DISABLED (they 404) so we never
                     expose an unauthenticated Eva endpoint by accident.

The /v1/* routes (chat/completions, models) let Home Assistant use Eva as an
OpenAI-style conversation agent: HA POSTs OpenAI-shaped chat, we forward the last
user turn to the same Letta `eva` agent (persona, memory, HA tools) and return the
reply in OpenAI shape. LAN only — never put this behind the Cloudflare tunnel.
"""
import base64
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("EVA_WEB_PORT", "8284"))
HOST = os.environ.get("EVA_WEB_HOST", "0.0.0.0")
LETTA_HOST = os.environ.get("LETTA_HOST", "http://localhost:8283").rstrip("/")
AGENT_ID = os.environ.get("EVA_AGENT_ID", "")
AUTH_USER = os.environ.get("EVA_WEB_USER", "eva")
AUTH_PASS = os.environ.get("EVA_WEB_PASSWORD", "")
API_KEY = os.environ.get("EVA_API_KEY", "")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

try:
    # Intent-based toolset pre-loading (see toolset_router.py). Best-effort: if it's
    # missing or errors, chat still works — Eva just keeps whatever tools she has.
    from toolset_router import preload_for
except Exception:  # noqa: BLE001
    preload_for = None


def letta_send(message: str):
    """Send one user turn to Letta; return (reply_text, [tool_names])."""
    url = f"{LETTA_HOST}/v1/agents/{AGENT_ID}/messages"
    body = json.dumps({"messages": [{"role": "user", "content": message}]}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode())
    msgs = data.get("messages", data if isinstance(data, list) else [])
    reply_parts, tools = [], []
    for m in msgs:
        t = m.get("message_type")
        if t == "assistant_message" and m.get("content"):
            reply_parts.append(m["content"])
        elif t == "tool_call_message":
            name = m.get("tool_call", {}).get("name")
            if name:
                tools.append(name)
    reply = "\n".join(p.strip() for p in reply_parts).strip()
    return reply or "(no reply)", tools


def run_turn(message: str):
    """Pre-attach the right toolsets (best-effort) then send one turn to Letta.

    Shared by the web UI (/api/chat) and the OpenAI-compatible shim
    (/v1/chat/completions) so both surfaces get the lazy toolset router.
    """
    if preload_for is not None and AGENT_ID:
        try:
            preload_for(message, AGENT_ID, LETTA_HOST)
        except Exception:  # noqa: BLE001 — best-effort; never block the chat
            pass
    return letta_send(message)


def _last_user_message(payload: dict) -> str:
    """Pull the latest user turn out of an OpenAI chat-completions request.

    HA sends the whole running transcript; Letta owns Eva's memory/thread, so we
    only forward the newest user turn and let Letta supply the history. `content`
    is usually a string but the vision schema allows a list of parts — join text.
    """
    msgs = payload.get("messages")
    if not isinstance(msgs, list):
        return ""
    for m in reversed(msgs):
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content", "")
            if isinstance(c, str):
                return c.strip()
            if isinstance(c, list):  # [{type:"text", text:"..."}, ...]
                parts = [p.get("text", "") for p in c if isinstance(p, dict)]
                return "\n".join(parts).strip()
    return ""


class Handler(BaseHTTPRequestHandler):
    server_version = "eva-web"

    # ---- helpers -------------------------------------------------------
    def _authed(self) -> bool:
        if not AUTH_PASS:
            return True  # auth disabled
        hdr = self.headers.get("Authorization", "")
        if not hdr.startswith("Basic "):
            return False
        try:
            user, _, pw = base64.b64decode(hdr[6:]).decode().partition(":")
        except Exception:
            return False
        return hmac.compare_digest(user, AUTH_USER) and hmac.compare_digest(pw, AUTH_PASS)

    def _need_auth(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Eva"')
        self.end_headers()

    def _api_authed(self) -> bool:
        """Bearer-key auth for the OpenAI-compatible /v1/* routes."""
        hdr = self.headers.get("Authorization", "")
        if not hdr.startswith("Bearer "):
            return False
        return hmac.compare_digest(hdr[7:].strip(), API_KEY)

    def _json(self, code: int, obj):
        payload = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _file(self, path: str, ctype: str):
        try:
            with open(path, "rb") as f:
                payload = f.read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("eva-web: " + (fmt % args) + "\n")

    # ---- routes --------------------------------------------------------
    def do_GET(self):
        # OpenAI-compatible surface (Home Assistant): Bearer-key auth, own routes.
        if self.path.startswith("/v1/"):
            return self._openai_get()
        if not self._authed():
            return self._need_auth()
        if self.path in ("/", "/index.html"):
            return self._file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
        if self.path == "/api/health":
            ok = True
            try:
                with urllib.request.urlopen(f"{LETTA_HOST}/v1/health/", timeout=4) as r:
                    ok = r.status == 200
            except Exception:
                ok = False
            return self._json(200, {"letta": ok, "agent": AGENT_ID})
        self.send_error(404)

    def do_POST(self):
        # OpenAI-compatible surface (Home Assistant): Bearer-key auth, own routes.
        if self.path.startswith("/v1/"):
            return self._openai_post()
        if not self._authed():
            return self._need_auth()
        if self.path != "/api/chat":
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode())
            message = (payload.get("message") or "").strip()
        except Exception:
            return self._json(400, {"error": "bad request"})
        if not message:
            return self._json(400, {"error": "empty message"})
        try:
            reply, tools = run_turn(message)
            return self._json(200, {"reply": reply, "tools": tools})
        except urllib.error.URLError as e:
            return self._json(502, {"error": f"Letta unreachable: {e.reason}"})
        except Exception as e:  # noqa: BLE001
            return self._json(502, {"error": f"Letta error: {e}"})

    # ---- OpenAI-compatible shim (Home Assistant conversation agent) ----
    def _openai_get(self):
        if not API_KEY:
            return self.send_error(404)  # /v1 disabled when no key configured
        if not self._api_authed():
            return self._json(401, {"error": {"message": "invalid api key", "type": "invalid_request_error"}})
        if self.path.rstrip("/") == "/v1/models":
            return self._json(200, {
                "object": "list",
                "data": [{"id": "eva", "object": "model", "created": int(time.time()), "owned_by": "eva"}],
            })
        self.send_error(404)

    def _openai_post(self):
        if not API_KEY:
            return self.send_error(404)  # /v1 disabled when no key configured
        if not self._api_authed():
            return self._json(401, {"error": {"message": "invalid api key", "type": "invalid_request_error"}})
        if self.path.rstrip("/") != "/v1/chat/completions":
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode())
        except Exception:
            return self._json(400, {"error": {"message": "bad request", "type": "invalid_request_error"}})
        message = _last_user_message(payload)
        if not message:
            return self._json(400, {"error": {"message": "no user message", "type": "invalid_request_error"}})
        model = payload.get("model") or "eva"
        stream = bool(payload.get("stream"))
        try:
            reply, _tools = run_turn(message)
        except urllib.error.URLError as e:
            return self._json(502, {"error": {"message": f"Letta unreachable: {e.reason}", "type": "server_error"}})
        except Exception as e:  # noqa: BLE001
            return self._json(502, {"error": {"message": f"Letta error: {e}", "type": "server_error"}})
        cid = "chatcmpl-" + uuid.uuid4().hex
        created = int(time.time())
        if stream:
            return self._openai_stream(cid, created, model, reply)
        return self._json(200, {
            "id": cid,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    def _openai_stream(self, cid: str, created: int, model: str, reply: str):
        """Minimal SSE: one content delta, then a stop chunk, then [DONE].

        Letta already returns the whole turn, so there's nothing to stream
        token-by-token; a single delta satisfies clients that require stream=true.
        """
        def chunk(delta, finish):
            return "data: " + json.dumps({
                "id": cid, "object": "chat.completion.chunk", "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }) + "\n\n"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(chunk({"role": "assistant", "content": reply}, None).encode())
        self.wfile.write(chunk({}, "stop").encode())
        self.wfile.write(b"data: [DONE]\n\n")


def main():
    if not AGENT_ID:
        sys.exit("eva-web: EVA_AGENT_ID is not set")
    if not AUTH_PASS:
        sys.stderr.write("eva-web: WARNING — EVA_WEB_PASSWORD is empty; auth is DISABLED\n")
    if API_KEY:
        sys.stderr.write("eva-web: OpenAI-compatible /v1 routes ENABLED (Bearer key) for HA\n")
    else:
        sys.stderr.write("eva-web: EVA_API_KEY unset; /v1 routes DISABLED (404)\n")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    sys.stderr.write(f"eva-web: serving on http://{HOST}:{PORT}  -> agent {AGENT_ID} via {LETTA_HOST}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
