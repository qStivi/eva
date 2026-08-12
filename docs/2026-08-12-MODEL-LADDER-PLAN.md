# Eva — model ladder: local brains + auto cost-routing

_Planning session, 2026-08-12. Two related-but-separate threads that converge on one
idea: a **tiered model ladder** for Eva — a local default brain, escalating to cloud
APIs only for genuinely hard turns, auto-routed by task complexity. Stays on **Letta**.
Supersedes the roadmap's "cloud-escalation via OpenRouter" bullet: we go **direct
provider APIs** (Anthropic + Mistral) instead._

## The two things

1. **Compare API models + auto cost-routing.** Claude and Mistral, both within each
   company's lineup and mixed across them. See how expensive they get; pick a model by
   task complexity **automatically** to optimize cost. Keep the Letta backend.
2. **Which models are viable to run locally?** A batch pulled from a benchmark site
   (filtered to a 24 GB card there) — check what actually runs **on this machine**,
   using quantized and/or smaller sibling models where the headline model won't fit.

They converge: the local winner becomes the ladder's **tier-0 default**; Claude/Mistral
are the escalation tiers; the giant open-weights models are cloud-only.

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

- **A. Providers into Letta — direct APIs.** Add **Anthropic** and **Mistral** as native
  Letta providers (BYO keys), not via OpenRouter. Register the tiers to compare:
  Claude (Haiku → Sonnet → Opus) and Mistral (Medium → Large), plus local as tier-0.
- **B. Complexity router.** Reuse the **`toolset_router.preload_for()`** seam in
  `eva-web`: add a `model_router` that classifies each incoming message and sets the
  Letta agent's model tier for that turn before dispatch. Heuristic first (length /
  keywords / tool-intent / prior-turn signals); optionally a tiny local classifier
  later. Local stays default; escalate only hard turns.
- **C. Cost instrumentation.** Log tokens × per-model price per turn so spend is visible
  and the router is measurable.
- **D. Compare.** Fixed prompt set across tiers → plot quality vs. cost → tune
  thresholds.

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
- **Target = this machine** (RX 9070 XT, 16 GB, ROCm/GGUF), not a 24 GB card.
- **Serving via LM Studio** (existing local path).

## Open questions / next steps

- Exact Claude + Mistral model IDs and current pricing to wire (pull fresh at build time).
- Complexity signal: pure heuristic vs. a tiny local classifier — decide after seeing
  real message distribution.
- Whether to add the cheap giant open-weights (Hy3, DeepSeek V4-Pro, GLM-5.2) as extra
  API tiers once Claude+Mistral routing works.
- First concrete build step: register Anthropic+Mistral providers in Letta, or pull the
  two first local models — whichever thread we start with in the next session.

_Source data: model specs gathered 2026-08-12 from Hugging Face model cards,
artificialanalysis.ai, llm-stats.com, and vendor announcements; verify sizes/quant
availability against the live GGUF repos before pulling._
