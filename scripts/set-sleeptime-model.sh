#!/usr/bin/env bash
# The sleeptime consolidation agent (fires every 5 turns, folds facts into
# `human` -- see persona/eva-sleeptime.md) has been running on the same local
# LM Studio model as foreground chat (openai/gpt-oss-20b via :1234) since it
# was first stood up -- the original plan (docs/2026-07-22-EVA-WITH-HANDS-PLAN.md)
# hoped for a bigger local model (30B-A3B-Thinking) instead, but that was
# never wired up, so it's been quietly riding the GPU/VRAM the foreground
# chat model needs, contending for the same resource every single time it
# fires. Moving it to a cloud model (same mechanism eva-web/model_router.py
# already uses for per-message tiering: PATCH /v1/agents/{id} {"model": ...})
# gets it off the GPU entirely and onto the same Mistral billing already
# tracked for chat/research -- see the usage screenshot from 2026-08-22.
#
# One-time / idempotent: just re-PATCHes the model field, safe to re-run
# with a different handle to change tiers later. Does NOT touch the parent
# agents (eva/eva-spike) -- only the sleeptime agent in each group.
#
# Usage:  ./scripts/set-sleeptime-model.sh [model-handle]
#   default: mistral/mistral-medium-latest -- matches model_router's "mid"
#   tier, a reasonable quality bar for judgment calls (perspective fixes,
#   dedup, the source-caution rule from the 2026-08-22 incident) without
#   paying "hard" tier prices for something that runs unattended in the
#   background, unread unless something goes wrong.
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
HANDLE="${1:-mistral/mistral-medium-latest}"

python3 -c "
import json, urllib.request

LETTA = '$LETTA'
HANDLE = '$HANDLE'

groups = json.load(urllib.request.urlopen(LETTA + '/v1/groups/'))
agents = json.load(urllib.request.urlopen(LETTA + '/v1/agents/'))
name_by_id = {a['id']: a.get('name', '?') for a in agents}

for g in groups:
    if g.get('manager_type') != 'sleeptime':
        continue
    parent = name_by_id.get(g.get('manager_agent_id'), g.get('manager_agent_id'))
    for sleeptime_id in g.get('agent_ids', []):
        req = urllib.request.Request(
            f'{LETTA}/v1/agents/{sleeptime_id}',
            data=json.dumps({'model': HANDLE}).encode(),
            headers={'Content-Type': 'application/json'}, method='PATCH')
        with urllib.request.urlopen(req, timeout=15) as r:
            updated = json.load(r)
        print(f'{parent} sleeptime ({sleeptime_id}): model -> {updated.get(\"model\")}')
"
