# eva-web

A tiny, **dependency-free** (stdlib-only Python 3) web UI + reverse proxy for the
local Eva agent running on [Letta](https://letta.com). It serves a chat page and
forwards turns to the Letta server, so:

- the browser only ever talks to `eva-web` (no CORS, Letta stays off the LAN),
- any device on the LAN can use Eva from a URL — no install (works as a phone PWA),
- it's the seed of Eva's *own* server (eventually: two-track logic, journal/MCP, etc.).

## Run

```bash
# config is read from the environment (see the env file below)
python3 app.py
```

Then open `http://<host>:8284`.

## Configuration (environment variables)

| Var | Default | Meaning |
|---|---|---|
| `EVA_WEB_PORT` | `8284` | Listen port |
| `EVA_WEB_HOST` | `0.0.0.0` | Bind address (`0.0.0.0` = LAN-reachable) |
| `LETTA_HOST` | `http://localhost:8283` | Letta server base URL |
| `EVA_AGENT_ID` | — (required) | Letta agent id to chat with |
| `EVA_WEB_USER` | `eva` | HTTP Basic auth username |
| `EVA_WEB_PASSWORD` | — | HTTP Basic auth password; **empty disables auth** |

## Deployment on this machine

Runs as a **systemd user service** (boot-starts via linger, restarts on crash):

- Unit: `~/.config/systemd/user/eva-web.service`
- Env (chmod 600, holds the password): `~/.config/eva-web/eva-web.env`

```bash
systemctl --user status eva-web      # health
systemctl --user restart eva-web     # after editing the env or app.py
journalctl --user -u eva-web -f      # logs
```

For LAN access on Fedora/Bazzite (firewalld), open the port once:

```bash
sudo firewall-cmd --add-port=8284/tcp --permanent && sudo firewall-cmd --reload
```

## Endpoints

- `GET /` — chat UI
- `GET /api/health` — `{ "letta": bool, "agent": "..." }`
- `POST /api/chat` — `{ "message": "..." }` → `{ "reply": "...", "tools": [...] }`

## Notes

- The whole stack needs the **LM Studio** OpenAI-compatible server (the model behind
  Letta) running. The UI loads regardless, but Eva can't think until that's up.
- Streaming responses are a natural next upgrade (Letta exposes a `/messages/stream`
  SSE endpoint); v1 is request/response for simplicity.
