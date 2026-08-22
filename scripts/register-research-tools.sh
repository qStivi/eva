#!/usr/bin/env bash
# Upsert eva-task-runner-backed tools into Letta's tool registry (source-code
# tools, same pattern register-toolsets.sh uses for use_toolset): research_task
# and check_task (background research jobs), create_timer (reminders/
# alarms — docs/2026-08-22-timers-reminders-spec.md), and delegate_to_harness
# (DeepSeek Harness + Mistral, HITL-gated — docs/2026-08-22-delegate-to-claude-spec.md).
# Run this once eva-task-runner is up, THEN run register-toolsets.sh so
# toolsets.json's 'research'/'work' groups and 'core' membership resolve to
# real tool ids.
#
#   ./scripts/register-research-tools.sh && ./scripts/register-toolsets.sh
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"

for name in research_task check_task create_timer delegate_to_harness; do
  src="$DIR/tools/$name.py"
  [ -f "$src" ] || { echo "missing $src" >&2; exit 1; }
  echo "== registering $name =="
  python3 - "$src" "$LETTA" <<PY
import json, sys, urllib.request
src = open(sys.argv[1]).read()
payload = json.dumps({"source_code": src, "source_type": "python"}).encode()
req = urllib.request.Request(sys.argv[2] + "/v1/tools/", data=payload, method="PUT",
                             headers={"Content-Type": "application/json"})
d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
print("  $name ->", d.get("id") or ("ERR " + json.dumps(d)[:200]))
PY
done

echo "Now run: ./scripts/register-toolsets.sh   (applies the 'research' group membership)"
