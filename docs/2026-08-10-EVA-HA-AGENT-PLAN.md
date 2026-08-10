# Eva as a Home Assistant conversation agent — design & build plan

_Planning session, 2026-08-10. A **thin adapter**, not a pivot: expose the existing
Eva (Letta agent) through Home Assistant's Assist pipeline so you can talk to her —
by text and by voice — from HA's surfaces (companion app, browser, voice satellites),
without rebuilding anything. Additive to, and independent of, the
["Eva with hands" arc](2026-07-22-EVA-WITH-HANDS-PLAN.md)._

## The idea, in one line

Eva's brain is **Letta** (agent `eva`, gpt-oss-20b), which speaks its own
`/v1/agents/{id}/messages` API — not OpenAI's. HA's LLM conversation integrations
speak **OpenAI Chat Completions**. So the entire integration is one small
**OpenAI-compatible shim** in front of Letta. HA sees a normal OpenAI conversation
agent; behind it is the full Eva — same persona, same memory, same sleep-time
consolidation, same HA-control tools. **One Eva, a new face.** No change to Letta or
the agent config.

## Why this is smart to do before the big arc (not a distraction)

- **It's additive and low-risk.** It adds a new *inbound* surface. It does not touch
  the runner / ntfy / HITL machinery the "with hands" arc needs, so it can't rot it.
- **It attacks that arc's biggest weakness for free.** The reason Phase 1 of the big
  arc exists is that the Flutter app talks to Letta directly, so there is *no
  always-on, phone-reachable, notification-capable server seam* for background events.
  HA is exactly that server, already running in the house. Living inside HA gives Eva
  a background-reachable, voice-capable surface from infrastructure we already run.
- The genuinely novel, higher-risk runner+HITL work still has to happen — but there's
  no reason it must come first, and this de-risks it rather than delaying it.

## Architecture

```
HA Assist  ──OpenAI Chat Completions──►  eva shim (eva-web :8284, LAN)  ──►  Letta :8283  ──►  eva agent
 (text / voice)   Bearer API key            + toolset_router.preload_for()        (persona, memory, HA tools)
```

- **Reuse `eva-web`, don't build new infra.** `eva-web/app.py` already has
  `letta_send(message) -> (reply, tools)` and imports `preload_for(...)` (the lazy
  toolset router), dispatched by simple path matching in `do_POST`. Add a
  `POST /v1/chat/completions` route that: takes the last user message from the OpenAI
  `messages` array → `preload_for(msg)` → `letta_send(msg)` → wraps the reply in an
  OpenAI `chat.completion` JSON. ~40 lines, reusing everything.
- **Auth.** The `/v1/*` paths accept a **Bearer API key** (random secret in
  `~/.config/eva-web/eva-web.env`), separate from the UI's HTTP Basic auth. HA stores
  that key as the integration's "API key."
- **Networking.** eva-web already binds `0.0.0.0:8284` and is LAN-reachable (firewall
  port already open). HA (`192.168.129.102`) reaches the bazzite host
  (`192.168.128.126`) — the subnets already route (Letta→HA MCP over SSE proves it).
  **LAN only — this endpoint is never put on the Cloudflare tunnel;** HA is local.

## Decisions

1. **Eva is a pure conversation agent in HA — HA's Assist API / intent tools stay OFF
   for this agent.** When you say "turn off the lights," Eva acts through *her own* HA
   MCP tools (the existing Letta→HA path), not HA-injected function schemas. This
   avoids a confusing double-control path, and avoids piling HA's function definitions
   on top of Eva's already-large tool context (the known 20B-slowdown gotcha — see
   `eva-home-assistant-mcp` / `eva-lazy-toolsets`).

2. **HA integration = "Extended OpenAI Conversation" (HACS), unless core supports a
   base-URL override.** Core OpenAI Conversation historically hardcodes
   `api.openai.com`; the community **Extended OpenAI Conversation** custom integration
   is purpose-built to point HA at a custom OpenAI-compatible base URL and to disable
   HA function-calling. **The one live unknown:** whether HA 2026.7's *core* OpenAI
   Conversation now allows a custom base URL — verified cheaply in Phase 2; if it does,
   we skip HACS.

3. **One shared Letta thread is a feature, not a bug.** HA turns and Flutter-app turns
   both land on the same `eva` thread → continuous memory across every surface. Correct
   for a companion. Tradeoff: no per-surface conversation isolation — accepted.

4. **Non-streaming responses for v1.** Letta returns the full turn anyway; emit a
   single completion. Add a one-chunk SSE path only if HA insists on `stream:true`.

## Build phases

- **Phase 0 — Reachability check.** From HA (or a box on its subnet):
  `curl http://192.168.128.126:8284/api/health` → expect Letta health JSON. If blocked,
  it's firewall/subnet and everything waits on that. _(Blocked today: HA is mid-update;
  runs once it's back.)_
- **Phase 1 — The shim.** Add `POST /v1/chat/completions` (+ a stub `GET /v1/models`,
  which some clients probe) to `eva-web/app.py`; add an `EVA_API_KEY` Bearer check for
  the `/v1/*` paths; secret into the env file. Test locally with a raw OpenAI-shaped
  `curl` → expect Eva's reply. Restart `eva-web.service`. **Does not need HA.**
- **Phase 2 — Wire HA.** Install Extended OpenAI Conversation (or configure core if
  base-URL works); base URL `http://192.168.128.126:8284/v1`, API key = the secret,
  model name = anything (e.g. `eva`). Turn **off** "Control Home Assistant / expose
  Assist API." Test via HA Developer Tools → Assist / the Assist chat box.
- **Phase 3 — Make it an Assist pipeline (the payoff).** Build a pipeline STT → **Eva**
  → TTS, selectable in the HA companion app and on Assist satellites (Voice PE, etc.).
  v1 uses HA's built-in/cloud TTS; wiring the local `~/tts` models is a later nicety.
- **Phase 4 — Polish.** Tune latency; optionally trim exposed HA entities; consider
  routing the HA surface to a faster/cloud model (voice makes 20B lag more noticeable).

## Risks / watch-items

- **Latency.** gpt-oss-20b + STT + TTS round-trips can feel slow for voice. Mitigated
  by keeping HA's tool schemas off and leaning on the lazy router; flagged as a
  candidate for a faster/cloud model on this surface (ties into the roadmap's
  cloud-escalation item).
- **Core-vs-HACS unknown** (decision 2) — resolved in Phase 2, cheaply.
- **Security surface.** A new LAN endpoint that can drive the house + Eva's memory →
  gated by the Bearer key, LAN-bound, never tunneled.

## Effort

Roughly a **half-day**: the shim is ~40 lines reusing existing helpers; the rest is
HA-side config. A thin adapter, not a pivot.
