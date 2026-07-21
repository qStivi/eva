#!/usr/bin/env bash
# Register the Home Assistant MCP server in Letta and attach its tools to the
# eva agent, so Eva can manage the shared list + control exposed devices.
#
# Prereqs (in Home Assistant): enable the "Model Context Protocol Server"
# integration, expose the entities/todo lists you want to Assist, and create a
# long-lived access token. Then put the URL + token in a chmod-600 env file:
#
#   ~/.config/letta/ha.env   (NOT committed):
#     HA_URL=http://192.168.x.x:8123
#     HA_TOKEN=<long-lived access token>
#
# Usage:  ./scripts/register-ha-mcp.sh          (resolves the 'eva' agent)
#         EVA_AGENT_ID=agent-... ./scripts/register-ha-mcp.sh
# Idempotent-ish: re-running re-adds/re-attaches (Letta tolerates repeats).
set -euo pipefail

LETTA="${LETTA_HOST:-http://localhost:8283}"
ENV_FILE="${HA_ENV_FILE:-$HOME/.config/letta/ha.env}"
SERVER_NAME="homeassistant"

[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (needs HA_URL + HA_TOKEN)" >&2; exit 1; }
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
: "${HA_URL:?HA_URL not set in $ENV_FILE}"
: "${HA_TOKEN:?HA_TOKEN not set in $ENV_FILE}"
SSE_URL="${HA_URL%/}/mcp_server/sse"

# Resolve the eva agent id (by name) unless one was provided.
AID="${EVA_AGENT_ID:-}"
if [ -z "$AID" ]; then
  AID="$(curl -s "$LETTA/v1/agents/" | python3 -c "import sys,json; d=json.load(sys.stdin); print(next((a['id'] for a in d if a.get('name')=='eva'), ''))")"
fi
[ -n "$AID" ] || { echo "could not resolve the 'eva' agent id" >&2; exit 1; }
echo "eva agent: $AID"
echo "HA MCP (SSE): $SSE_URL"

# Server config. auth_header + auth_token make Letta send "Authorization: Bearer <token>".
SERVER_JSON="$(python3 - "$SERVER_NAME" "$SSE_URL" "$HA_TOKEN" <<'PY'
import json, sys
name, url, token = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({
    "server_name": name,
    "type": "sse",
    "server_url": url,
    "auth_header": "Authorization",
    "auth_token": f"Bearer {token}",
}))
PY
)"

# 0) Validate connectivity before registering (best-effort; non-fatal).
echo "== testing HA MCP connectivity =="
curl -s -X POST "$LETTA/v1/tools/mcp/servers/test" \
     -H 'Content-Type: application/json' -d "$SERVER_JSON" \
| python3 -c "import sys,json;
try:
    d=json.load(sys.stdin); print('  test ok:', json.dumps(d)[:300])
except Exception as e:
    print('  (test endpoint returned non-JSON / unsupported; continuing)')" || true

# 1) Register the server (PUT adds it; ignore 'already exists').
echo "== registering server '$SERVER_NAME' =="
curl -s -X PUT "$LETTA/v1/tools/mcp/servers" \
     -H 'Content-Type: application/json' -d "$SERVER_JSON" \
| python3 -c "import sys,json;
try:
    d=json.load(sys.stdin); print('  ->', json.dumps(d)[:200])
except Exception:
    print('  -> (registered or already present)')" || true

# 2) List the tools the HA server exposes.
echo "== listing HA tools =="
TOOLS="$(curl -s "$LETTA/v1/tools/mcp/servers/$SERVER_NAME/tools" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(t.get('name','') for t in d if t.get('name')))")"
[ -n "$TOOLS" ] || { echo "no HA tools found — is the MCP Server integration on + entities exposed to Assist?" >&2; exit 1; }
echo "$TOOLS" | sed 's/^/  - /'

# 3) Register each tool into Letta's registry (so ids exist). We do NOT attach them
#    all to eva — attachment/membership is driven by toolsets.json via
#    scripts/register-toolsets.sh (lazy loading), so the context stays lean.
echo "== registering each HA tool into Letta's registry (not attaching) =="
while IFS= read -r TOOL; do
  [ -n "$TOOL" ] || continue
  TID="$(curl -s -X POST "$LETTA/v1/tools/mcp/servers/$SERVER_NAME/$TOOL" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || true)"
  if [ -z "$TID" ]; then echo "  ! $TOOL: could not register (skipped)"; else echo "  + $TOOL registered ($TID)"; fi
done <<< "$TOOLS"

echo "== done registering HA tools. =="
echo "Next: ./scripts/register-toolsets.sh   (applies the lean core + makes 'home'/'media' loadable)"
