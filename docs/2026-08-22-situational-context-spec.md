# Situational context ("meta context") — spec

_Design session, 2026-08-22. The HA-fields half (below, up to "Conversational
recall") is now **built** — `eva-web/situational_context.py`, wired into
`letta_send`'s single choke point, block created+attached to both `eva` and
`eva-spike`. The **conversational recall** section is still just a design,
not built. One of several specs from the same session — see also
[timers/reminders](2026-08-22-timers-reminders-spec.md) (built),
[tool-discovery](2026-08-22-tool-discovery-spec.md) (built),
[tool-trace transparency](2026-08-22-tool-trace-transparency-spec.md) (built),
and [admin panel](2026-08-22-eva-admin-panel-spec.md). Extended same-day
(still 2026-08-22) to add conversational recall, below — same
ephemeral-per-turn pattern, different source._

## The idea, in one line

Every time Eva receives *anything* — a message from you, a check-in nudge, a
timer firing, an HA-triggered check-in — she should also see a small bundle of
live situational facts: current time, date, day of week, weather, your phone's
location (named if it's somewhere you've configured in HA, otherwise just "out
and about"), what's playing on Spotify, what's running on Steam, **and now
also: relevant snippets from old conversations, pulled fresh each message.**
This needs to be **ephemeral** — visible for that turn, refreshed before the
next one, and never written into the permanent conversation transcript.

## Why a core memory block, not a chat message

Letta already has the right primitive for this, and it's already in use:
editable **core memory blocks** — always in the model's context window, but
not part of message history. That's how persona sync
(`scripts/sync-persona.sh`) already works: the persona block gets overwritten
wholesale, the model always sees the current version, and none of that
ever shows up as a "message" in the transcript the Flutter app renders via
`LettaApi.history()`.

Add a new block, e.g. `situational_context`, and have **eva-web** (the single
front door for chat — already proxies `/api/chat`, `/v1/chat/completions`, and
`/api/checkin/trigger`) `PATCH` it with fresh values immediately before
forwarding *any* message to Letta, regardless of which route triggered it.
That gives "updates on every message Eva receives" for free, since every path
already funnels through eva-web.

This is *not* literally "vanishes after one turn" — a memory block persists
until next overwritten. But since it's refreshed on every single inbound
event, it's always "as of the last time she heard from anyone," which is what
actually matters (there's no meaningful in-between state to worry about
going stale, since nothing reads it except the next model turn).

## What goes in the block

Format: short plain-text lines, not JSON (keep it cheap in tokens and easy for
the model to read naturally, consistent with how the persona block reads).

| Field | Source | Notes |
|---|---|---|
| Time of day, date, day of week | computed locally in eva-web | no external call, trivial |
| Weather | HA `weather.forecast_home` (confirmed 2026-08-22, via `GetLiveContext`) | `state` (condition, e.g. "rainy") + `temperature`/`temperature_unit`/`humidity` attributes — everything needed |
| Location | HA `person.stephan_glaue` (confirmed 2026-08-22) | `state` is already the zone name (`home`) when in a configured zone; device-level (`device_tracker.pixel_10_pro`) also available if the person entity is ever unreliable. "Out and about" fallback is just whatever HA reports when state isn't a known zone. |
| Spotify now-playing | HA `media_player.spotify` (confirmed 2026-08-22) | `state` (`playing`/`paused`/idle), attributes `media_title`, `media_artist`, `media_album_name`, `volume_level` — exactly what's needed, no separate Spotify Web API/OAuth needed |
| Steam activity | HA `sensor.steam` + `sensor.steam_now_playing` (confirmed 2026-08-22) | `sensor.steam` is presence (`online`/`away`/etc.); `sensor.steam_now_playing` is the game name when in a session (`unknown` when not playing anything) — no separate Steam Web API needed |

All five fields resolved via the same `GetLiveContext` HA path already proven
working (2026-08-22, once entities were exposed to Assist) — nothing needs a
separate integration or API key. This can ship as one build, not staged.

## Where this lives, concretely

- New helper in `eva-web`, e.g. `situational_context.py`: `build() -> str`,
  pulling from HA (weather, location) plus whatever Spotify/Steam sources get
  confirmed, formatting into the plain-text block.
- Called from eva-web's existing single choke point before any Letta send
  (wherever `letta_send(...)` currently lives) — `PATCH` the block, then send
  the message as normal.
- Failure handling: any individual source failing (HA unreachable, Spotify API
  timeout) should degrade to omitting that line, never block the actual
  message from going through — the chat has to keep working even if the
  weather doesn't.

## Conversational recall (added same-day, after the tool-discovery debugging)

The original idea behind this whole feature: a semantic search over Eva's
*own past conversations* should run automatically on every incoming message,
surfacing relevant old context ("we talked about this 3 weeks ago") the same
ephemeral way as the HA fields above — not something she has to think to go
looking for.

**What already exists is close but not this.** Eva already has
`conversation_search` (core-attached), a genuine hybrid text+semantic search
over her full message history — but it's on-demand, a tool she has to decide
to call. There's no automatic per-message trigger today, and building one
turned out to hit real constraints, checked directly against this
self-hosted instance on 2026-08-22:

- Letta's dedicated search API (`POST /v1/messages/search`,
  `POST /v1/agents/messages/search`) is explicitly **cloud-only** — confirmed
  live: `{"detail":"Message search requires message embedding, OpenAI, and
  Turbopuffer to be enabled."}`. Not available to a self-hosted deployment
  without standing up Turbopuffer (a separate vector DB) and real OpenAI
  embeddings, neither of which Eva's stack uses (LM Studio, local).
- `conversation_search` the *tool* has no callable source of its own — its
  registry entry is a true Letta-internal built-in (`tool_type: letta_core`,
  `source_code: None`). It can't be dispatched the way `call_tool` dispatches
  our own custom tools or HA's MCP tools (there's no `/v1/tools/run`-style
  standalone path for a `letta_core` tool) — the only way to invoke the real
  implementation is through an actual agentic turn, which defeats the point
  of a cheap pre-turn ephemeral lookup.

