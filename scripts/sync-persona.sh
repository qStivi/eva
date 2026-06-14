#!/usr/bin/env bash
# Push persona/eva.md into a Letta agent's persona block (iterate personality live).
#   ./scripts/sync-persona.sh <agent_id>     (or set EVA_AGENT_ID)
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
AID="${1:-${EVA_AGENT_ID:-}}"
[ -n "$AID" ] || { echo "usage: sync-persona.sh <agent_id>  (or set EVA_AGENT_ID)" >&2; exit 1; }
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PERSONA_FILE="$DIR/persona/eva.md"
[ -f "$PERSONA_FILE" ] || { echo "missing $PERSONA_FILE" >&2; exit 1; }

PAYLOAD="$(python3 -c "import json,sys; print(json.dumps({'value': open(sys.argv[1]).read()}))" "$PERSONA_FILE")"
curl -s -X PATCH "$LETTA/v1/agents/$AID/core-memory/blocks/persona" \
     -H 'Content-Type: application/json' -d "$PAYLOAD" \
| python3 -c "import sys,json; d=json.load(sys.stdin); print('persona synced ->', len(d.get('value') or ''), 'chars')"
