#!/usr/bin/env bash
# Upsert research_task and check_task into Letta's tool registry (source-code
# tools, same pattern register-toolsets.sh uses for use_toolset). Run this once
# eva-task-runner is up, THEN run register-toolsets.sh so the "research" group
# from toolsets.json actually resolves to real tool ids when it applies core.
#
#   ./scripts/register-research-tools.sh && ./scripts/register-toolsets.sh
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"

for name in research_task check_task; do
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