**Practical approach:** eva-web does its own lightweight recall search
directly against the full message log (`GET /v1/agents/{id}/messages`,
already proven and already used for the app's `history()`), scoring by
keyword/text overlap — same simple approach `search_tools` already uses for
tool matching, not true vector embeddings. Loses semantic nuance compared to
what a real embedding search would give, but needs no new infrastructure and
matches this codebase's existing stdlib-only, no-new-dependency posture.
Worth revisiting with real embeddings later only if keyword matching proves
too weak in practice — not worth the Turbopuffer/OpenAI dependency up front.

### Deduplication (the specific ask: don't repeat what she already has)

Two layers, of different reliability:

1. **Exact and cheap: the agent's live context window.** An agent's current
   `AgentState` carries a `message_ids` list — the actual set of messages
   presently in Eva's working context (confirmed directly today, watching it
   shrink to one entry after a `reset-messages` call). Any recall candidate
   whose message_id is already in that set gets dropped outright — it's
   already right there, repeating it would be pure waste.
2. **Fuzzy and best-effort: the memory blocks.** Eva's agent has
   `enable_sleeptime: true` (confirmed 2026-08-22) — a background companion
   agent reviews recent messages every 5 turns and can fold facts into the
   persona/human blocks on its own. If a fact already made it in there,
   surfacing it again from raw history is redundant even though it's not
   technically in the live context window. Checking for this precisely isn't
   possible without real semantic comparison; a workable approximation is a
   keyword-overlap check against the current block text, skip a candidate
   that scores high enough. Flag as approximate in the block itself if it
   ships — "trust but verify," not authoritative deduplication.

### Open questions specific to recall

- **Cost of scanning full history every message.** As the log grows (already
  227+ messages before today's reset), doing a keyword pass over the whole
  thing per incoming message needs a sanity check — cache/index locally in
  eva-web rather than re-fetching+rescoring from scratch every single time,
  most likely.
- **How many results, and how prominent.** Unlike the HA fields (fixed,
  small, always relevant), recall results are variable — zero hits is the
  common case for an ordinary message. The block should render nothing (or
  near-nothing) when there's genuinely nothing relevant, not force a
  low-confidence match in just to fill the section.

## Open questions for build time (situational fields)

All five HA-sourced fields are now confirmed (see table above) — nothing left
to research on the "does the data exist" front. What's left is build
mechanics:

- **How eva-web reads HA state.** Two options: reuse the same `GetLiveContext`
  MCP path proven above (one call gets everything in one shot, but returns
  *all* ~400 exposed entities — needs filtering down to the ~6 that matter),
  or call HA's own REST API directly (`GET /api/states/<entity_id>`, one call
  per field, needs `HA_URL`/`HA_TOKEN` — already sitting in
  `~/.config/letta/ha.env`, reusable here). Direct REST is probably cleaner
  for "give me these 6 known entity ids," since `GetLiveContext` is built for
  open-ended querying, not a fixed field list.
- **Zone naming for location:** only `home` is configured as a zone right now
  (confirmed above) — decide the exact "out and about" fallback wording for
  literally everywhere else, so it reads in-character, not robotic. Adding
  more named zones (work, etc.) in HA is optional, not required to ship v1.
- Token cost: once all fields are in, sanity-check the block's rendered size —
  it's paid on every single turn, unlike a tool call that's only paid when
  invoked.
