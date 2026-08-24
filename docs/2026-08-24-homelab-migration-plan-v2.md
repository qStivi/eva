# Eva Backend Migration to Homelab Proxmox (v2 — revised 2026-08-24)

Revises `docs/2026-08-24-homelab-migration-plan.md`. Changes from v1 are called out inline as **[CHANGED]**.

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
- `pct create` CT 141 (next free ID, confirmed free), Debian 13 or Ubuntu 24.04 (both templates
  already cached locally — no download needed), **unprivileged, no `nesting`/`keyctl` flags**.
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
