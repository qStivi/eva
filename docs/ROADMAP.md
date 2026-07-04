# Eva — roadmap / backlog

Living list of what's next, roughly ordered. Updated 2026-07-04.

## Done
- Character-first **Flutter app** (chat, notebook, "her", settings) — responsive
  phone + desktop layouts.
- **Native targets:** Android APK (on-device) + universal Linux **Flatpak**.
- **Live Letta wiring:** real chat, model switcher, notebook; configurable server.
- **Web search** for Eva (SearXNG + MCP) — she searches and cites, server-side, so
  it works from the phone too.

## In progress
- **Markdown rendering** in chat — Eva emits markdown (bold, headings, lists); render
  it properly, with her `*stage directions*` styled as quiet lavender italics.

## UI polish (small, batched)
- **"Searched the web" indicator** — surface when Eva used a tool (the app already
  parses tool names, just doesn't show them).
- **Bottom-anchor the chat** — messages sit above the composer instead of floating
  at the top with dead space.
- **Android launcher icon** from Eva's portrait (currently Flutter's default).

## Capabilities
- **Home Assistant integration** *(wanted)* — to-do list + home automation. Almost
  certainly an MCP tool (HA has a REST/WebSocket API + an official MCP server);
  gives Eva real control over the house and a shared todo list.
- **More MCP tools** as needs arise (the SearXNG pattern is repeatable).
- ~~Journal / Logseq tool~~ — **dropped**: the backend (memory + tools) covers this.

## The big arc — "Eva with hands, working in the background"
- **Eva delegates to Claude Code** — instead of raw bash (scary), an MCP tool that
  hands a task to `claude -p "<task>"` and returns the result. Powerful executor with
  its own guardrails. Needs **human-in-the-loop approval**.
- **Sub-agents / background tasks + check-ins** — Eva kicks off work, you keep
  chatting, she reports back or **notifies** you (needs async execution + a push
  channel to the app — the reason native mobile matters).
- **Sleep-time memory consolidation** (Letta `enable_sleeptime`) — a background brain
  that tidies memory; A/B a faithful model vs. a lean one.

> These three converge on the same infrastructure (async execution + notifications +
> HITL), so they deserve a dedicated planning session before building.
