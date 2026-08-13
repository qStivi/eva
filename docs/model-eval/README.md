# Eva local-model eval (2026-08-12)

Stage-1 persona bake-off of local models to replace Eva's brain (gpt-oss-20b) on the
RX 9070 XT (16 GB, ROCm/GGUF). Non-disruptive: harness hits LM Studio (localhost:1234)
directly with Eva's live persona + an 8-prompt battery.

- `eval_stage1.py` — the harness (env: OPENAI_API_KEY, OUTDIR, MODELS_JSON, RESULTS_FILE).
- `stage1_results.json` — 10 on-disk models. `stage2_round2_results.json` — 4 downloaded.
  `stage_crashers_results.json` — qwen3-30b (loaded only after ROCm runtime update).
- `consolidate.py` — merged ranking. `generate_artifact.py` — builds the comparison page.
- `eva_model_comparison.html` — the published comparison (artifact 90a8d315).

**Outcome:** Stage-2 finalists = ministral-3-3b, ministral-3-14b-reasoning,
deepseek-r1-0528-qwen3-8b, + lfm2.5-2.6b (wildcard). Engine kept on **Vulkan 2.28.2**
(ROCm loads qwen3-30b but crashes gpt-oss-20b). See ../2026-08-12-MODEL-LADDER-PLAN.md.

## Stage 2 — tool-calling (2026-08-12)

`stage2_lib.py` (throwaway Eva agent + tool set, NO HassClimateSetTemperature) +
`stage2_matrix.py` (4 models × {full, toned} persona × 8-prompt tool battery, scores
first-tool-picked). Results: `stage2_matrix_results.json`.

Findings: ministral-3-3b (8/8 full), ministral-3-14b-reasoning (8/8 toned), qwen3-8b
(8/8 full) all tool-call well. **deepseek-r1-0528-qwen3-8b = 2/8 — calls no tools,
only roleplays; DROPPED.** Toning down persona did NOT improve tool reliability (keep
full Eva). Watch-out: occasional confident hallucinated tool-use (claims success w/o
calling the tool). Note: HA tools only *execute* in the live eva agent (MCP linkage) +
nothing exposed to Assist yet; memory + web execute in test agents.
Prereq applied: flipped is_deleted=false on the 3 finalists in Letta provider_models.

## Thing 1 — cloud model comparison (2026-08-13)

Direct-provider (not OpenRouter) cost + voice comparison: Anthropic and Mistral
registered as native Letta providers (BYO keys in `~/.config/letta/cloud-providers.env`,
chmod 600, gitignored, never in the repo), then hit **directly** (not through Letta) with
the same persona + Stage-1 8-prompt battery, one call at a time (billed).

- `eval_cloud.py` — the harness (env: `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `OUTDIR`,
  `RESULTS_FILE`). 6 models: Haiku 4.5 / Sonnet 5 / Opus 5 (Anthropic), Ministral 8B /
  Small / Medium 3.5 (Mistral). Cost is self-computed from real per-call token usage ×
  each vendor's published rate — not pulled from a provider usage API (Anthropic's needs
  a separate Admin key; Mistral's Admin API usage-metrics endpoint wasn't used either, to
  keep both providers on the same footing).
- `rerun_failed.py` — retries only cells that errored, merges into the existing results
  file. **Gotcha hit:** `eval_cloud.py` originally had no `if __name__=="__main__":`
  guard, so `import eval_cloud` re-ran its whole battery as an import side effect —
  re-billed 3 already-successful models (~$0.02 extra). Fixed with a `run()` wrapper
  (same class of bug as `stage2_matrix.py` in Stage 2 — should've been caught sooner).
- Claude 5-gen models (Sonnet 5, Opus 5) reject an explicit `temperature` param
  ("deprecated for this model") — omit it, don't pin one.
- `cloud_results.json` — raw results + real cost per call. `generate_cloud_artifact.py`
  builds `cloud_comparison.html` (published artifact).

**Total spend across both runs: ~$0.27** (well under the €10/month hard cap set in each
provider's console — Anthropic Console → Limits (USD only); Mistral Admin Panel →
Workspace → Monthly spending limit).

**Findings:** All 6 models pass the mechanical checks (reasoning answer correct, exactly
3 bullets on format-follow) — the real differentiator is voice depth vs. cost. Opus 5
($0.145/battery) and Sonnet 5 ($0.048/battery) give the most textured, specific replies
(the boundary-refusal answers read like they're actually thinking about *this* report).
Ministral 8B and Mistral Medium 3.5 hold Eva's voice well for a fraction of the cost;
Mistral Small is fastest and cheapest but visibly terser ("I actually care." — two
sentences, done). No tool-calling tested this round (persona/voice only, matching
Stage 1's shape) — tool-calling economics for the cloud tiers is a follow-up, same as
the local Stage 2 matrix. Next: build the complexity router (plan step B) using this
cost data to decide when a turn is worth escalating past the local tier-0 default.
