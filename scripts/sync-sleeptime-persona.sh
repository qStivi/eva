#!/usr/bin/env bash
# Push persona/eva-sleeptime.md into a sleeptime agent's memory_persona block
# (the hygiene rules that steer what it folds into `human`) — same pattern as
# sync-persona.sh, different agent + block label. Pass the SLEEPTIME agent's
# id (e.g. eva-sleeptime, not eva itself) — find it via
#   curl -s $LETTA_HOST/v1/groups/ | jq -r '.[] | .agent_ids[]'
#
#   ./scripts/sync-sleeptime-persona.sh <sleeptime_agent_id>
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
AID="${1:?usage: sync-sleeptime-persona.sh <sleeptime_agent_id>}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PERSONA_FILE="$DIR/persona/eva-sleeptime.md"
[ -f "$PERSONA_FILE" ] || { echo "missing $PERSONA_FILE" >&2; exit 1; }

PAYLOAD="$(python3 -c "import json,sys; print(json.dumps({'value': open(sys.argv[1]).read()}))" "$PERSONA_FILE")"
curl -s -X PATCH "$LETTA/v1/agents/$AID/core-memory/blocks/memory_persona" \
     -H 'Content-Type: application/json' -d "$PAYLOAD" \
| python3 -c "import sys,json; d=json.load(sys.stdin); print('memory_persona synced ->', len(d.get('value') or ''), 'chars')"
