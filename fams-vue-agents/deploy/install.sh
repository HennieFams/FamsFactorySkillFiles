#!/usr/bin/env bash
# Install / update the FAMS Vue Agents pack INSIDE the Paperclip container.
#
# Same pattern as fams-support-agent / fams-integrity-agent: everything lives under
# /paperclip/fams-vue-agents on Paperclip's data volume (on the VM:
# /data/docker/volumes/docker_paperclip-data/_data/fams-vue-agents). No compose change,
# no Paperclip restart.
#
#   /paperclip/fams-vue-agents/
#     agent/        instructions for the 5 Vue agents (AGENTS-*.md, COMMON.md)
#     scripts/      devops.mjs (the only way to touch Azure DevOps), git-askpass.sh
#     config/       config.json (from git)
#     skills/       copy of FamsFactorySkillFiles/FAMS_VUE_AGENTS (incl. docs/ and fams-dispensing/reference/)
#     templates/    vue3-starter
#     secrets/      devops.pat  (chmod 600, never in git)
#     workspace/    the agents' working folder (cwd): repos/<repo> clones, .claude/settings.json
#
# Run on the VM, from the repo clone:
#   sudo bash fams-vue-agents/deploy/install.sh              # install/update, keep token
#   sudo bash fams-vue-agents/deploy/install.sh --token      # also (re)enter the Azure DevOps token
#   sudo bash fams-vue-agents/deploy/install.sh --verify-template   # also npm install + check the starter (slow)
set -euo pipefail

C=${PAPERCLIP_CONTAINER:-docker-server-1}
H=${FAMS_VUE_HOME:-/paperclip/fams-vue-agents}
SRC=$(cd "$(dirname "$0")/.." && pwd)
SKILLS=$(cd "$SRC/../FAMS_VUE_AGENTS" && pwd)
ASK_TOKEN=0; VERIFY_TEMPLATE=0
for a in "$@"; do
  case "$a" in
    --token) ASK_TOKEN=1 ;;
    --verify-template) VERIFY_TEMPLATE=1 ;;
    *) echo "unknown option $a"; exit 2 ;;
  esac
done

docker inspect "$C" >/dev/null 2>&1 || { echo "Container $C not found (set PAPERCLIP_CONTAINER=...)"; exit 1; }
# The user that runs the agents owns /paperclip (lesson from fams-notion-mcp/install.sh).
AGENT_USER=${AGENT_USER:-$(docker exec -u 0 "$C" stat -c %U /paperclip)}
AGENT_GROUP=$(docker exec -u 0 "$C" stat -c %G /paperclip)
echo "Container: $C   agents run as: $AGENT_USER"

for tool in git node npm; do
  docker exec "$C" sh -c "command -v $tool >/dev/null" || { echo "MISSING in container: $tool - install it (or tell Claude) before continuing"; exit 1; }
done
# Node >= 20.19 (ESLint 10 / Vite in the starter); devops.mjs itself needs >= 18 (fetch)
docker exec "$C" node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20||(a===20&&b>=19)?0:1)' \
  || { echo "Node $(docker exec "$C" node -v) in container; need >= 20.19"; exit 1; }
echo "git: $(docker exec "$C" git --version | cut -d' ' -f3)   node: $(docker exec "$C" node -v)   npm: $(docker exec "$C" npm -v)"

echo "Copying files into $C:$H ..."
docker exec -u 0 "$C" rm -rf /tmp/fva-src /tmp/fva-skills
docker cp "$SRC" "$C":/tmp/fva-src
docker cp "$SKILLS" "$C":/tmp/fva-skills

