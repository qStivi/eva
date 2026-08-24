# Eva Backend Migration to Homelab Proxmox (v2 — revised 2026-08-24)

Revises `docs/2026-08-24-homelab-migration-plan.md`. Changes from v1 are called out inline as **[CHANGED]**.

## Progress log (updated as execution proceeds)

**Done:**
- CT 141 provisioned — **Ubuntu 24.04** specifically (not Debian 13, see note below), unprivileged, no `nesting`/`keyctl` features, confirmed `systemctl is-system-running` → `running` with zero failed units.
- `eva` user created (non-root, lingering enabled via `loginctl enable-linger eva`) — the account everything runs as.
- SSH access set up: Bazzite (desktop) holds the private key and initiates connections *to* CT 141 as `eva`; CT 141 never connects out to the desktop. Dedicated keypair, not the shared `root@proxmox` key.
- Base tooling installed: Python 3.12 + venv + pip + `python3-cryptography`, git, Node.js 22 (NodeSource) + `@deepseek-ai/dsh`, native PostgreSQL 16, native `cloudflared` (Cloudflare's apt repo).
- Secrets/config staged from the desktop (via the Bazzite→CT SSH path) under `~/desktop-secrets-STAGING/` on CT 141: `letta.env`, `eva-task-runner.env` + FCM service-account JSON, `eva-web.env`, `cloudflared/eva.env`, `searxng/settings.yml`.
- Live `pg_dump -F c` (custom format) of the desktop's `letta` database taken with **zero downtime** — desktop eva was never stopped. Staged alongside the other secrets.
- Native Postgres `letta` role + `letta` database created (fresh generated password, not the container image's trivial default `letta`/`letta`).
- Dump restored into native Postgres — verified: 4 agents, 1047 messages, 76 memory blocks, all with real timestamps from the source. `archival_passages`/`source_passages` legitimately empty (matches source; eva's memory relies on the block/conversation system, not archival vector search).
- Letta 0.16.8 installed via pip into `eva`'s venv, all 3 `letta-patches/` applied on top (see below), configs wired into `~/.config/*` on CT 141.
- **Smoke-tested**: `letta server` started manually against the restored DB, confirmed healthy via `/v1/health/` and `/v1/agents/` — real restored agent data (`eva-sleeptime`, etc.) served correctly. Stopped afterward (not yet a proper systemd service).

**Now also done:**
- `eva`/`eva-sleeptime`'s `embedding_config` PATCHed to Mistral (matching the already-proven `eva-spike` shape) via Letta's own REST API, then validated with a real `POST .../archival-memory` call — confirmed a genuine 1024-dim non-zero Mistral vector came back, not just a `200`. Test passage deleted after.
- `LETTA_ENCRYPTION_KEY` generated and set — secrets in Letta's own DB (e.g. the Mistral API key) are now AES-256-GCM encrypted at rest going forward (opportunistic: old plaintext rows are untouched, new writes get encrypted, no migration step needed).
- All 6 systemd `--user` units deployed and verified live: `letta`, `eva-web`, `eva-task-runner`, `searxng`, `searxng-mcp`, `cloudflared-eva`. `eva-web`'s authenticated `/api/health` returns `{"letta": true, ...}`; `eva-task-runner` bound loopback-only on `:8286` as designed; SearXNG returns real JSON search results; the MCP bridge (`mcp-searxng`, installed natively via npm — see below) is visible to Letta via `/v1/tools/mcp/servers/searxng/tools`; `cloudflared` proven live end-to-end with a real request through `eva.qstivi.com` (got a genuine Cloudflare Access 403 challenge page back, not a tunnel error — confirms the tunnel is correctly routing to the CT's origin).
- `eva-task-runner`'s `FCM_SERVICE_ACCOUNT_FILE` path corrected from the desktop's `/home/qstivi/...` to CT 141's `/home/eva/...`.

**SearXNG MCP — also native, not a container.** `searxng-mcp` turned out to be `docker.io/isokoliuk/mcp-searxng` on the desktop, which is just a container wrapper around the `mcp-searxng` npm package (same author, `ihor-sokoliuk`/`isokoliuk`) — installed natively via `npm install -g mcp-searxng` (npm prefix scoped to `eva`'s home, since the global prefix from the NodeSource install isn't writable by non-root). Runs standalone in HTTP-transport mode (`MCP_HTTP_PORT=3010`, loopback-only by default, matching the desktop's posture) rather than the default stdio-spawned-by-client mode. The already-restored DB's `mcp_server` table already pointed at `http://127.0.0.1:3010/mcp` from the original dump — no re-registration needed, just had to actually run something listening there.

**Not yet done:** the actual cutover (desktop is still the live/authoritative system — CT 141 is fully up and independently verified, but running against the mid-August snapshot, not live data).

### Gotchas found during execution (fold into any future rerun)

- **Debian 13 (systemd 257) fails clean boot in unprivileged LXC without `nesting`** on this Proxmox version — confirmed via `systemctl is-system-running` → `degraded`, with `tmp.mount`/`run-lock.mount`/`dev-mqueue.mount` all failing. **Ubuntu 24.04 (systemd 255) boots clean with zero feature flags** — empirically verified, not assumed. This is *not* evidence nesting is required in general (every CT on this host has `nesting=1` regardless of workload, including plain-service CTs like MariaDB — almost certainly just Proxmox's UI/tteck-script default, not a per-CT necessity). **Use Ubuntu 24.04 for CT 141, not Debian 13.**
- **`pgvector` isn't installed by default** — needed both the Postgres extension (`postgresql-16-pgvector` package) and the Python/SQLAlchemy package (`pip install pgvector`). Neither is a `letta` dependency pulled in automatically.
- **The vector extension must be created inside the `letta` schema**, not `public` — the dump's tables reference the type as `letta.vector`. `CREATE EXTENSION vector SCHEMA letta;`, not a bare `CREATE EXTENSION vector;`. Restoring into the wrong schema fails silently on the two passages tables and cascades into FK/index errors that are easy to misread as a bigger problem.
- **`asyncpg` is also required** and not pulled in automatically — Letta's async ORM layer imports it directly even though `settings.py`'s URI-building helper references a `pg8000`-style driver string.
- Postgres dump/restore files must be copied somewhere `postgres`-readable before `pg_restore` — `eva`'s home directory is `700`, invisible to the `postgres` system user.

## Notes on Postgres credentials

Desktop's bundled Letta-container Postgres uses a hardcoded image default (`letta`/`letta`, both user and password) — not something Stephan chose, baked into the image's own env. The native CT 141 instance was set up with a freshly generated password instead (not the trivial default), stored only in `~/.config/letta/letta.env` (`LETTA_PG_PASSWORD`), `600` permissions, `eva`-owned. `LETTA_PG_DB`/`_USER`/`_HOST`/`_PORT` set alongside it — env-prefix confirmed as `LETTA_` from Letta's own `settings.py` (`SettingsConfigDict(env_prefix="letta_")`).

## Primary Objective

Move eva's backend services from a gaming desktop (unreliable, goes down on reboot/sleep) to
an always-on homelab Proxmox host (CT 141), matching uptime of Home Assistant, n8n, Grafana.

## Prerequisites (unchanged)

- Eva's "brain" already runs on cloud-routed Mistral models, not local LM Studio.
- eva-spike already migrated to cloud models.
- Only remaining local-GPU dependency is the embeddings service (addressed below).

## **[CHANGED]** Container strategy: no Podman/Quadlet on CT 141

v1 planned to run Letta, SearXNG+MCP, and Cloudflare Tunnel as rootless Podman Quadlet
containers, matching the desktop setup. That requires the LXC `nesting=1`/`keyctl=1` feature
flags on an otherwise-unprivileged CT — a new pattern for this homelab (no existing CT runs
Podman; the CTs that do run containers, e.g. Wiki.js on CT 105, run Docker with `nesting=1`,
and CT 105 is slated for retirement).

**Decision: go fully native on CT 141. Zero container runtime, zero nesting flag.**

| Service | v1 (desktop-mirrored) | v2 (native) |
|---|---|---|
| Letta | Podman Quadlet container + Postgres volume | `pip install letta` in a venv; native `postgresql` package |
| SearXNG + MCP | Rootless Podman Quadlets | Native pip/uWSGI install |
| Cloudflare Tunnel | Podman Quadlet container | Native `cloudflared` `.deb` + its own systemd unit |
| eva-task-runner | Native Python | Unchanged |
| eva-web | Native Python (stdlib-only) | Unchanged |

Net effect: CT 141 is created as a plain unprivileged LXC container with **no `features:`
flags at all** — no `nesting`, no `keyctl`. Every service on the box is a systemd unit backed
by a venv or a native binary.

## **[UNCHANGED]** Ingress: keep Cloudflare Tunnel

Considered replacing `cloudflared` with Nginx (via NPM/CT 102) for consistency with the rest
of the homelab's ingress pattern. Rejected: Cloudflare Tunnel is outbound-only (no open port
on OPNsense) and Cloudflare Access currently gates auth in front of it — "Access-gated,
proven." Replacing it would require either a public port-forward (increases attack surface,
needs its own TLS/auth story) or a VPN, for a "consistency" gain that isn't worth the tradeoff.
**No change to eva's ingress model.** `cloudflared` moves to CT 141 as a native install (see
table above) rather than staying containerized, but functionally it's identical to today.

## Embedding Swap (unchanged from v1)

Embeddings move from local LM Studio GPU inference
(`http://localhost:1234/v1`, `text-embedding-nomic-embed-text-v1.5`) to Mistral's cloud
embedding API (`mistral-embed`).

Letta's `LLMClient.create()` factory has no dedicated Mistral embedding case, so it falls back
to generic OpenAI-client behavior. Workaround: repurpose `OPENAI_API_KEY` to hold the actual
Mistral key (nothing else needs it post-migration).

Per-agent config:
```
embedding_endpoint_type: "mistral"
embedding_endpoint: "https://api.mistral.ai/v1"
embedding_model: "mistral-embed"
embedding_dim: 1024
embedding_chunk_size: 300
```
`embedding_dim: 1024` was already validated against a live Mistral response on eva-spike per
the 2026-08-24 how-to-run runbook — carries forward unchanged.

## Letta patches — reviewed, native install confirmed clean

The 3 patches live in `letta-patches/` in the repo (README + 3 files). All are plain
Python-source overrides of specific installed Letta module paths — nothing container-specific:

| Patch | Replaces | Purpose |
|---|---|---|
| `url_validation.py` | `letta/helpers/url_validation.py` | Allows loopback/RFC1918 private-network MCP targets (needed for SearXNG at `127.0.0.1:3010`), still blocks link-local/metadata SSRF vectors |
| `openai_client.py` | `letta/llm_api/openai_client.py` | Guards the `user` field so Mistral (BYOK, stricter schema) doesn't 422; injects a Mistral-specific `prompt_cache_key`; **also carries the retry/batch-splitting logic in `request_embeddings()`** — directly relevant to the Mistral embedding cutover |
| `helpers.py` | `letta/agents/helpers.py` | Better `ToolConstraintError` messaging so the model retries via `call_tool(...)` instead of failing outright |

Today: deployed as read-only bind-mounts into the container by `scripts/homelab-ct-setup.sh`.
**Native install is actually simpler here**, not just equivalent: after `pip install letta`
into the venv, copy these 3 files directly over their `site-packages/letta/...` equivalents —
no bind-mount plumbing needed. Carries forward unchanged from the README: re-`diff` against
upstream on every Letta version bump.

## Detailed Migration Steps

### Phase 1: Infrastructure Provisioning
- `pct create` CT 141 (next free ID, confirmed free), **Ubuntu 24.04 specifically** (template
  already cached locally — no download needed), **unprivileged, no `nesting`/`keyctl` flags**.
  Debian 13's newer systemd (257) fails a clean boot without `nesting` on this Proxmox
  version — empirically confirmed (see Progress log), so this isn't a coin-flip between the
  two templates.
- Install: Python 3 + venv, `postgresql`, Node.js + `@deepseek-ai/dsh`, `cryptography`, git,
  and `cloudflared` (native `.deb`/systemd unit — see Cloudflare's install docs for the
  Debian/Ubuntu repo).
- Verify storage: thin pool `pve/data` — currently 73.69% used, ~38.3 GB free headroom
  (re-checked live 2026-08-24, matches v1's figure). Letta/Postgres/workspace footprint is
  lightweight; a few GB disk / 2 GB RAM is enough, don't over-provision on this CPU- and
  storage-constrained host.

### Phase 2: Embedding API Validation
Unchanged from v1 — already proven on eva-spike. Re-verify `embedding_dim: 1024` once more
against a live call before touching production `eva`/`eva-sleeptime` agents, as a sanity check
post-migration.

### Phase 3: Data Migration
1. On desktop: `pg_dump` the Letta Postgres database (containerized today) to `letta.sql`.
2. SCP the dump + the 3 patch files + `letta.env` to CT 141.
3. Install native Postgres on CT 141, restore the dump.
4. `pip install letta` into a venv, overwrite the 3 files under `site-packages/letta/...` with
   the reviewed patches from `letta-patches/`, point it at the restored DB, verify agent
   queries.

### Phase 4: Service Cloning **[CHANGED — native instead of container copy]**
- Clone the eva repo to CT 141.
- Task-runner: copy `eva-task-runner.env`, FCM service-account JSON, `tasks.db`, workspace;
  install into a venv; native systemd unit.
- eva-web: copy `eva-web.env`; native systemd unit (stdlib-only, no venv deps beyond what it
  already needs).
- SearXNG: native pip/uWSGI install in place of the Podman Quadlet; port `settings.yml` over.
- Cloudflare Tunnel: install `cloudflared` natively, copy `eva.env`/tunnel token (unchanged
  token, same hostname `eva.qstivi.com`), create its native systemd unit.
- Write systemd unit files for everything above — no Quadlet `.container` files needed
  anywhere on this CT.

### Phase 5: Cutover Window (unchanged from v1)
Deliberate freeze, not live sync:
1. Stop all eva services on the desktop.
2. Final `pg_dump`.
3. Restore on CT 141, start all services.
4. Confirm message round-trip through the Flutter app via `eva.qstivi.com` (unchanged
   hostname/tunnel).
5. Disable (don't delete) desktop-side units — rollback is just re-enabling them if Phase 5
   verification fails.

### Phase 6: Cleanup (unchanged from v1)
- Remove `eva-lmstudio-status.service`.
- Remove LM Studio dependency from the Flutter app.
- Check whether desktop LM Studio is still needed for ComfyUI/TTS before fully retiring it.

## Resource Analysis (re-verified live, 2026-08-24)

| Component | Status | Impact |
|---|---|---|
| CPU | i3-8100T, 4 vCPUs, shared | No blocking issue |
| RAM | 31 GB total, 16 GB free, 19 GB available | Comfortable for a native-process footprint (lighter than containers — no Podman/systemd-user overhead) |
| Host root `/` | 64 GB, 11 GB free (83% used) | Immaterial — both CT templates already cached locally |
| VG `pve` | Fully allocated (4 MB free) | Irrelevant — CT disks are thin-provisioned from the `data` pool, not raw VG space |
| Thin pool `pve/data` | 145.85 GB, 73.69% used, ~38.3 GB free | Adequate for a lean CT |
| Next CT ID | 141 confirmed free | — |

**Recommendation unchanged:** allocate a few GB disk and 2 GB RAM, not more — this host is
CPU- and storage-constrained.

## Key Risks & Mitigations

- **Live data mutation during migration** — deliberate freeze window + final dump (unchanged).
- **Embedding dimension mismatch** — mitigated by pre-validated real-call check (unchanged).
- **Authentication fallthrough** — resolved by reusing `OPENAI_API_KEY` (unchanged).
- **CPU contention** — acknowledged, acceptable (unchanged).
- **[RESOLVED] Patch-file compatibility with native install** — reviewed `letta-patches/`
  (see above); all 3 are plain source-file overrides, native install is a clean copy-over,
  no rework needed.
- **[REMOVED as a risk]** rootless-Podman-in-unprivileged-LXC namespace/keyring issues — no
  longer applicable, since there's no Podman on this CT.
- **[NEW] Letta version drift** — the patches must be re-diffed against upstream on every
  Letta version bump (per `letta-patches/README.md`); applies natively same as it did
  containerized, just worth calling out explicitly since there's no image tag to pin against
  anymore — pin the venv's `letta` version explicitly in requirements instead.
