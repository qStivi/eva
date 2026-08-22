#!/usr/bin/env bash
# One-time setup: create the `situational_context` memory block (see
# eva-web/situational_context.py and docs/2026-08-22-situational-context-spec.md)
# and attach it to both eva and eva-spike, as SEPARATE blocks (not shared —
# same convention persona/human already use).
#
# Marks both blocks read_only=true. eva-web still writes to them fine — it
# uses the agent-scoped PATCH /v1/agents/{id}/core-memory/blocks/{label}
# admin path, which bypasses read_only. What read_only actually blocks is
# Eva's own memory_insert/memory_replace tools touching this block — needed
# after a live incident (2026-08-22) where she fabricated fake Spotify/Steam
# data and then used those tools to write the fabrication into the block
# itself, so it kept looking "confirmed" on the next turn. Confirmed live
# that a read_only block makes the tool call fail cleanly ("This block is
# read-only and cannot be edited.") instead of corrupting the block.
#
# Idempotent-ish: skips creating a block for an agent that already has one
# labeled situational_context.
#
# Usage:  ./scripts/create-situational-context-block.sh
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"

agent_id() {
  curl -s "$LETTA/v1/agents/" | python3 -c "
import sys, json
name = sys.argv[1]
d = json.load(sys.stdin)
print(next((a['id'] for a in d if a.get('name') == name), ''))
" "$1"
}

ensure_block() {
  local agent="$1" agent_id="$2"
  local existing
  existing="$(curl -s "$LETTA/v1/agents/$agent_id/core-memory/blocks" \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(next((b['id'] for b in d if b.get('label') == 'situational_context'), ''))
")"
  if [ -n "$existing" ]; then
    echo "$agent ($agent_id): already has situational_context ($existing) — leaving it"
    return
  fi
  local bid
  bid="$(curl -s -X POST "$LETTA/v1/blocks/" -H 'Content-Type: application/json' \
    -d '{"label":"situational_context","value":"(not yet refreshed)","limit":2000}' \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")"
  curl -s -X PATCH "$LETTA/v1/agents/$agent_id/core-memory/blocks/attach/$bid" > /dev/null
  curl -s -X PATCH "$LETTA/v1/blocks/$bid" -H 'Content-Type: application/json' \
    -d '{"read_only": true}' > /dev/null
  echo "$agent ($agent_id): created + attached + locked $bid"
}

for name in eva eva-spike; do
  aid="$(agent_id "$name")"
  if [ -z "$aid" ]; then
    echo "no '$name' agent found — skipping" >&2
    continue
  fi
  ensure_block "$name" "$aid"
done
