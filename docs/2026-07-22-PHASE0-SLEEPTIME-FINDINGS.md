# Phase 0 — sleep-time memory consolidation: findings & exact knobs

_2026-07-22. Validation of the first phase of [the "Eva with hands" plan](2026-07-22-EVA-WITH-HANDS-PLAN.md).
All work done on the throwaway **`eva-spike`** agent; **real `eva` is untouched** (still
`gpt-oss-20b`, no sleeptime). Nothing here is enabled on Eva yet — that's a follow-up decision._

## Bottom line

- **The mechanism works** and is fully mapped (knobs below). A background `sleeptime_agent`
  shares the main agent's memory blocks, fires on a step cadence, edits via memory tools,
  and the edits **persist** to the shared block.
- **The blocker turned out to be a Letta registry bug, not a version gap** — and it's fixed
  (see below). **No Letta upgrade exists or is needed**: 0.16.8 is the latest release.
- **Quality is the open problem.** The local 30B does **incremental, partial** hygiene —
  ~1 fix per background cycle, slow to converge, and it doesn't reliably finish the
  perspective/dedup pass even after several cycles. Good enough to *tidy over time*, not a
  crisp one-shot cleaner. See [Quality](#quality-the-real-limitation).

## The root-cause fix: Letta soft-deletes newer models (`is_deleted`)

The reason the desired consolidator model wouldn't attach:

- Letta 0.16.8's **sleeptime/group execution path resolves the model by handle** against the
  `provider_models` registry (unlike the **main-chat path**, which uses each agent's *cached*
  `llm_config` and skips resolution — that's why Eva runs `gpt-oss-20b` fine even though it
  wasn't resolvable).
- In `provider_models`, newer models were flagged **`is_deleted = true`** — Letta soft-deleted
  them in an earlier sync (when they weren't downloaded yet), and its sync logic
  ("already exists, skipping") **never resurrects** a soft-deleted row. Affected: the whole
  qwen3-30b-a3b family, **`openai/gpt-oss-20b` (Eva's own brain!)**, `qwen/qwen3-8b`, and more.
  Only 9 "legacy" models had `is_deleted=false` and thus resolved.
- Symptom on the sleeptime path: `HandleNotFoundError: … must be one of []`.

**Fix (applied):** flip the flag for the models we use. Reversible; the row just re-enables.

```sql
-- inside the letta container's bundled Postgres (db letta, user letta)
UPDATE provider_models SET is_deleted=false, updated_at=now()
WHERE handle IN (
  'openai-proxy/qwen3-30b-a3b-instruct-2507@q4_k_m',  -- the consolidator
  'openai-proxy/openai/gpt-oss-20b',                  -- Eva's brain (remove latent fragility)
  'openai-proxy/qwen/qwen3-8b'                         -- eva-spike's brain
);
```

After this, `/v1/models` lists them and the handle resolves (a `PATCH /v1/agents/{id}` with
`{"model": handle}` returns 200 instead of 404). **Durability caveat:** this is a direct DB
edit; a future provider re-sync *should* leave a present, non-deleted model alone (sync skips
existing rows), but re-verify after any Letta restart/upgrade.

## Exact sleeptime knobs (0.16.8)

- **Enable:** `PATCH /v1/agents/{main_id}` `{"enable_sleeptime": true}` (or set at create).
  This auto-creates:
  - a **sleeptime agent** named `<main>-sleeptime`, `agent_type: "sleeptime_agent"`, which
    **shares the main agent's memory blocks** (same block ids — verified) and has only memory
    tools: `memory_insert`, `memory_replace`, `memory_rethink`, `memory_finish_edits`. It has
    **no archival tool**, so "route episodic facts → archival" is out of scope for Phase 0
    (would need attaching `archival_memory_insert` to this agent).
  - a **group** (`manager_type: "sleeptime"`) whose `manager_agent_id` is the **main** agent
    and `agent_ids` is `[sleeptime agent]`.
- **Cadence:** `PATCH /v1/groups/{group_id}`
  `{"manager_config": {"manager_type": "sleeptime", "sleeptime_agent_frequency": N}}`.
  It fires the consolidator once every **N main-agent steps** (default **5**). The group's
  `turns_counter` accumulates toward N. **Gotcha that cost real debugging time:** at the
  default `freq=5`, a single test message does **not** trigger a run — set `freq=1` for
  deterministic testing, then restore.
- **Consolidator model:** set the sleeptime agent's `llm_config` (see model-choice gotcha).
- **Steering the behavior:** the sleeptime agent's own **`memory_persona`** block is the
  customization lever — its base system prompt is the generic "Letta-Sleeptime-Memory"
  organizer; `memory_persona` is where Eva-specific hygiene rules go.

## Model choice

**Shipped on Eva: `gpt-oss-20b`** (the sleeptime agent inherits the main agent's model, so
this is automatic and free). Reason: on 16 GB VRAM, a *different* consolidator model can't stay
resident alongside Eva's chat model, so LM Studio would **swap** models around every 5th turn
(~30–60 s lag on that reply). Reusing Eva's own `gpt-oss-20b` means **zero swapping** — chat
stays snappy and consolidation piggybacks on the already-loaded model. Since we deliberately
accepted incremental hygiene, this is the right trade for shipping now.

**Higher-quality option (deferred to better hardware / cloud):** `qwen3-30b-a3b-instruct-2507@q4_k_m`
with `enable_reasoner=false` — better per-cycle hygiene, ~40–56 s/run, but forces the VRAM swap
on this box. It's what the **`eva-spike`** testbed uses.

- **`…-thinking`** (reasoner on) was **rejected**: ~3 min/run (CPU-offloaded on 16 GB) and it
  burns its budget on `<think>`, tool-calling poorly through Letta — shallow, non-persisting edit.
- Both 30B variants (unlike qwen2.5-7b) correctly **leave the `persona` block alone** ✓.
  qwen2.5-7b was disqualified: it rewrote Eva's `persona` and its own instructions.
- `gpt-oss-20b` inherits `enable_reasoner=true` from Eva; it tool-calls cleanly for memory edits.

## Quality (the real limitation)

With strengthened `memory_persona` instructions (rewrite to third person, de-embellish, dedup,
concretize dates, drop trivia, use `memory_rethink` for whole-block rewrites), the consolidator:

- ✅ correctly de-embellished ("the most obsessed keyboard enthusiast on the entire planet…"
  → "Stephan likes mechanical keyboards") and rewrote a line into third person;
- ❌ but fixes only **~1 issue per cycle** and, after ~5 cycles, still left a first-person line,
  a second-person line, a duplicate, and a relative date. Left alone it also tends to **append
  trivia** ("Stephan said hello") rather than rewrite.

So sleeptime here is a **slow incremental tidier**, not a reliable cleaner. Options to close the
gap (a decision, not yet done):
1. **Accept incremental** — over a long real conversation it keeps improving; pair with a strong
   persona directive so Eva writes cleaner in the first place (less for the consolidator to fix).
2. **Stronger steering / fewer, blunter rules**, or periodically force a full `memory_rethink`.
3. **Escalate consolidation to a cloud model** (ties into the roadmap's cloud-escalation item) —
   run the background tidy on a frontier model where hygiene is reliable.

## Other gotchas captured

- **Model handle assignment:** the `{"model": handle}` shorthand validates against the
  resolvable registry (404 if not there); setting the full `llm_config` object stores it but
  the **run still re-resolves the handle** — so the model must be un-deleted regardless.
- **BYOK `lmstudio_openai` provider is a dead end here:** it discovers via LM Studio's native
  `/api/v0/models`, which **401s** because this LM Studio enforces an API key and Letta's
  lmstudio client doesn't send it (the same reason Eva uses the `openai`-base proxy). The
  base `openai` provider is the only working auth path.

## Shipped state (2026-07-22)

Phase 0 is **live on the real Eva**, in its accepted-incremental form:

- `eva` (`gpt-oss-20b`): `enable_sleeptime=true`. Consolidator `eva-sleeptime` runs
  **`gpt-oss-20b`** (inherited, no VRAM swap), shares Eva's `human`/`persona` blocks, hygiene
  instructions in its `memory_persona`, `freq=5`. Verified: Eva still chats normally in-character.
- `eva-spike` + `eva-spike-sleeptime` (`qwen3-30b-a3b-instruct`): kept as the higher-quality
  testbed.
- **Backups:** image `letta-rollback:0.16.8`; DB `pg_dump` at
  `~/letta-backups/letta-20260722-182211.dump`; Eva's pre-enable memory blocks at
  `~/letta-backups/eva-blocks-20260722-185915.json`.
- **To roll back on Eva:** `PATCH /v1/agents/{eva}` `{"enable_sleeptime": false}` and, if needed,
  restore the `human` block from the blocks backup.

## Next (deferred)
- **Raise quality** when hardware allows or via **cloud escalation** (roadmap item): swap the
  consolidator to `qwen3-30b-a3b-instruct` (needs the VRAM headroom) or a cloud flagship.
- **Archival routing** — attach `archival_memory_insert` to the sleeptime agent to move
  dated/episodic facts to (timestamped) archival, keeping core for stable facts.
