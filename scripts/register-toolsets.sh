#!/usr/bin/env bash
# Apply Eva's lazy-tool-loading scheme from toolsets.json:
#   1. build tools/use_toolset.py, search_tools.py, call_tool.py with the group
#      registry injected, upsert them into Letta;
#   2. set the eva agent to the lean 'core' set (attach core, detach every group tool).
# Groups then load on demand — either the old way (use_toolset("home"|"media"|...),
# still supported as a fallback) or the new way (search_tools(query) then
# call_tool(name, args), which needs no attach step at all — see
# docs/2026-08-22-tool-discovery-spec.md).
#
# Run AFTER the domain tools exist in Letta's registry (e.g. scripts/register-ha-mcp.sh).
# Idempotent — safe to re-run whenever toolsets.json changes.
#   ./scripts/register-toolsets.sh            (resolves the 'eva' agent)
#   EVA_AGENT_ID=agent-... ./scripts/register-toolsets.sh
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
TS="$DIR/toolsets.json"
[ -f "$TS" ] || { echo "missing $TS" >&2; exit 1; }
for f in use_toolset search_tools call_tool; do
  [ -f "$DIR/tools/$f.py" ] || { echo "missing $DIR/tools/$f.py" >&2; exit 1; }
done

AID="${EVA_AGENT_ID:-}"
if [ -z "$AID" ]; then
  AID="$(curl -s "$LETTA/v1/agents/" | python3 -c "import sys,json; d=json.load(sys.stdin); print(next((a['id'] for a in d if a.get('name')=='eva'), ''))")"
fi
[ -n "$AID" ] || { echo "could not resolve the 'eva' agent id" >&2; exit 1; }
echo "eva agent: $AID"

# 1) Build each GROUPS-injected tool from toolsets.json, then upsert it into Letta.
echo "== registering use_toolset / search_tools / call_tool (groups injected) =="
python3 - "$TS" "$DIR/tools" "$LETTA" <<'PY'
import json, sys, urllib.request
ts_path, tools_dir, letta = sys.argv[1], sys.argv[2], sys.argv[3]
ts = json.load(open(ts_path))
descriptions = {
    "use_toolset": "Load/unload a named set of tools on demand (lazy tool loading).",
    "search_tools": "Search for a gated tool by what you're trying to do.",
    "call_tool": "Call a tool found via search_tools, no attach step needed.",
}
for name, desc in descriptions.items():
    src = open(f"{tools_dir}/{name}.py").read().replace("{}  # __INJECT_GROUPS__", json.dumps(ts["groups"]))
    payload = json.dumps({"source_code": src, "source_type": "python", "description": desc}).encode()
    req = urllib.request.Request(letta + "/v1/tools/", data=payload, method="PUT",
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    print(f"  {name} ->", d.get("id") or ("ERR " + json.dumps(d)[:200]))
PY

# 2) Apply membership: attach 'core', detach every group tool.
echo "== applying lean core to eva =="
python3 - "$TS" "$LETTA" "$AID" <<'PY'
import json, sys, urllib.request
ts = json.load(open(sys.argv[1])); letta, aid = sys.argv[2], sys.argv[3]
core = set(ts["core"])
def api(method, path):
    req = urllib.request.Request(letta + path, method=method, headers={"Content-Type": "application/json"})
    b = urllib.request.urlopen(req, timeout=15).read().decode()
    return json.loads(b) if b else None
idbyname = {t["name"]: t["id"] for t in api("GET", "/v1/tools/?limit=300") if t.get("name")}
attached = {t["name"] for t in api("GET", "/v1/agents/%s/tools?limit=300" % aid)}
added, removed = [], []
for tn in sorted(core):
    if tn not in attached and tn in idbyname:
        api("PATCH", "/v1/agents/%s/tools/attach/%s" % (aid, idbyname[tn])); added.append(tn)
# Detach ANYTHING attached that isn't core — not just current group members. Core
# is meant to be the exhaustive default set, so a tool dropped from toolsets.json
# entirely (not moved into a group) must still get put away, not linger attached
# forever because it's no longer "managed" by any group.
for tn in sorted(attached):
    if tn not in core and tn in idbyname:
        api("PATCH", "/v1/agents/%s/tools/detach/%s" % (aid, idbyname[tn])); removed.append(tn)
print("  attached core:", added or "(already lean)")
print("  detached groups:", removed or "(none attached)")
missing = [t for t in core if t not in idbyname]
if missing:
    print("  ! core tools missing from registry (register their MCP first):", missing)
PY

echo "== eva's tools now =="
curl -s "$LETTA/v1/agents/$AID/tools?limit=300" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('  count:', len(d)); [print('   -', t['name']) for t in sorted(d, key=lambda x: x['name'])]"
echo "(remember to sync the persona: ./scripts/sync-persona.sh $AID)"
