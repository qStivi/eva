#!/usr/bin/env bash
# Measure decode throughput (tokens/sec) of the currently-loaded "evatest" model.
# Generates ~300 tokens from a fixed prompt and reports completion_tokens / time.
set -uo pipefail
KEY="$(grep -oP 'OPENAI_API_KEY=\K.*' ~/.config/letta/letta.env)"
MODEL="${1:-evatest}"
t0=$(date +%s.%N)
RESP=$(curl -s -m 180 localhost:1234/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,sys;print(json.dumps({"model":sys.argv[1],"messages":[{"role":"user","content":"Write a 250-word vivid description of a thunderstorm over a city at night. No preamble."}],"max_tokens":350,"temperature":0.7}))' "$MODEL")")
t1=$(date +%s.%N)
RESP="$RESP" DT="$(echo "$t1 - $t0" | bc)" python3 -c '
import sys,json,os
d=json.loads(os.environ["RESP"])
u=d.get("usage",{})
ct=u.get("completion_tokens"); pt=u.get("prompt_tokens")
dt=float(os.environ["DT"])
print(f"  decode: {ct} tok in {dt:.1f}s = {ct/dt:.1f} t/s   (prompt {pt} tok)" if ct else f"  no usage: {json.dumps(d)[:200]}")
'
