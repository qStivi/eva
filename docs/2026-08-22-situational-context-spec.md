# Situational context ("meta context") — spec

_Design session, 2026-08-22. Not yet built. One of three specs from the same
session — see also
[timers/reminders](2026-08-22-timers-reminders-spec.md) and
[tool-discovery](2026-08-22-tool-discovery-spec.md)._

## The idea, in one line

Every time Eva receives *anything* — a message from you, a check-in nudge, a
timer firing, an HA-triggered check-in — she should also see a small bundle of
live situational facts: current time, date, day of week, weather, your phone's
location (named if it's somewhere you've configured in HA, otherwise just "out
and about"), what's playing on Spotify, what's running on Steam. This needs to
be **ephemeral** — visible for that turn, refreshed before the next one, and
never written into the permanent conversation transcript.

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
| Weather | HA (weather entity, already integrated) | reuse the existing Letta→HA MCP path, or pull it server-side in eva-web directly — cheaper to do server-side than via a tool call |
| Location | HA `device_tracker`/`person` entity | named zone if inside a configured HA zone, otherwise generic "out and about" (deliberately not raw coordinates — privacy-conscious default, matches the "just on the go" framing from the original ask) |
| Spotify now-playing | needs a live source — **not yet confirmed** | HA's Spotify integration may expose current track as a media_player entity; confirm before assuming this is free |
| Steam activity | **HA has it** (confirmed 2026-08-22) | user checked — HA already exposes what's needed, no separate Steam Web API integration required. Confirm the exact entity/attribute at build time. |

Two fields (Spotify, Steam) need a source confirmed before this is buildable
end-to-end — see open questions below. Time/date/weather/location can ship
first as a smaller v1 if the other two need more research.

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

## Open questions for build time

- **Spotify:** does HA's integration expose "currently playing" in a way
  that's queryable without user-specific OAuth juggling on eva-web's side, or
  does this need Spotify's own Web API with its own token flow? Check the HA
  integration first — reusing infra beats a second OAuth dance.
- **Steam:** confirmed available via HA (no separate Steam Web API needed) —
  identify the exact entity id and which attribute carries "currently
  playing" at build time.
- **Weather:** which HA weather entity/integration is actually configured —
  confirm the entity id and what fields it exposes (condition, temp) before
  writing the formatter.
- **Zone naming for location:** confirm which HA zones are already configured
  (home, work, etc.) vs. need adding, and decide the exact "out and about"
  fallback wording so it reads in-character, not robotic.
- Token cost: once all fields are in, sanity-check the block's rendered size —
  it's paid on every single turn, unlike a tool call that's only paid when
  invoked.
