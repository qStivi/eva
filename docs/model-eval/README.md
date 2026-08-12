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
