# Tool-use transparency ("what did she actually do") — spec

_Design session, 2026-08-22. Not yet built. Fourth spec from the same
session — see also
[timers/reminders](2026-08-22-timers-reminders-spec.md) (built),
[tool-discovery](2026-08-22-tool-discovery-spec.md) (built) and
[situational-context](2026-08-22-situational-context-spec.md)._

## The idea, in one line

A collapsible disclosure under each of Eva's turns — *"3 tools used · thought
for 12s"* — that expands to show her reasoning and every tool call (name,
arguments, result), the way Claude Code/claude.ai show their own tool-use
trace. Prompted by watching a real tool-discovery bug live today: without
this, "she didn't find anything" was a black box until I went and read
Letta's raw message log by hand.

## What already exists (the precedent this extends)

`flutter/lib/widgets/message_bubble.dart` already has a "quiet tag" —
`_toolTag`, a small icon+label row under Eva's bubble — but it's narrow in
every direction:
- **Hardcoded allowlist** (`_toolTags`): only `searxng_web_search` ("searched
  the web") and `web_url_read` ("read a page") get a tag at all. Anything
  else Eva calls (`GetLiveContext`, `HassTurnOn`, `create_timer`, the new
  `search_tools`/`call_tool`...) is silently invisible today.
- **Not expandable** — just a static label, no arguments, no result, no
  reasoning text.
- **Only wired for the live send path**, not history — `LettaApi.history()`
  currently filters the raw Letta message list down to *only*
  `user_message`/`assistant_message`, discarding `reasoning_message`/
  `tool_call_message`/`tool_return_message` entirely. Reload the app and
  every trace from before that moment is already gone.

This feature replaces the narrow tag with something that (a) covers every
tool, not a hardcoded few, (b) is inspectable, not just a label, and (c)
survives a reload, since it comes from history the same way live turns do.

## Where the data already lives

Nothing new needs to happen on the Letta/eva-task-runner side — the raw data
is already there every time. A Letta turn's response (`POST
/v1/agents/{id}/messages`, live) and its history (`GET
/v1/agents/{id}/messages`) both return the same interleaved sequence:
`reasoning_message` → `tool_call_message` → `tool_return_message` →
(repeat) → final `assistant_message`. Verified today, live, e.g.:

```
reasoning_message -> None
tool_call_message -> {'name': 'search_tools', 'arguments': '{"query": ...}'}
tool_return_message -> {"matches": [...]}
reasoning_message -> None
tool_call_message -> {'name': 'call_tool', 'arguments': '{"name": "GetLiveContext", ...}'}
tool_return_message -> {...}
assistant_message -> "..."
```

(`reasoning_message.content` was `None` in these examples — gpt-oss-20b's
tool-calling turns don't always populate visible reasoning text; the UI needs
to handle an empty/absent reasoning gracefully, not assume it's always there.)

## What changes concretely

**eva-web** (`letta_send`/`run_turn`, the live-send path used by `/api/chat`):
currently collapses the raw message list down to `(reply, tools, usage)`,
throwing away everything except tool *names* for the tag allowlist. Extend
this to build an ordered trace list —
`[{"type": "reasoning"|"tool_call"|"tool_return", ...}, ...]` — and include it
in the `/api/chat` JSON response alongside `reply`.

**`LettaApi`** (Flutter): `sendMessageViaWeb` already parses `tools` out of
the same response — extend `LettaReply` to also carry the trace.
`history()`'s message-type filter needs to stop discarding
`reasoning_message`/`tool_call_message`/`tool_return_message` — group them
under whichever `assistant_message` they precede (a "turn" = everything from
one `user_message`/nudge up to the next `assistant_message`), same shape as
the live path so history and live turns render identically after a reload.

**Flutter UI**: replace `_toolTag`'s static row with a tappable summary line
— *"3 tools used · thought for 12s"* (omit either clause if there's nothing
to show: a plain-text reply with no tool calls needs no disclosure at all,
matching Claude's behavior of not showing an empty affordance). Tapping
expands an inline panel (not a separate screen) showing, in order:
- Reasoning text, if present, in a quiet/italic style consistent with Eva's
  existing "aside" typography (`message_bubble.dart` already has this look
  for stage-direction asides — reuse it).
- Each tool call: name, arguments (compact, readable — not raw JSON dumped
  verbatim), and its result/error.

Timing ("thought for Ns"): no field for this exists yet anywhere in the
pipeline. Simplest source is eva-web timing its own call to Letta
server-side (wall clock around the `/v1/agents/{id}/messages` POST) and
including it in the trace — cheap, no dependency on Letta exposing anything
new. For history (already-elapsed turns), message timestamps
(`date` field, confirmed present on every message type) can reconstruct it:
first message's `date` to the final `assistant_message`'s `date`.

## Open questions for build time

- **Payload size for history.** `history()` currently fetches ~60 messages
  and returns lean `HistoryMessage`s; carrying full traces (especially tool
  results, which can be large — e.g. `GetLiveContext`'s ~400-entity dump seen
  today) makes each history load noticeably heavier. Consider truncating
  large tool-return bodies in the trace (with a "truncated" marker) rather
  than shipping them in full — the point is transparency into *what* she
  called and roughly *what came back*, not a full data dump.
- **Formatting tool args/results readably.** Raw JSON is functional but ugly
  inside a chat bubble — worth a light formatter (key: value lines, or at
  least pretty-printed JSON with wrapping) rather than a single dense line.
- **What counts as "a tool"** for the summary count — does `search_tools`
  itself count separately from the `call_tool` it led to, or does the UI
  collapse a search+call pair into one logical step? Leaning toward counting
  every actual tool call literally (simpler, matches what really happened),
  but worth deciding once it's on screen and something to actually look at.
- Visual: confirm the collapsed summary line's placement/style relative to
  the (now-generalized, no-longer-hardcoded) reasoning disclosure — one
  combined affordance, not two separate rows competing for attention.
