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
| `EVA_API_KEY` | — | Bearer key for the OpenAI-compatible `/v1/*` routes; **empty disables `/v1` (routes 404)** |

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

### OpenAI-compatible shim (Home Assistant conversation agent)

Lets Home Assistant use Eva as an OpenAI-style conversation agent (Assist pipeline,
voice, companion app). HA POSTs OpenAI-shaped chat; we forward the **last user turn**
to the same Letta `eva` agent (Letta owns the history/memory) and return the reply in
OpenAI shape. Same persona, memory, sleep-time, and HA-control tools as every other
surface — one Eva, a new face. Auth is a **Bearer key** (`EVA_API_KEY`), separate from
the UI's Basic auth. **LAN only — never expose these routes via the Cloudflare tunnel.**

- `GET /v1/models` — lists a single model `eva` (some clients probe this)
- `POST /v1/chat/completions` — standard request; honours `stream: true` (emits a
  single SSE content chunk + `[DONE]`, since Letta returns the whole turn at once)

HA setup: point an OpenAI-compatible conversation integration (e.g. *Extended OpenAI
Conversation*) at base URL `http://<host>:8284/v1`, API key = `EVA_API_KEY`, model
`eva`. Turn **off** "Control Home Assistant / expose Assist API" — Eva already controls
the house through her own HA tools, so don't inject HA's function schemas on top.
See [`docs/2026-08-10-EVA-HA-AGENT-PLAN.md`](../docs/2026-08-10-EVA-HA-AGENT-PLAN.md).

## Notes

- The whole stack needs the **LM Studio** OpenAI-compatible server (the model behind
  Letta) running. The UI loads regardless, but Eva can't think until that's up.
- Streaming responses are a natural next upgrade (Letta exposes a `/messages/stream`
  SSE endpoint); v1 is request/response for simplicity.
