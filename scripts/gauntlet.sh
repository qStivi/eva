#!/usr/bin/env bash
# Run the Eva model gauntlet against ONE model and report memory/perspective/speed.
#   ./scripts/gauntlet.sh openai-proxy/gpt-oss-20b
# Creates a throwaway agent, runs a fixed 4-turn convo, prints each reply + any
# memory tool calls, dumps the resulting human block, then deletes the agent
# (set KEEP=1 to keep it). Pre-warms the model first to dodge the cold-load timeout.
set -uo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
MODEL="${1:?usage: gauntlet.sh <openai-proxy/model-id>}"
KEY="$(grep -oP 'OPENAI_API_KEY=\K.*' ~/.config/letta/letta.env)"
BARE="${MODEL#openai-proxy/}"

say()  { printf '\n\033[1;36m%s\033[0m\n' "$*"; }

# --- pre-warm (load) the model directly via LM Studio so Letta's first call is fast
say "[pre-warm] $BARE"
curl -s -m 180 localhost:1234/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,sys;print(json.dumps({"model":sys.argv[1],"messages":[{"role":"user","content":"hi"}],"max_tokens":1}))' "$BARE")" \
  >/dev/null && echo "  loaded." || { echo "  pre-warm FAILED"; }

# --- create throwaway agent on this model
say "[create agent] model=$MODEL"
AID="$(EVA_MODEL="$MODEL" EVA_NAME="gauntlet-$(date +%s)" \
  bash "$(dirname "$0")/create-eva.sh" 2>&1 | tee /dev/stderr | grep -oP 'created agent: \Kagent-[0-9a-f-]+')"
[ -n "${AID:-}" ] || { echo "no agent id; abort"; exit 1; }

turn() {
  local msg="$1"
  printf '\n\033[1;33mYOU:\033[0m %s\n' "$msg"
  local t0 t1
  t0=$(date +%s.%N)
  curl -s --max-time 300 -H 'Content-Type: application/json' -X POST \
    "$LETTA/v1/agents/$AID/messages" \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"messages":[{"role":"user","content":sys.argv[1]}]}))' "$msg")" \
  | python3 -c '
import sys, json
d = json.load(sys.stdin)
for m in d.get("messages", []):
    t = m.get("message_type")
    if t == "tool_call_message":
        tc = m.get("tool_call", {})
        print("  [TOOL ->]", tc.get("name"), (tc.get("arguments") or "")[:200])
    elif t == "reasoning_message":
        r = (m.get("reasoning") or "")[:120].replace("\n"," ")
        if r: print("  [think]", r, "...")
    elif t == "assistant_message":
        print("EVA:", m.get("content"))
'
  t1=$(date +%s.%N)
  printf '\033[2m  (%.1fs)\033[0m\n' "$(echo "$t1 - $t0" | bc)"
}

turn "hey eva, rough day. how're you doing?"
turn "just so you know about me: i've got a younger brother named Leo, and i genuinely can't stand horror movies."
turn "what should we watch tonight then?"
turn "do you actually remember things about me, or just pretend to?"

say "[HUMAN BLOCK after convo]"
curl -s "$LETTA/v1/agents/$AID/core-memory/blocks/human" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("value","<none>"))'

if [ "${KEEP:-0}" = "1" ]; then
  say "[kept agent $AID]"
else
  curl -s -X DELETE "$LETTA/v1/agents/$AID" >/dev/null && say "[deleted agent $AID]"
fi
