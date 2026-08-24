# Moving eva's backend to the homelab Proxmox host

Goal: always-on reliability. Right now eva's whole backend (Letta, eva-task-runner,
eva-web, SearXNG+MCP, the Cloudflare Tunnel) lives on the gaming desktop, so it goes down
whenever that machine reboots or sleeps. The homelab Proxmox host (see
`homelab-proxmox-topology` memory / Confluence "/root Admin Directory (Proxmox Host)")
is a better home: it's already the always-on box everything else (Home Assistant, n8n,
Grafana, ...) lives on.

This was reachable only after two things happened earlier this session/recently: eva's
"brain" moved off local LM Studio to cloud-routed Mistral models, and eva-spike was
migrated to a cloud model too. The one remaining local-GPU dependency — embeddings — is
addressed below.

## What's moving, what's not

Not GPU-bound, moves as-is:
- **Letta** (Quadlet container, host networking, named Postgres volume `letta_pgdata`,
  3 bind-mounted local patch files)
- **eva-task-runner** (`runner.py` + `executors/`, stdlib-only except `cryptography` for
  FCM JWT signing; SQLite job DB at `~/.local/share/eva/tasks.db`; scratch dir
  `~/eva-workspace`; needs Node on PATH for `dsh`)
- **eva-web** (`app.py` + friends, stdlib-only Flask... actually stdlib `http.server`
  style, no framework deps found)
- **SearXNG + SearXNG MCP** (2 rootless Podman Quadlets, already portable)
- **Cloudflare Tunnel** (`cloudflared-eva.container` — host networking, reaches Letta's
  `:8283` locally; the tunnel config itself doesn't change, it just needs to run
  co-located with Letta on the new host)

Retired, not migrated:
- **`eva-lmstudio-status.service`** (loopback `:8285`, reports LM Studio's model-load
  state to the app) — becomes dead code once nothing depends on local LM Studio anymore.
  Remove the systemd unit and whatever calls it in the Flutter app / eva-web.

Changing:
- **Embeddings** — currently all 4 agents (`eva`, `eva-spike`, and their sleeptime
  agents) point at `http://localhost:1234/v1`, `text-embedding-nomic-embed-text-v1.5`
  (LM Studio, GPU-accelerated on this desktop). The homelab host has no GPU. Rather than
  standing up a CPU-only LM Studio/Ollama over there (adding yet another host process to
  keep alive), switch to Mistral's own embedding API (`mistral-embed`).

  **Resolved (2026-08-24), traced through this Letta version's actual source in the
  running container, not assumed from docs:** `embedding_endpoint_type: "mistral"` is a
  valid schema value, but `LLMClient.create()`'s factory has no dedicated Mistral case —
  it falls through to the generic `OpenAIClient`, which just POSTs to whatever
  `embedding_endpoint` you give it. That much works cleanly. The real gotcha:
  `OpenAIClient._prepare_client_kwargs_embedding()` does **not** do the BYOK
  provider-key lookup that chat requests get — it unconditionally authenticates with
  `OPENAI_API_KEY` (env var / `model_settings.openai_api_key`), regardless of
  `embedding_endpoint_type`. So pointing `embedding_endpoint` at Mistral alone would
  401; the fix is to repurpose `letta.env`'s `OPENAI_API_KEY` to hold the real Mistral
  key once LM Studio is retired (nothing else will need that var at that point). Final
  per-agent `embedding_config`:
  ```json
  {
    "embedding_endpoint_type": "mistral",
    "embedding_endpoint": "https://api.mistral.ai/v1",
    "embedding_model": "mistral-embed",
    "embedding_dim": 1024,
    "embedding_chunk_size": 300
  }
  ```
  `embedding_dim: 1024` is Mistral's documented `mistral-embed` output size — confirm
  with one real embedding call before it goes into any agent config, since a wrong
  `embedding_dim` breaks vector storage outright rather than failing softly.

## Step-by-step

### 1. Provision the CT
Next free ID after the current highest (140) — call it **141**. Debian or Ubuntu
(matches the rest of the homelab's CTs), with:
- `podman` + `systemd --user` lingering enabled (`loginctl enable-linger <user>`) — same
  rootless Quadlet pattern already used on the desktop.
- Node.js + `npm install -g @deepseek-ai/dsh` — on a normal CT (not an atomic-OS host)
  this can just go through the distro's package manager or nodesource, no Homebrew
  detour needed.
- Python 3 + `pip install cryptography` (the one real third-party dependency across
  eva-task-runner/eva-web).
- `git` (to clone/pull the `eva` repo).

Check `STORAGE_DOCS.md` on the Proxmox host first for free space before sizing the CT —
Letta's Postgres + job DB + workspace scratch files aren't large, but confirm rather than
assume.

### 2. Prove the embedding swap on eva-spike first
Following the established "test on eva-spike, never live eva" discipline, using the
`embedding_config` resolved above:
1. Repoint `letta.env`'s `OPENAI_API_KEY` at the real Mistral key (see "Changing" above
   for why this is safe — nothing else uses that var once LM Studio is retired) and
   restart `letta.service`.
2. `PATCH /v1/agents/eva-spike` (and `eva-spike-sleeptime`) with the `embedding_config`
   block above.
