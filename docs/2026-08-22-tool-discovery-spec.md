# Tool discovery — spec

_Design session, 2026-08-22. Not yet built. One of three specs from the same
session — see also
[timers/reminders](2026-08-22-timers-reminders-spec.md) and
[situational-context](2026-08-22-situational-context-spec.md)._

## The problem with today's system

Today, tool availability is handled by `eva-web/toolset_router.py`
(`preload_for(...)`): before forwarding a message to Letta, eva-web scans it
against `toolsets.json`'s `keywords` and pre-attaches whichever groups matched,
on the theory that Letta only starts letting a *newly-attached* tool actually be
called on the **next** turn, not the one it's attached during (see
`eva-lazy-toolsets` memory). It works, but it's a heuristic guess made *before*
Eva ever sees the message — it can miss (a keyword that isn't in the list) or
over-attach (a keyword that matches but isn't what was meant).

Now that Eva can loop — chain multiple tool calls within a single incoming
message via Letta's continuation/heartbeat mechanism — there's a cleaner
architecture available that doesn't need to guess at all.

## The idea, in one line

Give Eva exactly two **permanent, always-attached** tools instead of a growing
pile of pre-gated groups:

- `search_tools(query: str) -> list[{name, description}]`
- `call_tool(name: str, args: dict) -> result`

Both are server-side dispatch, not real Letta tool attachment/detachment.
`search_tools` always searches the **full** registry (everything in
`toolsets.json`'s groups, flattened) and returns whatever matches — no
pre-filtering, no keyword-list-goes-stale risk. `call_tool` looks up `name` in
the same registry and invokes it. Since neither tool is ever attached or
detached, there's no next-turn lag to design around — Eva can search and call
within the same turn, which the looping capability now supports.

## Why this beats fixing the keyword list

- **Correctness, not coverage.** The current failure mode is "the keyword list
  missed a phrasing." A search-based lookup (even simple substring/fuzzy
  matching over tool name + description first; upgrade to embeddings only if
  that proves too weak in practice) degrades gracefully instead of silently
  missing.
- **No attach/detach bookkeeping.** `preload_for` mutates which tools are
  attached to the agent per-request; `search_tools`/`call_tool` never touch
  Letta's tool attachment at all, so there's nothing to get out of sync.
- **Keeps the 20B context-size problem solved.** The whole reason lazy loading
  exists is that dumping every HA/research tool schema into context at once
  slows the daily-driver model down. This still only ever exposes *two* tool
  schemas to the model at all times — the registry itself lives server-side and
  never enters context except as search results (short name+description pairs)
  and call results.

## What changes concretely

- `toolsets.json` stops being "keyword-gated groups to pre-attach" and becomes
  purely the tool **registry** — flatten `groups` into one name→description
  index for `search_tools` to search over. `index` (persona-facing group
  blurbs) and `keywords` (the pre-load heuristic) both become dead weight and
  get removed once this ships.
- `core` tools (`memory_insert`, `GetDateTime`, the todo-list Hass tools, etc.)
  stay permanently attached as today — they're cheap and used constantly
  enough that a search round-trip for them would be pure overhead. Only the
  *gated* groups (`home`, `media`, `house_extras`, `research`) move behind
  `search_tools`/`call_tool`.
- `eva-web`'s `toolset_router.py` shrinks to just resolving `call_tool`
  dispatch (look up the real Letta tool, invoke it, return the result) —
  `preload_for`'s keyword-matching logic goes away entirely.
- Actual invocation: `call_tool` still has to reach the real underlying
  tool (an HA MCP tool, `research_task`, etc.) — this is the part that needs
  the most care at build time, since those are normally invoked by Letta
  itself, not proxied. Worth checking whether Letta exposes a "call this tool
  by name against this agent" API that doesn't require the tool to be attached
  first, or whether `call_tool` needs to attach-then-immediately-call-then-detach
  under the hood (which would reintroduce the next-turn problem unless the
  attach happens *before* the model's turn starts, e.g. eagerly on
  `search_tools`— worth prototyping both before committing).

## Open questions for build time

- Confirm (prototype, don't assume) whether Letta's API supports invoking a
  tool that isn't currently attached to the agent — this is the crux of
  whether `call_tool` is a clean passthrough or needs the eager-attach dance.
- Search quality: start with simple case-insensitive substring/word matching
  over name+description (matches the existing `keywords` list's simplicity);
  only reach for embeddings if real usage shows it's too weak.
- Whether `search_tools` results should be capped/ranked, given the registry
  will keep growing (timers' `create_timer`, future tools, etc.).

## Follow-up (2026-08-22, building Phase 2): the model still calls gated
tools directly, not through `call_tool`

Confirmed live, twice, testing `delegate_to_harness`: Eva sometimes calls a
gated tool **by name directly** — skipping `call_tool` entirely, even right
after `search_tools` found it — and gets Letta's own `ToolConstraintError`.
The error's own message ("Cannot call X, valid tools include: [...]") gave
her nothing to self-correct from; she read it as "the tool is broken" and
told Stephan so, offering a manual workaround instead of retrying correctly.

**Fix, live 2026-08-22:** a local patch to Letta's own error builder
(`_build_rule_violation_result` in `letta/agents/helpers.py`) — bind-mounted
via `~/.config/letta/helpers.py` (not checked into this repo; same pattern
as `openai_client.py`/`url_validation.py`, see `letta.container`'s Volume=
lines). Whenever a rejected tool isn't a real *rule* violation (no
`hint_lines` from Letta's own `ToolRulesSolver`) and `call_tool`/`search_tools`
are both in the agent's valid set, appends a hint pointing straight at
`call_tool(name=..., args={...})`. General — not hardcoded to
`delegate_to_harness`, applies to any gated tool.

**Confirmed live end-to-end (2026-08-22, after migrating eva-spike off
LM Studio onto `mistral-small-latest`):** forced the exact original failure
(told her explicitly to call `delegate_to_harness` directly, bypassing
`call_tool`) — got the hint verbatim in the tool return. Next turn, unprompted
("ok, now actually get that file created for real"), she switched to
`call_tool(name='delegate_to_harness', args={'task': ...})` on her own and it
worked. Real self-correction, not just a rendering check.

**Unrelated gotcha hit during that same migration**, worth remembering:
switching an agent's model to Mistral while its message history still has
old `reasoning_content` from a different model (qwen3-8b, via LM Studio) 422s
— `extra_forbidden` on `reasoning_content`, same failure family as the
2026-08-13 Mistral BYOK bug and the harness `thinking` bug, but a third
distinct field this time, coming from historical message replay rather than
a live request. Not patched (Letta's serialization would need a fix to strip
it per-provider) — worked around by resetting eva-spike's message history
(`PATCH /v1/agents/{id}/reset-messages`), reasonable since it's the
throwaway test agent. Anyone else migrating an agent's provider mid-
conversation should expect this if the prior model wrote reasoning content.
