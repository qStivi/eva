#!/usr/bin/env bash
# Create the "keeper" Eva agent in Letta from persona/eva.md.
#   EVA_MODEL=openai-proxy/qwen/qwen3-14b ./scripts/create-eva.sh
# Prints the new agent id. (Letta allows duplicate names; don't run twice blindly.)
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
MODEL="${EVA_MODEL:-openai-proxy/qwen/qwen3-8b}"
NAME="${EVA_NAME:-eva}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PERSONA_FILE="$DIR/persona/eva.md"
[ -f "$PERSONA_FILE" ] || { echo "missing $PERSONA_FILE" >&2; exit 1; }

PAYLOAD="$(python3 - "$PERSONA_FILE" "$MODEL" "$NAME" <<'PY'
import json, sys
persona = open(sys.argv[1]).read()
model, name = sys.argv[2], sys.argv[3]
print(json.dumps({
    "name": name,
    "model": model,
    "embedding_config": {
        "embedding_endpoint_type": "openai",
        "embedding_endpoint": "http://localhost:1234/v1",
        "embedding_model": "text-embedding-nomic-embed-text-v1.5",
        "embedding_dim": 768,
        "embedding_chunk_size": 300,
    },
    "memory_blocks": [
        {"label": "persona", "value": persona, "limit": 8000},
        {"label": "human",
         "value": "This is Stephan (handle: qStivi). I'll learn about him over time and save what matters to this block.",
         "limit": 8000},
    ],
    "include_base_tools": True,
}))
PY
)"

curl -s -X POST "$LETTA/v1/agents/" -H 'Content-Type: application/json' -d "$PAYLOAD" \
| python3 -c "import sys,json; d=json.load(sys.stdin); print('created agent:', d.get('id'), '| model:', d.get('llm_config',{}).get('model')) if d.get('id') else print('ERROR:', json.dumps(d)[:400])"
