#!/usr/bin/env bash
# Install / update the FAMS Support Agent INSIDE the Paperclip container.
#
# Paperclip runs in Docker (container docker-server-1), and its agents run inside that
# container as root. Everything is installed under /paperclip/fams-support-agent, which is
# on Paperclip's existing data volume (on the VM: /data/docker/volumes/docker_paperclip-data/_data),
# so it survives container restarts/rebuilds and NO compose change or restart is needed.
#
# Run on the VM, from the cloned repo:   sudo bash deploy/install.sh
# Re-running is safe: code/config are refreshed; data/ (index, ledger, outbox) and an
# edited config/column_map.json are kept.
set -euo pipefail

C=${PAPERCLIP_CONTAINER:-docker-server-1}
H=${SUPPORT_AGENT_HOME:-/paperclip/fams-support-agent}
SRC=$(cd "$(dirname "$0")/.." && pwd)

docker inspect "$C" >/dev/null 2>&1 || { echo "Container $C not found (set PAPERCLIP_CONTAINER=...)"; exit 1; }
echo "Copying files into $C:$H ..."
docker exec "$C" rm -rf /tmp/fsa-src
docker cp "$SRC" "$C":/tmp/fsa-src

docker exec -e H="$H" "$C" bash -euo pipefail -c '
  mkdir -p "$H"/{scripts,config,agent,skills,workspace,bin,data/raw,data/outbox,.uv}
  cp -r /tmp/fsa-src/scripts/. "$H/scripts/"
  cp -r /tmp/fsa-src/agent/.   "$H/agent/"
  cp -r /tmp/fsa-src/skills/.  "$H/skills/"
  # agent working folder: dot-files are stored without the dot in git (easier to upload)
  mkdir -p "$H/workspace/.claude"
  cp /tmp/fsa-src/deploy/workspace/mcp.json             "$H/workspace/.mcp.json"
  cp /tmp/fsa-src/deploy/workspace/claude-settings.json "$H/workspace/.claude/settings.json"
  cp /tmp/fsa-src/config/agent.env.example "$H/config/"
  [ -f "$H/config/column_map.json" ] || cp /tmp/fsa-src/config/column_map.json "$H/config/"
  [ -f "$H/config/agent.env" ] || cp /tmp/fsa-src/config/agent.env.example "$H/config/agent.env"
  chmod 700 "$H/data"; chmod 600 "$H/config/agent.env"

  # uv (single static binary) into $H/bin - no change to the image
  if [ ! -x "$H/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$H/bin" UV_NO_MODIFY_PATH=1 sh
  fi
  export UV_CACHE_DIR="$H/.uv/cache" UV_TOOL_DIR="$H/.uv/tools" UV_PYTHON_INSTALL_DIR="$H/.uv/python"

  # Python venv for the scripts, using the image'"'"'s own python3 (no pip needed)
  [ -x "$H/.venv/bin/python" ] || "$H/bin/uv" venv --python /usr/bin/python3 "$H/.venv"
  "$H/bin/uv" pip install --python "$H/.venv/bin/python" -q -r "$H/scripts/requirements.txt"


  rm -rf /tmp/fsa-src
  # Same owner as the rest of Paperclip'"'"'s data, so agents can write here whichever user they run as
  OWNER=$(stat -c %U:%G /paperclip)
  chown -R "$OWNER" "$H"
  echo
  echo "Installed in $H"
  "$H/.venv/bin/python" -c "import azure.storage.blob, requests, mcp; print(\"python deps: OK\")"
  echo "uv: $("$H/bin/uv" --version)   uvx: $H/bin/uvx"
'
echo "Next: sudo bash deploy/set_config.sh   (secrets + settings), then README step 4."
