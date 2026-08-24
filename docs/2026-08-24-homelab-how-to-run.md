# How to run: eva backend migration to the homelab Proxmox host

Handoff runbook for whoever (whichever Claude session) executes the actual move. Read
`docs/2026-08-24-homelab-migration-plan.md` first for the *why* — this doc is the
concrete *how*, step by step, written so it can be followed without re-deriving
anything. Ping the user (Stephan) before anything destructive or before the final
cutover — everything up through "bring the new CT up alongside the old one" is safe to
do unsupervised since the desktop instance keeps running the whole time.

Status as of 2026-08-24: the embedding swap (the one open technical question in the
migration plan) has been **verified working** against `eva-spike` on the desktop's
current Letta instance — see "Already done" below. Nothing else has been migrated yet.

## Already done (on the desktop, ahead of the actual move)

- `~/.config/letta/letta.env`'s `OPENAI_API_KEY` now holds the real Mistral API key
  (repurposed — see the migration plan's "Changing → Embeddings" section for why this
  is safe: Letta's embedding auth path ignores `embedding_endpoint_type` and always
  uses this one var, and nothing else needs it once LM Studio is retired).
- `eva-spike` and `eva-spike-sleeptime`'s `embedding_config` patched to:
  ```json
  {
    "embedding_endpoint_type": "mistral",
    "embedding_endpoint": "https://api.mistral.ai/v1",
    "embedding_model": "mistral-embed",
    "embedding_dim": 1024,
    "embedding_chunk_size": 300
  }
  ```
- Verified live: `POST /v1/agents/{eva-spike-id}/archival-memory` returned `200` with a
  real Mistral-generated vector (Letta stores it zero-padded to a fixed 4096-column, but
  the real payload is exactly 1024 non-zero values — confirms `embedding_dim: 1024` is
  correct). The test passage was deleted afterward — no leftover state.
- **Live `eva`/`eva-sleeptime` have NOT been touched** — still pointed at local LM
  Studio. Flip these the same way once you're ready (step 2 below), same pattern.

## What has NOT happened yet
- No CT has been provisioned.
- No data has been migrated.
- `eva`/`eva-sleeptime`'s embedding config is unchanged.
- Nothing has been pushed to GitHub beyond what was already on `main` before this
  migration effort started — this doc and the setup script are new, uncommitted files.

## Step 1 — Provision the CT
Proxmox side (on the Proxmox host itself, not inside a CT):
```bash
# next free ID after 140 (dynDNS) — confirm nothing's taken it since
# docs/2026-08-24-homelab-migration-plan.md was written
pct create 141 <a Debian/Ubuntu template> \
    --hostname eva --cores 2 --memory 2048 --swap 512 \
    --rootfs <thin-pool-backed storage>:4 \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --unprivileged 1 --features nesting=1
pct start 141
```
(Exact template/storage-pool names depend on what's already configured on this host —
check `pveam list` / `pvesm status` rather than guessing. `nesting=1` matters —
rootless Podman inside an LXC CT needs it.)

Then inside the CT, as the service user (create one if starting from a bare template —
match the desktop's `qstivi` convention or use whatever's standard for this homelab):
```bash
git clone https://github.com/qStivi/eva.git ~/projects/eva
~/projects/eva/scripts/homelab-ct-setup.sh
```
This installs Podman, Node+dsh, Python+cryptography, enables systemd-user lingering,
and creates the directory scaffold. It does **not** touch secrets or migrate data.

## Step 2 — Flip eva's own embedding config (safe to do now, independent of the CT)
Can happen on the desktop's current Letta instance, before or after CT provisioning —
it doesn't depend on the new host existing yet. Same commands as what was already run
against eva-spike, just against `eva` and `eva-sleeptime`:
```bash
for agent in eva eva-sleeptime; do
  id=$(curl -s "http://localhost:8283/v1/agents/?name=$agent" \
        | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[0]['id'])")
  curl -s -X PATCH "http://localhost:8283/v1/agents/$id" \
    -H "Content-Type: application/json" \
    -d '{"embedding_config": {"embedding_endpoint_type":"mistral","embedding_endpoint":"https://api.mistral.ai/v1","embedding_model":"mistral-embed","embedding_dim":1024,"embedding_chunk_size":300}}'
done
```
Verify with a real recall/memory-search turn in the live conversation before considering
this done — don't just trust the `200`.

Once this lands, local LM Studio is no longer load-bearing for eva at all (chat's
already cloud-routed since the earlier tier retune). `eva-lmstudio-status.service` on
the desktop becomes dead code at that point — fine to leave running harmlessly, or
retire it (also drop whatever calls it from the Flutter app / eva-web) — not urgent,
doesn't block the migration.

