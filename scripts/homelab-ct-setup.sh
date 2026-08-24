#!/usr/bin/env bash
# One-shot provisioning for a fresh Debian/Ubuntu Proxmox CT that will host
# eva's backend (see docs/2026-08-24-homelab-migration-plan.md and
# docs/2026-08-24-homelab-how-to-run.md for the full picture — this script
# only covers "make the box able to run the stack", not the actual data
# migration/cutover, which is manual and one-time.
#
# Idempotent-ish: safe to re-run, each step just no-ops if already done.
# Run as the service user (not root) inside the CT — everything here assumes
# a rootless Podman + systemd --user setup, same pattern as the desktop.
#
# Usage: ./scripts/homelab-ct-setup.sh
set -euo pipefail

echo "== System packages =="
sudo apt-get update -qq
sudo apt-get install -y -qq \
    podman uidmap slirp4netns \
    python3 python3-pip python3-venv \
    git curl ca-certificates gnupg

echo "== Node.js (for dsh — DeepSeek Harness) =="
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y -qq nodejs
fi
node --version

echo "== dsh (DeepSeek Harness) =="
if ! command -v dsh >/dev/null 2>&1; then
    sudo npm install -g @deepseek-ai/dsh
fi
dsh --version || true

echo "== Python deps (stdlib-only stack + cryptography for fcm.py's JWT signing) =="
pip3 install --user --break-system-packages cryptography 2>/dev/null \
    || pip3 install --user cryptography

echo "== Podman lingering (so user Quadlets survive without an active login) =="
loginctl enable-linger "$USER"

echo "== Directories =="
mkdir -p ~/.config/containers/systemd ~/.config/systemd/user
mkdir -p ~/.config/letta ~/.config/eva-task-runner ~/.config/eva-web ~/.config/cloudflared
mkdir -p ~/.local/share/eva ~/eva-workspace

echo "== Clone the repo (skip if already present) =="
if [ ! -d ~/projects/eva/.git ]; then
    mkdir -p ~/projects
    git clone https://github.com/qStivi/eva.git ~/projects/eva
else
    echo "  ~/projects/eva already exists, skipping clone"
fi

echo "== Letta core patches (from the repo, no secrets in these) =="
cp ~/projects/eva/letta-patches/url_validation.py \
   ~/projects/eva/letta-patches/openai_client.py \
   ~/projects/eva/letta-patches/helpers.py \
   ~/.config/letta/
echo "  copied to ~/.config/letta/ — see letta-patches/README.md for what each does"

cat <<'EOF'

== Done with the automatable part. Manual steps remain — see
   docs/2026-08-24-homelab-how-to-run.md for the full checklist:
     - copy the Quadlet unit files + systemd user units from the repo/desktop
     - copy secrets (letta.env, eva-task-runner.env, eva-web.env,
       cloudflared/eva.env, the FCM service-account JSON) — none of these
       are in git, they need a manual scp
     - migrate Letta's Postgres data (pg_dump / restore)
     - enable + start every systemd user unit
     - verify, then cut over
EOF
