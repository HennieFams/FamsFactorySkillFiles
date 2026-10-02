#!/usr/bin/env bash
# Install / update the FAMS Data Integrity Agent code INSIDE the Paperclip container.
#
# Why this exists: Paperclip's skill importer rejects skills that contain executable
# scripts, so the FAMS_INTEGRITY / FAMS_INTEGRITY_CHECK skills are docs-only and all
# code (check engine, read-only DB layer, tests) is installed here instead - same
# pattern as fams-support-agent.
#
# Installs to /paperclip/fams-integrity-agent (Paperclip's data volume; on the VM:
# /data/docker/volumes/docker_paperclip-data/_data/fams-integrity-agent). Survives
# container restarts; no compose change or restart needed.
#
# Run on the VM, from the cloned repo:   sudo bash fams-integrity-agent/deploy/install.sh
# Re-running is safe: code, config and SQL are refreshed from git; runs/ is kept.
set -euo pipefail

C=${PAPERCLIP_CONTAINER:-docker-server-1}
H=${INTEGRITY_AGENT_HOME:-/paperclip/fams-integrity-agent}
SRC=$(cd "$(dirname "$0")/.." && pwd)

docker inspect "$C" >/dev/null 2>&1 || { echo "Container $C not found (set PAPERCLIP_CONTAINER=...)"; exit 1; }
echo "Copying files into $C:$H ..."
docker exec "$C" rm -rf /tmp/fia-src
docker cp "$SRC" "$C":/tmp/fia-src

docker exec -e H="$H" "$C" bash -euo pipefail -c '
  mkdir -p "$H"/{config,agent,bin,runs,.uv}
  rm -rf "$H/scripts" "$H/tests" "$H/sql"
  cp -r /tmp/fia-src/scripts "$H/scripts"
  cp -r /tmp/fia-src/tests   "$H/tests"
  cp -r /tmp/fia-src/sql     "$H/sql"
  cp -r /tmp/fia-src/agent/. "$H/agent/"
  # config.json is version-controlled: git is the source of truth, change it there
  cp /tmp/fia-src/config/config.json "$H/config/config.json"

  if [ ! -x "$H/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$H/bin" UV_NO_MODIFY_PATH=1 sh
  fi
  export UV_CACHE_DIR="$H/.uv/cache" UV_TOOL_DIR="$H/.uv/tools" UV_PYTHON_INSTALL_DIR="$H/.uv/python"
  [ -x "$H/.venv/bin/python" ] || "$H/bin/uv" venv --python /usr/bin/python3 "$H/.venv"
  "$H/bin/uv" pip install --python "$H/.venv/bin/python" -q -r "$H/scripts/requirements.txt"

  rm -rf /tmp/fia-src
  OWNER=$(stat -c %U:%G /paperclip)
  chown -R "$OWNER" "$H"
  echo
  echo "Installed in $H"
  "$H/.venv/bin/python" -c "import pandas, pymssql; print(\"python deps: OK\")"
  echo "Offline self-test (no database needed):"
  cd "$H" && "$H/.venv/bin/python" -m pytest -q -p no:cacheprovider tests | tail -1
'
echo "Next: README step 2 (connection test with the agent's FAMS_DB_* secrets)."
