# Letta core patches

Three full copies of Letta modules, each with a small local fix applied, bind-mounted
over the corresponding file inside the running `letta` container (see
`~/.config/containers/systemd/letta.container`'s `Volume=` lines — not itself in this
repo, since it also holds `EnvironmentFile=` secrets; see
`docs/2026-08-24-homelab-how-to-run.md` for how that unit file travels).

These are **full replacement copies of the upstream file**, not diffs — Letta ships as a
container image, so there's no way to apply a small patch on top; the whole module gets
swapped out via a read-only bind mount at the same path Letta imports it from. That means
each file needs re-diffing against upstream on every Letta version bump (a `git diff`
against a fresh copy of the same file from the new image is the fastest way to check
whether the underlying file changed enough to need re-applying the fix).

| File | Real path inside the container | What it fixes |
|---|---|---|
| `url_validation.py` | `/app/letta/helpers/url_validation.py` | Letta's stock MCP URL validator rejects all non-global IPs, so it refuses to connect to a self-hosted MCP on loopback/LAN (our SearXNG MCP at `127.0.0.1:3010`). Patched to permit loopback/private targets while still blocking link-local/cloud-metadata (`169.254.0.0/16`, `fe80::/10`). See `~/lmstudio-searxng-websearch.md` (desktop-only notes) and the `lmstudio-searxng-web-search` memory. |
| `openai_client.py` | `/app/letta/llm_api/openai_client.py` | Letta's OpenAI-compatible client unconditionally sets a `user` field on every request, even for non-OpenAI BYOK providers routed through the same code path (e.g. Mistral, `model_endpoint_type="openai"`). Mistral's stricter schema 422s on that (`extra_forbidden: body.user`). Patch guards both call sites with a `provider_name` check, the same pattern Letta already uses elsewhere in this file for other OpenAI-specific fields. No upstream fix as of the date this was written (2026-08-13). |
| `helpers.py` | `/app/letta/agents/helpers.py` | `ToolConstraintError`'s own message (a tool rejected because it isn't attached, not a rule violation) gave the model nothing to self-correct from — confirmed live that Eva reads it as "the tool is broken" and gives up instead of retrying via `call_tool`, even right after `search_tools` found the exact tool. Patch adds a hint pointing at `call_tool(name=..., args=...)` whenever `search_tools`/`call_tool` are both in the agent's valid tool set. See `docs/2026-08-22-tool-discovery-spec.md` and the `eva-testing-use-spike-agent` memory. |

## Wiring these up on a new host

The Quadlet unit (`letta.container`) expects these at `~/.config/letta/*.py` on the host,
bind-mounted read-only into the container. `scripts/homelab-ct-setup.sh` copies them
there automatically from this directory after cloning the repo — no manual step needed,
unlike the actual secrets (`letta.env` etc.), which are deliberately kept out of git.
