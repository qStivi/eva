# Eva — model ladder: local brains + auto cost-routing

_Planning session, 2026-08-12. Two related-but-separate threads. Stays on **Letta**.
Supersedes the roadmap's "cloud-escalation via OpenRouter" bullet: we go **direct
provider APIs** (Anthropic + Mistral) instead._

**Correction, 2026-08-13:** originally scoped as one ladder where the local winner is
tier-0 and cloud only escalates hard turns. The user corrected this: **Thing 1's ladder
is fully API — no local tier, no local fallback at all.** Thing 2's local winner
(ministral-3-3b, see below) stays Eva's actual live brain, but that's a separate,
already-shipped decision — it does **not** feed into Thing 1's router. The two threads
no longer converge into one ladder; they're independent outcomes that both happen to
be about "which model, when."

## The two things

1. **Compare API models + auto cost-routing.** Claude and Mistral, both within each
   company's lineup and mixed across them. See how expensive they get; pick a model by
   task complexity **automatically** to optimize cost, among cloud tiers only. Keep the
   Letta backend.
2. **Which models are viable to run locally?** A batch pulled from a benchmark site
   (filtered to a 24 GB card there) — check what actually runs **on this machine**,
   using quantized and/or smaller sibling models where the headline model won't fit.
   (Already resolved — see Thing 2 below. Its winner is Eva's live brain, independently
   of Thing 1.)

## The real hardware target (this machine, not a 24 GB card)

The benchmark site's "24 GB" filter was incidental. Eva runs here:

- **GPU:** AMD **Radeon RX 9070 XT**, **16 GB** VRAM (15.9 GiB), RDNA4 / **gfx1201**.
- **RAM:** 47 GB system + 15 GB swap (offload headroom).
- **Serving path:** ROCm, **not CUDA** — models must run as **GGUF** via llama.cpp /
  **LM Studio** (the existing local path; ComfyUI + TTS already prove stock ROCm torch
  works on gfx1201).
- **The bar to beat:** this box already runs Eva's current brain **gpt-oss-20b** locally.
  A replacement must fit 16 GB *and* be as good or better.

So the constraint is **16 GB VRAM + ROCm/GGUF**, not 24 GB. Because every candidate below
is ≤10B, the 24→16 change drops none of them — it just means run **Q4–Q6**, not BF16, and
watch context length.

## Local-viability verdict

### Fits on 16 GB — local candidates

| Model | Size | Modality | Notes for this box |
|---|---|---|---|
| **Ministral 3 8B Reasoning 2512** | 8B dense | text+vision | Mistral: 24 GB BF16 / <12 GB quantized → here run Q5–Q6, comfortable. Reasoning-tuned. **First pick.** |
| **Phi-4-mini-reasoning** | 4B dense | text | ~3–4 GB, 300+ tok/s class; likely the "good past Phi experience." **First pick.** |
| **Qwen3.5-9B** | 9B dense | text | ~4–5 GB; strong small-model benchmarks |
| **LFM2.5-2.6B** | 2.6B dense | text, agentic | <2.5 GB, tool-calling, day-1 GGUF; trivially fits |
| **MiMo-7B / MiMo-VL-7B** | 7B dense | text / VL | Xiaomi — sister lineage of MiMo-V2-Flash; reasoning+coding tuned |
| **Hunyuan-7B** | 7B dense | text | Tencent dense, 256K ctx, fast/slow thinking |
| **DeepSeek-R1-Distill-Qwen-14B** | 14B dense | text | older DeepSeek reasoning distill; fits Q4/Q5 (32B distill too big) |
| **Step3-VL-10B** | 10.2B dense | VL | Q4 ~6 GB; vision-support risk in GGUF |
| **Qwen3-VL-8B-Thinking** | 8B dense | VL | FP8/GGUF published; vision-support risk |
| **Gemma 4 E4B** | ~4B eff. | text+img+audio | trivially fits; PLE efficiency |
| **Phi-4-multimodal-instruct** | ~4B | text+img+audio | Q4 ~2–3 GB |
| **MiniCPM-SALA** | 9B dense | text, 1M ctx | model fits; long context is the RAM cost |

**Risk flags:** (1) **Vision/multimodal** models (Step3-VL, Qwen3-VL, Phi-4-multimodal,
Gemma 4 audio) — llama.cpp/LM Studio vision support is patchier than text; treat as
optional. (2) Everything needs a GGUF that loads on **gfx1201**.

### Won't fit 16 GB — cloud-tier only (giant MoE)

MoE models must hold **all** expert weights in VRAM; "active params" is compute, not
memory. None of these has a 16 GB-viable sibling (checked).

| Model | Total / active | Sibling that fits 16 GB? |
|---|---|---|
| **Hy3** (Tencent) | 295B / 21B | Hunyuan-7B (different lineage, but fits — listed above) |
| **MiMo-V2-Flash** (Xiaomi) | 309B / 15B | **MiMo-7B** (listed above) |
| **Inkling-Small** (Thinking Machines) | 276B / 12B | none |
| **LongCat-Flash-Thinking** (Meituan) | 560B / ~27B | none |
| **GLM-5.2** (Zhipu) | 753B / 40B | none shipped (Air/Flash only requested) |
| **DeepSeek-V4-Pro-Max** | 1.6T / 49B | none V4-gen (only older R1-Distills) |
| **Kimi K3** (Moonshot) | 2.8T / 104B | none |

