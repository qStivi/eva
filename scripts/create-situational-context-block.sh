#!/usr/bin/env bash
# One-time setup: create eva-web's ephemeral-refresh memory blocks — see
# eva-web/situational_context.py, eva-web/recall.py, and
# docs/2026-08-22-situational-context-spec.md (both the HA-fields half and
# the "Conversational recall" section) — and attach them to both eva and
# eva-spike, as SEPARATE blocks per agent (not shared — same convention
# persona/human already use).
#
# Marks every block read_only=true. eva-web still writes to them fine — it
# uses the agent-scoped PATCH /v1/agents/{id}/core-memory/blocks/{label}
# admin path, which bypasses read_only. What read_only actually blocks is
# Eva's own memory_insert/memory_replace tools touching a block — needed
# after a live incident (2026-08-22) where she fabricated fake Spotify/Steam
# data and then used those tools to write the fabrication into
# situational_context itself, so it kept looking "confirmed" on the next
# turn. Confirmed live that a read_only block makes the tool call fail
# cleanly ("This block is read-only and cannot be edited.") instead of
# corrupting the block. conversation_recall gets the same lock as a matter
# of course, even though nothing's caused trouble there yet.
#
# Idempotent-ish: skips creating a block for an agent that already has one
# with a given label.
#
# Usage:  ./scripts/create-situational-context-block.sh
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
LABELS=(situational_context conversation_recall)

agent_id() {
  curl -s "$LETTA/v1/agents/" | python3 -c "
import sys, json
name = sys.argv[1]
d = json.load(sys.stdin)
print(next((a['id'] for a in d if a.get('name') == name), ''))
" "$1"
}

ensure_block() {
  local agent="$1" agent_id="$2" label="$3"
  local existing
  existing="$(curl -s "$LETTA/v1/agents/$agent_id/core-memory/blocks" \
    | python3 -c "
import sys, json
label = sys.argv[1]
d = json.load(sys.stdin)
print(next((b['id'] for b in d if b.get('label') == label), ''))
" "$label")"
  if [ -n "$existing" ]; then
    echo "$agent ($agent_id): already has $label ($existing) — leaving it"
    return
  fi
  local bid
  bid="$(curl -s -X POST "$LETTA/v1/blocks/" -H 'Content-Type: application/json' \
    -d "{\"label\":\"$label\",\"value\":\"(not yet refreshed)\",\"limit\":2000}" \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")"
  curl -s -X PATCH "$LETTA/v1/agents/$agent_id/core-memory/blocks/attach/$bid" > /dev/null
  curl -s -X PATCH "$LETTA/v1/blocks/$bid" -H 'Content-Type: application/json' \
    -d '{"read_only": true}' > /dev/null
  echo "$agent ($agent_id): created + attached + locked $label ($bid)"
}

for name in eva eva-spike; do
  aid="$(agent_id "$name")"
  if [ -z "$aid" ]; then
    echo "no '$name' agent found — skipping" >&2
    continue
  fi
  for label in "${LABELS[@]}"; do
    ensure_block "$name" "$aid" "$label"
  done
done