docker exec -u 0 -e H="$H" "$C" bash -euo pipefail -c '
  umask 022
  mkdir -p "$H"/{agent,scripts,config,tests,workspace/repos,workspace/knowledge,workspace/.claude}
  (umask 077; mkdir -p "$H/secrets")
  rm -rf "$H/scripts" "$H/tests" "$H/templates" "$H/skills" "$H/agent"
  cp -r /tmp/fva-src/scripts   "$H/scripts"
  cp -r /tmp/fva-src/tests     "$H/tests"
  cp -r /tmp/fva-src/agent     "$H/agent"
  cp -r /tmp/fva-src/templates "$H/templates"
  cp -r /tmp/fva-skills        "$H/skills"
  # Paperclip rejects skills that contain code, so fams-dispensing/reference/ lives in
  # skill-assets/ in git and is put back here, where the (unchanged) SKILL.md says it is.
  cp -r /tmp/fva-src/skill-assets/. "$H/skills/"
  cp /tmp/fva-src/config/config.json "$H/config/config.json"
  cp /tmp/fva-src/deploy/workspace/claude-settings.json "$H/workspace/.claude/settings.json"
  cp /tmp/fva-src/README.md "$H/README.md"
  rm -rf /tmp/fva-src /tmp/fva-skills
'

if [ "$ASK_TOKEN" = 1 ] || ! docker exec -u 0 "$C" sh -c "[ -s '$H/secrets/devops.pat' ]"; then
  read -rs -p "Azure DevOps PAT for fams-agents (Code: Read & write; Enter = keep current): " TOKEN; echo
  if [ -n "$TOKEN" ]; then
    printf '%s' "$TOKEN" | docker exec -u 0 -i "$C" sh -c "umask 077; cat > '$H/secrets/devops.pat'"
  fi
  unset TOKEN
fi

# Code, config, instructions and skills: root-owned, read-only for the agents (they can't
# edit their own guard rails). Workspace + secrets: owned by the agent user.
docker exec -u 0 -e H="$H" -e AU="$AGENT_USER" -e AG="$AGENT_GROUP" "$C" sh -euc '
  chown root:root "$H"; chmod 755 "$H"
  for d in agent scripts config tests skills templates README.md; do
    chown -R root:root "$H/$d"; chmod -R u=rwX,go=rX "$H/$d"
  done
  chmod 755 "$H/scripts/git-askpass.sh" "$H/scripts/devops.mjs"
  chown -R "$AU:$AG" "$H/workspace" "$H/secrets"
  chown root:root "$H/workspace/.claude" "$H/workspace/.claude/settings.json"; chmod 755 "$H/workspace/.claude"; chmod 644 "$H/workspace/.claude/settings.json"
  chmod 700 "$H/secrets"; [ -f "$H/secrets/devops.pat" ] && chmod 600 "$H/secrets/devops.pat" || true
'

echo
echo "Offline self-test (guard rails, no network):"
# Judge by node's exit code (the output format differs between Node versions).
if RESULT=$(docker exec -u "$AGENT_USER" -w /tmp "$C" sh -c "node --test --test-reporter=tap '$H'/tests/*.test.mjs 2>&1"); then
  echo "$RESULT" | grep -E "^# (tests|pass|fail)"
else
  echo "$RESULT" | tail -40; echo "SELF-TEST FAILED - fix before creating the agents"; exit 1
fi

if docker exec -u 0 "$C" sh -c "[ -s '$H/secrets/devops.pat' ]"; then
  echo "Azure DevOps token check:"
  docker exec -u "$AGENT_USER" "$C" node "$H/scripts/devops.mjs" whoami || echo "  -> token check FAILED (wrong/expired PAT, or no network to dev.azure.com)"
else
  echo "No Azure DevOps token yet - re-run with --token."
fi

if [ "$VERIFY_TEMPLATE" = 1 ]; then
  echo "Checking the Vue starter (npm install + lint + tests + build + budget) ..."
  docker exec -u "$AGENT_USER" "$C" sh -euc "
    rm -rf /tmp/fva-tpl && cp -r '$H/templates/vue3-starter' /tmp/fva-tpl && cd /tmp/fva-tpl
    npm ci --include=dev --no-audit --no-fund --loglevel=error
    if npm run check > /tmp/fva-check.log 2>&1; then tail -3 /tmp/fva-check.log; else tail -40 /tmp/fva-check.log; echo TEMPLATE CHECK FAILED; fi
    rm -rf /tmp/fva-tpl /tmp/fva-check.log"
fi
echo
echo "Installed in $H. Next: README section 3 (create the 5 agents in Paperclip)."
