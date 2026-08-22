# Eva admin panel — spec

_Design session, 2026-08-22. Not yet built. Fifth spec from the same
session — see also
[timers/reminders](2026-08-22-timers-reminders-spec.md) (built),
[tool-discovery](2026-08-22-tool-discovery-spec.md) (built),
[situational-context](2026-08-22-situational-context-spec.md), and
[tool-trace transparency](2026-08-22-tool-trace-transparency-spec.md)._

## The idea, in one line

A small web panel for *managing* Eva — memory blocks, tool
attachment/registry state, a live/historical tool-call trace across the whole
agent — the things Letta's own visual ADE would normally cover, if it worked
against a self-hosted server. It doesn't: confirmed today, directly from
Letta's docs and GitHub repo, that there's no documented path connecting
`chat.letta.com` or the desktop app to a self-hosted instance like Eva's
("Self-hosted agents cannot be accessed through chat.letta.com" — an explicit
statement in their docs, not a config gap). This is for Stephan only — an
admin surface, not something Eva's conversational app exposes.

## Why this is worth building rather than living without

Most day-to-day management is already covered without any UI:

| Need | Already covered by |
|---|---|
| Persona edits | `persona/eva.md` + `scripts/sync-persona.sh` |
| Tool attachment / toolset groups | `toolsets.json` + `scripts/register-toolsets.sh` |
| Check-in schedule | Real UI already, in the Flutter app's settings screen |
| One-off API poking | Swagger UI at `localhost:8283/docs` |

What's genuinely missing, confirmed by real friction today:
- **Reading a memory block's live current value** without opening the source
  file and trusting it's actually what got synced (drift is possible — the
  file could be edited without re-running the sync script, or a block could
  get written to directly via the API, bypassing the file entirely).
- **Browsing a tool-call trace across the whole agent**, not just the last
  ~60 messages a phone app cares about. Today's `search_tools` bug was
  diagnosed by hand-pulling and reading Letta's raw message JSON over curl —
  workable, but exactly the kind of thing a real panel should make instant.
- **Seeing exactly what's attached to an agent right now** without a script
  round-trip (`curl .../tools`) — useful for eva-spike too, which has
  accumulated an ad-hoc set of test tools over this session with no single
  place that shows it.

## Scope

**In scope (v1):**
- **Memory blocks** — list all blocks on an agent (persona, human, and once
  built, `situational_context`), view current value, edit and save (i.e. a
  UI wrapper around the same `PATCH /v1/agents/{id}/core-memory/blocks/{name}`
  `sync-persona.sh` already uses).
- **Tools** — list everything attached to an agent, and separately the full
  Letta tool registry (`GET /v1/tools/`) so it's obvious what's registered vs.
  attached. Read-only for v1 — attach/detach stays script-driven
  (`toolsets.json` is the source of truth; a UI that can silently drift from
  it is worse than no UI).
- **Trace viewer** — browse an agent's message history with the full
  reasoning/tool-call/tool-return detail, not the collapsed
  `user_message`/`assistant_message`-only view the phone app needs. This
  shares real ground with the
  [tool-trace transparency spec](2026-08-22-tool-trace-transparency-spec.md)
  — same underlying data shape (interleaved `reasoning_message`/
  `tool_call_message`/`tool_return_message`), different audience (admin,
  full history, every agent vs. app, current conversation, Eva's real agent
  only). Worth building the parsing logic once and sharing it if both end up
  built, rather than solving the same problem twice.
- **Agent picker** — switch between `eva` and `eva-spike` (and any future
  throwaway test agents) from one place, since this session repeatedly needed
  to check both.

**Explicitly out of scope (v1):** creating/deleting agents, editing
`toolsets.json` membership through the UI (stays file+script — see above),
anything that writes into Eva's actual conversation (no "send a message as
Eva" or similar from the admin side — that's what the real app is for).

## Where this lives

Extending **eva-web** is the natural home — it already has the Basic-auth
gate, already proxies to Letta, and already has a `/api/*` pattern for
non-chat routes (`/api/checkin/*`). A separate `/admin/*` path, same Basic
auth (or a second, stricter credential if v1's edit capability makes that
feel warranted — decide at build time), LAN-only like the rest of eva-web's
UI surface (never on the Cloudflare tunnel — this is more sensitive than
chat, since it can edit memory directly).

Server-side, this is mostly thin proxying to Letta's own API
(`/v1/agents/{id}/core-memory/blocks`, `/v1/agents/{id}/tools`,
`/v1/agents/{id}/messages`, `/v1/tools/`) — no new data model of its own.

## Open questions for build time

- **Auth strength for the edit path.** Read-only browsing is low-risk; a
  memory-block *write* through a web form is a real way to corrupt Eva's
  persona/state if the panel itself is ever compromised or fat-fingered.
  Worth deciding whether the existing eva-web Basic auth is enough, or this
  wants a second factor/confirmation step.
- **Shared trace-parsing code with the tool-trace transparency spec** — if
  both get built, decide whether the admin panel consumes the same
  eva-web-side trace-building code the chat feature uses, or they stay
  independent (the audiences differ enough that some divergence is fine, but
  the core "walk the message list and group reasoning/tool_call/tool_return
  under an assistant_message" logic shouldn't be written twice).
- **How much of Letta's Swagger UI this actually needs to replace.** If the
  honest answer after building v1 is "I still reach for `/docs` half the
  time," that's a sign to scope down rather than keep adding — this exists to
  remove specific friction points hit in practice, not to be a full Letta
  client reimplementation.
