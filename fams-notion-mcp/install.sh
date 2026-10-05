#!/usr/bin/env bash
# Give Paperclip's Claude agents a Notion MCP server (read + edit pages).
#
# Uses Notion's own open-source server (@notionhq/notion-mcp-server) with an INTERNAL
# INTEGRATION TOKEN, because the hosted Notion MCP (mcp.notion.com) needs a browser OAuth
# login and doesn't support unattended agents yet.
#
# Installs into Paperclip's data volume: /paperclip/notion-mcp (survives restarts, no compose change)
#   run.sh   - starts the server, reading the token from ./token (chmod 600)
#   token    - the Notion integration secret (never in git, never in .claude.json)
# Then registers it for the agents as a user-scope MCP server called "notion".
#
# Run on the VM, from this folder:   sudo bash install.sh
# Re-run any time: keeps the token unless you paste a new one; --remove unregisters it.
set -euo pipefail
C=${PAPERCLIP_CONTAINER:-docker-server-1}
D=/paperclip/notion-mcp
VERSION=${NOTION_MCP_VERSION:-2.5.2}

docker inspect "$C" >/dev/null 2>&1 || { echo "Container $C not found (set PAPERCLIP_CONTAINER=...)"; exit 1; }

# Who runs the agents, and where is their Claude config? (same as the Paperclip server process)
AGENT_USER=$(docker inspect -f '{{.Config.User}}' "$C"); AGENT_USER=${AGENT_USER:-root}
AGENT_ENV=$(docker exec -u 0 "$C" sh -c 'tr "\0" "\n" < /proc/1/environ | grep -E "^(HOME|CLAUDE_CONFIG_DIR)=" || true')
ENVARGS=(); while IFS= read -r l; do [ -n "$l" ] && ENVARGS+=(-e "$l"); done <<< "$AGENT_ENV"
echo "Agents run as: $AGENT_USER   ${AGENT_ENV//$'\n'/  }"
claude_as_agent() { docker exec -u "$AGENT_USER" "${ENVARGS[@]}" "$C" claude "$@"; }
docker exec "$C" sh -c 'command -v claude >/dev/null' || { echo "claude CLI not found on PATH in $C"; exit 1; }

if [ "${1:-}" = "--remove" ]; then
  claude_as_agent mcp remove --scope user notion || true
  echo "Removed the notion MCP server from the agents' config (files in $D kept)."; exit 0
fi

echo "Installing @notionhq/notion-mcp-server@$VERSION into $C:$D ..."
docker exec -u 0 "$C" sh -euc "
  mkdir -p '$D'
  cd '$D' && npm install --silent --no-audit --no-fund --omit=dev @notionhq/notion-mcp-server@$VERSION >/dev/null
  cat > '$D/run.sh' <<'EOF'
#!/bin/sh
# Started by Claude Code (stdio). Token comes from the file next to this script.
D=\$(dirname \"\$0\")
NOTION_TOKEN=\$(cat \"\$D/token\") exec \"\$D/node_modules/.bin/notion-mcp-server\" \"\$@\"
EOF
  chmod 755 '$D/run.sh'
"

read -rs -p "Notion integration secret (ntn_…; Enter = keep current): " TOKEN; echo
if [ -n "$TOKEN" ]; then
  printf '%s' "$TOKEN" | docker exec -u 0 -i "$C" sh -c "cat > '$D/token'"
fi
docker exec "$C" sh -c "[ -s '$D/token' ]" || { echo "No token saved yet - re-run and paste it."; exit 1; }
OWNER=$(docker exec "$C" stat -c %U:%G /paperclip)
docker exec -u 0 "$C" sh -c "chown -R $OWNER '$D'; chown $AGENT_USER '$D/token'; chmod 600 '$D/token'"

# Quick check: the server starts and the token works (asks Notion who the integration is)
echo "Checking the token with Notion ..."
docker exec -u "$AGENT_USER" "$C" sh -c "
  printf '%s\n' \
   '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"install-check\",\"version\":\"1\"}}}' \
   '{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}' \
   '{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"API-get-self\",\"arguments\":{}}}' \
  | timeout 30 '$D/run.sh' 2>/dev/null | grep '\"id\":2' | head -c 400; echo"

# Register for the agents (user scope = every Claude agent that shares this config)
claude_as_agent mcp remove --scope user notion >/dev/null 2>&1 || true
claude_as_agent mcp add --scope user notion -- "$D/run.sh"
claude_as_agent mcp list | grep -i notion || true
echo
echo "Done. New agent runs get the mcp__notion__* tools. They can only see pages shared with the integration."