## Step 3 — Copy secrets (manual, none of this is in git)
From the desktop (`qstivi@<desktop>`) to the new CT — do this over SSH/SCP directly
between the two boxes, not through any intermediate storage:

| Source (desktop) | Destination (CT) | Contents |
|---|---|---|
| `~/.config/letta/letta.env` | same path | `OPENAI_API_KEY` (now the Mistral key, see Step "Already done"), `OPENAI_API_BASE` (obsolete after Step 2 for embeddings, but harmless to leave — nothing else reads it once LM Studio's fully off eva's path) |
| `~/.config/letta/url_validation.py` | same path | Loopback/private-IP MCP patch |
| `~/.config/letta/openai_client.py` | same path | Mistral `user`-field-stripping patch |
| `~/.config/letta/helpers.py` | same path | `ToolConstraintError` hint patch |
| `~/.config/eva-task-runner/eva-task-runner.env` | same path | Runner port, Letta host, agent id, SearXNG URL, `RESEARCH_CLOUD_MODEL`, `FCM_SERVICE_ACCOUNT_FILE` path |
| the file `FCM_SERVICE_ACCOUNT_FILE` points at | same path | Firebase service-account JSON (push notifications) |
| `~/.config/eva-web/eva-web.env` | same path | Port/host, Letta host, agent id, basic-auth creds, `EVA_API_KEY` |
| `~/.config/cloudflared/eva.env` | same path | `TUNNEL_TOKEN` |
| `~/.config/searxng/settings.yml` | same path | Must keep `json` under `search.formats` (MCP needs it — see the `lmstudio-searxng-web-search` memory) |

## Step 4 — Copy the Quadlet/systemd unit files
From `~/.config/containers/systemd/` on the desktop:
`letta.container`, `searxng.container`, `searxng-mcp.container`, `searxng.network`,
`cloudflared-eva.container` → same path on the CT, unchanged (they already use `%h` for
the home-relative paths, so they're portable as-is).

From `~/.config/systemd/user/` on the desktop:
`eva-task-runner.service`, `eva-web.service` → same path on the CT, unchanged
(`WorkingDirectory`/`ExecStart` already point at `~/projects/eva/...`, which the CT setup
script already cloned to the same path).

Do **not** copy `eva-lmstudio-status.service` — it's desktop-only, retired per Step 2.

## Step 5 — Migrate Letta's data
On the desktop:
```bash
systemctl --user stop eva-task-runner eva-web cloudflared-eva letta
# (stop order matters less than "stop everything before the final dump" —
#  the important part is nothing writes to Letta's DB after this point)
podman start letta_pgdata >/dev/null 2>&1 || true   # ensure the volume's container context is up if needed
podman exec letta pg_dump -U letta letta > /tmp/letta-final.sql   # confirm actual db/user names from letta.container's env first
scp /tmp/letta-final.sql <ct-host>:/tmp/letta-final.sql
rm /tmp/letta-final.sql   # don't leave a plaintext dump of eva's memory lying around
```
On the CT:
```bash
systemctl --user start letta   # brings up the empty Postgres volume + schema
sleep 15
podman exec -i letta psql -U letta letta < /tmp/letta-final.sql
rm /tmp/letta-final.sql
systemctl --user restart letta
```
Verify: `curl http://localhost:8283/v1/agents/` on the CT lists `eva`, `eva-spike`, and
both sleeptime agents, with the embedding configs from Step 2/"Already done" intact.

## Step 6 — Bring up the rest, verify before cutover
```bash
systemctl --user enable --now searxng searxng-mcp cloudflared-eva eva-task-runner eva-web
```
With the old (desktop) instance still stopped and the new (CT) instance up:
- `curl http://localhost:8284/...` (eva-web) responds on the CT.
- A real message round-trips through `eva.qstivi.com` (the tunnel now runs from the CT,
  same `TUNNEL_TOKEN`, same public hostname — nothing changes app-side).
- `check_task`/a trivial `delegate_to_harness` job runs successfully (proves
  `dsh`/Node/the strip-proxy work on the new box).
- A push notification actually arrives on the phone (proves the FCM service-account
  file copied correctly).

## Step 7 — Cutover / cleanup
If Step 6 all checks out:
- Leave the desktop's Quadlet/systemd units in place but disabled
  (`systemctl --user disable letta eva-task-runner eva-web cloudflared-eva`) rather than
  deleting anything — cheap rollback if something's wrong post-cutover.
- Tell Stephan it's live and ask him to confirm from his phone before calling this done.

## Rollback
If anything in Step 6 fails: just `systemctl --user start` the stopped units back up on
the desktop — nothing was deleted there, only stopped. The CT can be torn down
(`pct stop 141 && pct destroy 141`) and retried without any risk to the live service.
