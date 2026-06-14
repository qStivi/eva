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
"""
import base64
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("EVA_WEB_PORT", "8284"))
HOST = os.environ.get("EVA_WEB_HOST", "0.0.0.0")
LETTA_HOST = os.environ.get("LETTA_HOST", "http://localhost:8283").rstrip("/")
AGENT_ID = os.environ.get("EVA_AGENT_ID", "")
AUTH_USER = os.environ.get("EVA_WEB_USER", "eva")
AUTH_PASS = os.environ.get("EVA_WEB_PASSWORD", "")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


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
            reply, tools = letta_send(message)
            return self._json(200, {"reply": reply, "tools": tools})
        except urllib.error.URLError as e:
            return self._json(502, {"error": f"Letta unreachable: {e.reason}"})
        except Exception as e:  # noqa: BLE001
            return self._json(502, {"error": f"Letta error: {e}"})


def main():
    if not AGENT_ID:
        sys.exit("eva-web: EVA_AGENT_ID is not set")
    if not AUTH_PASS:
        sys.stderr.write("eva-web: WARNING — EVA_WEB_PASSWORD is empty; auth is DISABLED\n")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    sys.stderr.write(f"eva-web: serving on http://{HOST}:{PORT}  -> agent {AGENT_ID} via {LETTA_HOST}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