3. Exercise something that triggers a real embedding call (recall/memory search) against
   eva-spike and confirm it works before touching live `eva`/`eva-sleeptime` — also
   confirms the `embedding_dim: 1024` guess against a real response.
4. Only after that succeeds, repeat on the live agents.

### 3. Migrate Letta's data
This is the only step with real state to carry over carefully:
1. On the desktop: `podman exec letta pg_dump -U <user> <db> > letta.sql` (or tar the
   `letta_pgdata` volume directly — either works, `pg_dump` is safer across Postgres
   versions).
2. Copy `letta.sql` (or the volume tar) to the new CT over SSH/SCP.
3. Also copy the 3 local patch files (`~/.config/letta/{url_validation.py,
   openai_client.py,helpers.py}`) and `~/.config/letta/letta.env` (contains the LM
   Studio `OPENAI_API_BASE`/`OPENAI_API_KEY` — these become obsolete/removable once the
   embedding swap lands, since nothing will call local LM Studio anymore).
4. Bring up `letta.container` on the new CT, restore the dump, verify agents list/query
   correctly before decommissioning the old instance.

### 4. Migrate everything else
- `eva-task-runner`: clone the repo, copy `~/.config/eva-task-runner/eva-task-runner.env`,
  copy the FCM service-account JSON (`FCM_SERVICE_ACCOUNT_FILE`), copy
  `~/.local/share/eva/tasks.db` (job history — not critical if lost, but no reason to
  drop it), copy `~/eva-workspace` if there's anything worth keeping in it.
- `eva-web`: clone the repo (same checkout), copy `~/.config/eva-web/eva-web.env`.
- SearXNG + MCP: copy the two `.container` files + `searxng.network` +
  `~/.config/searxng/settings.yml`.
- Cloudflare Tunnel: copy `cloudflared-eva.container` + `~/.config/cloudflared/eva.env`
  (the `TUNNEL_TOKEN`) — same token, same tunnel, just running from a new host. No
  Cloudflare-side route change needed since the tunnel always talked to `localhost:8283`
  relative to wherever it runs.
- Re-create the systemd user units (`eva-task-runner.service`, `eva-web.service`) on the
  new CT, pointing `WorkingDirectory`/`ExecStart` at the new checkout path.

### 5. Cutover
Because Letta's Postgres data is live and mutating, do the actual switch as a short,
deliberate freeze rather than a live sync:
1. Stop all eva services on the desktop (`systemctl --user stop letta eva-task-runner
   eva-web cloudflared-eva searxng searxng-mcp`).
2. Take a final `pg_dump` (step 3.1) to capture anything since the first copy.
3. Restore that final dump on the new CT, start everything there.
4. Point the Flutter app's server URL at... actually nothing changes here if the
   Cloudflare Tunnel hostname (`eva.qstivi.com`) stays the same — the app talks to that
   hostname regardless of which host is behind the tunnel. Just confirm a real message
   round-trips before calling it done.
5. Retire the desktop-side systemd units and Quadlet files (or just leave them disabled
   — no rush to delete).

### 6. Cleanup
- Remove `eva-lmstudio-status.service` and its LAN-status caller in the app.
- Once confirmed stable, LM Studio itself no longer needs to autostart for eva's sake
  (it may still be wanted for other projects on this desktop — ComfyUI, TTS — check
  before disabling anything there).

## Open questions to resolve before starting
- Whether to keep the Cloudflare Tunnel as the sole ingress (current setup, Access-gated,
  already proven) vs. also registering the new CT behind Nginx Proxy Manager on
  `*.lab.qstivi.com` for LAN-only access — not required, just an option since NPM is
  already there.

## Resource budget (confirmed 2026-08-24, from Confluence "/root Admin Directory")

Live snapshot of the Proxmox **host itself** (point-in-time, not the CT's own future
resources — this is what a new CT would be carved out of and share):

| Resource | Value | Verdict for a new eva CT |
| --- | --- | --- |
| CPU | Intel i3-8100T, 4 cores/4 threads **total for the whole host** | Shared with every other guest (MariaDB, NPM, n8n, HA, Grafana, Minecraft, ...). Fine for eva's actual workload — chat/embeddings are network calls to Mistral now, not local compute — but `dsh`/harness job bursts will contend with the rest of the host. No dedicated headroom to assume. |
| RAM | 31 GiB total, 17 GiB free / 20 GiB available | Comfortable — Letta+Postgres+eva-task-runner+eva-web+SearXNG+MCP is a light footprint. |
| Host root partition (`/`) | 64 GB, only 11 GB free (83% used) | Tight, but this is the **host's own** `/`, not the CT's disk — only matters for template downloads/ISOs landing there. |
| VG `pve` | 222 GB, ~4 MB free — **fully allocated** | Can't provision a classic LV; a new CT's disk has to come from the thin pool instead (normal for `pct create`, just don't try to allocate a plain LV manually). |
| Thin pool `pve/data` | 145.85 GB, 73.63% used, ~38.5 GB free headroom | Real room exists here for a new CT's rootfs — eva's data (Postgres + SQLite job DB + workspace scratch) is nowhere near 38 GB, so this isn't a tight fit. |

Net: no resource blocker. Size the new CT modestly (a few GB disk, 2 GB RAM would be
generous) rather than over-provisioning against a host that's already CPU-constrained
and has limited thin-pool headroom shared with everything else.
