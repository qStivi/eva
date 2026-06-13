#!/usr/bin/env bash
# Load ONE model (default variant) and run the gauntlet + speed probe against it.
#   ./scripts/run-candidate.sh 'zai-org/glm-4.6v-flash'
# Letta already lists every downloaded model by its canonical handle (refreshed on
# its last restart), so we address openai-proxy/<key> directly. lms load logs the
# loaded size so we can infer the quant. Restart letta once if a new model id is
# missing from /v1/models.
set -uo pipefail
KEY="${1:?usage: run-candidate.sh <publisher/model-key>}"
DIR="$(cd "$(dirname "$0")" && pwd)"
LMS() { flatpak run --command=sh ai.lmstudio.lm-studio -c "\$HOME/.lmstudio/bin/lms $*"; }

printf '\n\033[1;35m========== %s ==========\033[0m\n' "$KEY"
LMS "unload --all" >/dev/null 2>&1
echo "[load] $KEY"
LMS "load '$KEY' -y --ttl 3600" 2>&1 | tr '\r' '\n' \
  | grep -Ei 'successfully|GiB|error|fail' | tail -3
LMS "ps" 2>&1 | grep -E "$(echo "$KEY" | cut -d/ -f2)|DEVICE"

bash "$DIR/gauntlet.sh" "openai-proxy/$KEY"
printf '\n\033[1;36m[decode speed]\033[0m\n'; bash "$DIR/tps.sh" "$KEY"
