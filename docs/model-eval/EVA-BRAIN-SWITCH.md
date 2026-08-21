# Eva brain switch — 2026-08-12

Eva's live Letta agent was switched from **gpt-oss-20b (full persona)** to
**ministral-3-3b (toned persona)** after the model bake-off (see README.md + the
comparison artifact 90a8d315).

## Current live state
- **Model:** `openai-proxy/mistralai/ministral-3-3b`, `enable_reasoner: false`, ctx 30000.
- **Persona:** toned (`persona/eva-toned.md`, ~4603 chars) in the agent's `persona` block.
- **Message buffer:** reset (required — see gotcha). Core memory (persona + human blocks
  + archival) preserved, so Eva kept what she knows about Stephan.

## Why the buffer had to be cleared (gotcha)
ministral-3-3b's chat template enforces **strict user/assistant alternation**. Eva's
prior 110-message history (built under gpt-oss with `enable_reasoner: true`, which
interleaved reasoning messages) was not strictly alternating, so ministral 500'd with:
`"conversation roles must alternate user and assistant roles except for tool calls and
results."` Fresh/clean buffers render fine. **Watch-item:** if the error recurs later,
Letta produced a non-alternating sequence again — reset the buffer or investigate the
message that broke alternation.

## How to revert
- **Model + persona only:** PATCH the eva agent's `llm_config` back to gpt-oss (handle
  `openai-proxy/openai/gpt-oss-20b`, `enable_reasoner: true`, ctx 30000, max_tokens 16384)
  and set the `persona` block back to `persona/eva.md`. Old model/persona snapshot:
  `REVERT-eva-before-ministral.json`.
- **Full restore (incl. old conversation history):** re-import `eva-backup-<ts>.af.json`
  via `POST /v1/agents/import` as a new agent (does not overwrite the live one).

## Prerequisite applied
The 3 finalist models were soft-deleted in Letta 0.16.8 (`provider_models.is_deleted=t`);
flipped to `false` so they're usable. A Letta restart may re-soft-delete newer models —
re-flip if agent creation with them 404s. (See auto-memory `letta-soft-deletes-newer-models`.)

## Open follow-ups
- **Repo persona source-of-truth: DONE.** `persona/eva.md` is now the TONED persona
  (canonical); the old full persona is preserved as `persona/eva-full.md`. `create-eva.sh`
  and `sync-persona.sh` read `eva.md`, so both now use toned automatically.
- **Sleeptime/group agents** (if enabled) may need the same model + a clean buffer.
