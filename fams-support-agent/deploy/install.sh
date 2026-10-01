#!/usr/bin/env bash
# Install the FAMS Support Agent files on the Paperclip VM.
# Run from the unzipped fams-support-agent folder:   sudo bash deploy/install.sh
# Re-running is safe: code/config are refreshed; data/ (index, ledger, outbox) is kept.
set -euo pipefail

HOME_DIR=${SUPPORT_AGENT_HOME:-/data/fams-support-agent}
RUN_AS=${PAPERCLIP_USER:-$(stat -c %U /data 2>/dev/null || echo "$SUDO_USER")}   # user that runs Paperclip
SRC=$(cd "$(dirname "$0")/.." && pwd)

echo "Installing to $HOME_DIR (owner: $RUN_AS)"
mkdir -p "$HOME_DIR"/{scripts,config,agent,skills,workspace,data/raw,data/outbox}
cp -r "$SRC"/scripts/* "$HOME_DIR/scripts/"
cp -r "$SRC"/agent/* "$HOME_DIR/agent/"
cp -r "$SRC"/skills/* "$HOME_DIR/skills/"
for f in mcp.json claude-settings.json; do cp "$SRC/config/$f" "$HOME_DIR/config/$f"; done
# keep a column_map you've already edited
[ -f "$HOME_DIR/config/column_map.json" ] || cp "$SRC/config/column_map.json" "$HOME_DIR/config/"

# Python deps (system python, no venv needed for two small libs)
apt-get update -qq && apt-get install -y -qq python3-pip >/dev/null
pip3 install --quiet --break-system-packages -r "$HOME_DIR/scripts/requirements.txt"

# uv/uvx for the Freshdesk MCP server, installed for the Paperclip user
if ! sudo -u "$RUN_AS" bash -lc 'command -v uvx' >/dev/null 2>&1; then
  sudo -u "$RUN_AS" bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi
sudo -u "$RUN_AS" bash -lc 'uvx --quiet freshdesk-mcp --help >/dev/null 2>&1 || true'   # pre-fetch

chown -R "$RUN_AS":"$RUN_AS" "$HOME_DIR"
chmod 700 "$HOME_DIR/data"
echo
echo "Done. Next: README step 3 (secrets) and step 4 (first index build)."
echo "uvx path for the Paperclip user: $(sudo -u "$RUN_AS" bash -lc 'command -v uvx' || echo 'NOT FOUND')"
