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

## Open questions for build time

All five source fields are now confirmed (see table above) — nothing left to
research on the "does the data exist" front. What's left is build mechanics:

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
