# Eva — roadmap / backlog

Living list of what's next, roughly ordered. Updated 2026-07-21.

## Done
- Character-first **Flutter app** (chat, notebook, "her", settings) — responsive
  phone + desktop layouts.
- **Native targets:** Android APK (on-device) + universal Linux **Flatpak**.
- **Live Letta wiring:** real chat, model switcher, notebook; configurable server.
- **Web search** for Eva (SearXNG + MCP) — she searches and cites, server-side, so
  it works from the phone too.
- **Markdown rendering** in chat *(2026-07-21)* — committed Eva turns render markdown
  (bold, headings, lists, code), her `*stage directions*` as quiet lavender italics;
  the live typewriter keeps its plain-text + caret path.
- **"Searched the web" indicator** *(2026-07-21)* — Eva's turns show a quiet tag when
  she used a user-facing tool (`searxng_web_search` → "searched the web",
  `web_url_read` → "read a page"); internal memory/conversation tools stay hidden.
- **Bottom-anchor the chat** *(2026-07-21)* — messages sit above the composer instead
  of clinging to the top with dead space below.
- **Android launcher icon** *(2026-07-21)* — Eva's portrait on the Catppuccin-crust
  background (legacy + adaptive), replacing Flutter's default mark.
- **Home Assistant integration** *(2026-07-21)* — Eva keeps the shared todo/shopping
  list and controls exposed devices (lights, media, climate, sensors) via HA's built-in
  **Model Context Protocol Server** (SSE), registered in Letta like the SearXNG MCP.
  `scripts/register-ha-mcp.sh` + a persona directive ("the house, and your list").
  Token in chmod-600 `~/.config/letta/ha.env`. Verified: reads + writes the list live.
- **Lazy toolset loading** *(2026-07-21)* — Letta eager-loads every attached tool each
  turn (slow + worse tool-picking), so Eva keeps a lean **core** (~11) and domain tools
  live in groups (`home`, `media`, `house_extras`) in `toolsets.json`. Because Letta only
  surfaces newly-attached tools *next* turn, `eva-web/toolset_router.py` pre-attaches the
  right group from the message (keyword intent) in eva-web + the `eva` CLI, so tools are
  present from turn start. `scripts/register-toolsets.sh` applies the scheme;
  `tools/use_toolset.py` is a model-facing fallback. Verified: one-turn house reads.

## Capabilities
- **More MCP tools** as needs arise (the SearXNG pattern is repeatable).
- **Cloud escalation** *(decided 2026-07-21)* — keep the local model as Eva's default
  brain, but escalate genuinely hard turns to a cloud flagship. Route via **OpenRouter**
  (one OpenAI-compatible endpoint, no per-token markup, ~5.5% top-up fee) so it drops
  into the existing Letta OpenAI-proxy pattern as just another `base_url` + key. Two
  cloud tiers: **standard** (DeepSeek V4 Pro / GLM-5.2 — near-frontier, cheap) and
  **max** (Kimi K3-class, on demand only). Local stays the default; cloud is opt-in per
  hard task, not per message.
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