These are the **API/cloud-tier candidates** for Thing 1's ladder — but note Thing 1 as
scoped is **Claude + Mistral**; the giants are a separate "cheap open-weights via API"
option we can add later.

## Plan — Thing 1: comparison + auto cost-routing

- **A. Providers into Letta — direct APIs. ✅ DONE 2026-08-13.** Anthropic + Mistral
  registered as native Letta providers (BYO keys, `~/.config/letta/cloud-providers.env`,
  chmod 600, gitignored). Tiers compared: Claude Haiku 4.5 / Sonnet 5 / Opus 5, Mistral
  Ministral 8B / Small / Medium 3.5.
- **D. Compare. ✅ DONE 2026-08-13** (moved ahead of B/C — needed real cost data first).
  Ran the Stage-1 8-prompt battery directly against both providers' APIs (not through
  Letta). Total spend **~$0.27**, well under the €10/month cap set in each console. Full
  writeup: `docs/model-eval/README.md` § Thing 1, results in `docs/model-eval/
  cloud_results.json`, published comparison `docs/model-eval/cloud_comparison.html`.
  Headline: all 6 pass the mechanical checks; Opus 5/Sonnet 5 give the most textured
  replies, Ministral 8B and Mistral Medium 3.5 hold Eva's voice well for far less, Mistral
  Small is cheapest/fastest but visibly terser. No tool-calling tested yet (persona/voice
  only, matching Stage 1's shape).
- **B. Complexity router. ✅ LIVE 2026-08-13.** Built on `feat/eva-ha-agent` (where
  `eva-web/app.py` actually lives — this branch had gone stale on that file, see commit
  note) as `eva-web/model_router.py`, wired into the shared `run_turn()` used by both the
  web UI and the HA `/v1` shim. Per the user's explicit choice: **escalates freely by
  complexity, no artificial stickiness, and this is now Eva's actual live brain** —
  ministral-3-3b local is no longer the default. Heuristic v1 scores length + regex
  signal groups (reasoning / emotional / boundary-test / identity-authenticity — the
  last one added after the comparison showed it's the biggest voice-quality gap between
  tiers) into cheap/mid/hard. Live-tested: cheap→mid escalation on an identity question
  produced a visibly richer reply; a same-tier follow-up **hit Letta's automatic
  prompt cache** (confirmed empirically, zero extra config) for a 10x cost drop.
  Commits: `feat/eva-ha-agent` f28d971, 8ef23d2.

  **Mistral BYOK fixed 2026-08-13** (see "Mistral bug — fixed locally" below) — tiers now
  genuinely mix both companies: **cheap = Ministral 8B, mid = Mistral Medium 3.5, hard =
  Opus 5** (Mistral is ~10x cheaper than the equivalent Anthropic tier for comparable
  quality per the bake-off; Opus reserved for turns where the extra quality earns its
  cost). Was Anthropic-only (Haiku/Sonnet/Opus) for a few hours between the router going
  live and the fix landing.
- **C. Cost instrumentation. ✅ DONE 2026-08-13**, and better than planned — rather than
  self-estimating tokens×price, `model_router.py` reads Letta's **real** per-turn
  `usage_statistics` (including the cache read/write split), computes exact cost, and
  logs it to `~/.config/eva-web/cost_log.jsonl` (outside the repo). `GET /api/cost` on
  `eva-web` sums it with a per-tier breakdown, so spend is visible on demand.

## Plan — Thing 2: local eval

- Pull the ≤10B fitters as GGUF into **LM Studio**; run each at **Q4–Q6**; A/B against
  **gpt-oss-20b** inside the same Letta `eva` agent (same persona, same tools).
- **Order:** text reasoning first — **Ministral 3 8B Reasoning**, **Phi-4-mini-reasoning**,
  then Qwen3.5-9B / MiMo-7B / Hunyuan-7B. Vision models only if Eva needs to see.
- The winner becomes the ladder's **tier-0 default brain**, replacing gpt-oss-20b if it's
  better at Eva's actual workload (chat + tool use + house control).

## Decisions locked

- **Stay on Letta.** No backend change.
- **Direct provider APIs** for Claude + Mistral (not OpenRouter — overrides the
  2026-07-21 roadmap bullet).
- **Target = this machine** (RX 9070 XT, 16 GB, ROCm/GGUF), not a 24 GB card — applies
  to Thing 2 (local eval) only.
- **Serving via LM Studio** for Thing 2's local brain (existing local path).
- **Thing 1's ladder is fully API, no local tier** (2026-08-13). The router in step B
  picks among Claude/Mistral cloud tiers only; it never falls back to a local model.
  Eva's actual live brain (ministral-3-3b, local) is a separate, unrelated decision from
  Thing 2 — Thing 1 does not touch it.

## Mistral bug — fixed locally (2026-08-13)

Root cause found in Letta 0.16.7's `letta/llm_api/openai_client.py` (the generic
OpenAI-compatible client Mistral is routed through, since `MistralProvider` uses
`model_endpoint_type="openai"` — there's no Mistral-specific request path):

1. **The real leak:** `ChatCompletionRequest(..., user=str(), ...)` in
   `build_request_data()` explicitly passes `user=""` at construction time. Pydantic's
   `model_dump(exclude_unset=True)` only omits fields that were never *passed* to the
   constructor — an explicit empty string still counts as set, so it always serializes
   into the request body regardless of any later conditional.
2. **The visible symptom:** a second block ("always set user id for openai requests")
   unconditionally does `data.user = self.actor.id` right after, for *every* provider
   routed through this client — including non-OpenAI BYOK providers like Mistral, whose
   stricter schema 422s on any field it doesn't recognize (`extra_forbidden`).

Letta already has the right pattern elsewhere in the same file — `if llm_config.provider_name
and llm_config.provider_name != "openai": <skip OpenAI-specific field>` (used for prompt-cache
fields) — it just wasn't applied to `user`. Confirmed no existing letta-ai/letta GitHub
issue for this.

**Fix:** removed the `user=str()` default from the constructor, and guarded both
"always set" reassignments (Responses API path + Chat Completions path) on
`llm_config.provider_name in (None, "openai")`. Applied as a local patch, not upstream:
- Patched file: `~/.config/letta/openai_client.py` (full file, copied from the container
  and edited — not a diff/PR against letta-ai/letta).
- Bind-mounted over the container's copy via
  `~/.config/containers/systemd/letta.container` (`Volume=...ro,Z`), same pattern as the
  existing `url_validation.py` override for the loopback-MCP block.
- Restart `systemctl --user restart letta.service` to apply; survives normal restarts
  (lives in `~/.config`, not the container image) but a Letta image update could shift
  these line numbers/logic enough to need re-diffing against the new version.
- Live-tested: single-turn and multi-turn Mistral conversation both work on the real
  `eva` agent now.

Consider upstreaming this as a real letta-ai/letta PR at some point — it's a clean,
narrowly-scoped fix that benefits any BYOK provider routed through the OpenAI-compatible
client, not just Mistral. (User's plan: research Letta's policy on AI-generated
contributions before opening one.)

### Follow-up: Mistral prompt caching wasn't actually reliable (fixed same day)

The `user`-field fix alone got Mistral *working*, but every turn was still paying full
price — Letta sends the complete context (persona, tools, memory, history) on **every**
call to **every** provider; that's fundamental to Letta's stateless-per-call architecture,
true for all providers, not something a patch changes. The question was whether that
resend gets a cache discount.

Checked Mistral's real API docs (not an aggregator): Mistral **does** support prompt
caching at the same 90% discount as Anthropic, but — unlike Anthropic, which caches
automatically — Mistral requires an explicit `prompt_cache_key` parameter on each request
("increases the chance of a cache hit, but doesn't guarantee one" without it). Letta's
`ChatCompletionRequest` schema has no field for this at all, and its one existing
cache-key helper (`_apply_prompt_cache_settings`) is explicitly real-OpenAI-only — its own
docstring says it deliberately *avoids* setting a key for OpenAI, since OpenAI's own
automatic hash-based routing already works well and an explicit key can hurt it there.
Mistral's docs recommend the opposite. Different providers, different caching designs —
this needed new code, not a tweak to existing logic.

**Fix:** added `_apply_mistral_cache_key()` to the same `openai_client.py` patch —
injects `prompt_cache_key` (keyed on the acting user's id) via the SDK's `extra_body`
mechanism (already used elsewhere in this file for OpenRouter-specific fields), only for
`provider_name == "mistral"`. Confirmed live: 4 consecutive turns, cache hit on every turn
after the first, cached portion growing with the conversation (4,608 → 4,736 tokens) —
reliable, not incidental.

This second fix is more of a **feature addition** than a bug fix (Letta was doing what it
documented, just not what Mistral needs) — worth keeping that distinction in mind if/when
researching contribution norms for a PR: the `user`-field fix is an uncontroversial
correctness bug, this one is closer to "add Mistral-specific caching support," which a
maintainer might reasonably want configurable/discussed rather than hardcoded.

## Open questions / next steps

- Complexity signal: heuristic v1 is live and reasonably tuned (see step B) but untested
  against real message volume yet — revisit thresholds/signals after seeing how often it
  actually escalates in daily use, and watch `~/.config/eva-web/cost_log.jsonl` against
  the €10 cap.
- Whether to add the cheap giant open-weights (Hy3, DeepSeek V4-Pro, GLM-5.2) as extra
  API tiers once Claude+Mistral routing works.
- Tool-calling economics for the cloud tiers — mirror Stage 2's tool-selection matrix
  against the now-live router, since every real turn now runs with the full tool set
  attached (not the bare eval_cloud.py setup) and costs ~10x more per turn than that
  comparison implied.

_Source data: model specs gathered 2026-08-12 from Hugging Face model cards,
artificialanalysis.ai, llm-stats.com, and vendor announcements; verify sizes/quant
availability against the live GGUF repos before pulling._
