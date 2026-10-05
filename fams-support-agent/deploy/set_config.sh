#!/usr/bin/env bash
# Write secrets + settings into /paperclip/fams-support-agent/config/agent.env inside the
# Paperclip container. Prompts hide what you type; press Enter to keep the current value.
# Run on the VM:   sudo bash deploy/set_config.sh
set -euo pipefail
C=${PAPERCLIP_CONTAINER:-docker-server-1}
F=/paperclip/fams-support-agent/config/agent.env
PY=/paperclip/fams-support-agent/.venv/bin/python

ask() {  # name, prompt, secret(0/1)
  local v
  if [ "$3" = 1 ]; then read -rs -p "$2: " v; echo; else read -r -p "$2: " v; fi
  [ -n "$v" ] && ARGS+=("$1=$v")
  return 0
}
ARGS=()
echo "Leave blank to keep the current value."
ask FRESHDESK_API_KEY            "Freshdesk API key" 1
ask AZURE_BLOB_CONTAINER_SAS_URL "Blob SAS URL" 1
ask SENDGRID_PROXY_BASE          "SendGrid proxy base URL (…/api/SendGrid)" 1
ask NOTION_API_KEY               "Notion integration token (ntn_…)" 1
ask SUPPORT_EMAIL_MODE           "Email mode [dryrun|fams_proxy]" 0
ask SUPPORT_AGENT_START_AT       "Ignore tickets created before (UTC, e.g. 2026-10-01T12:00:00Z)" 0
# Recipients: one comma-separated list sets both who gets the drafts and the allow-list
read -r -p "Reviewer email(s), comma-separated (e.g. schalk@fams.co.za,hennie@fams.co.za): " R
R=$(printf '%s' "$R" | tr -d ' ')
[ -n "$R" ] && ARGS+=("SUPPORT_REVIEWER_EMAIL=$R" "SUPPORT_EMAIL_ALLOWED_TO=$R")

# pass values through stdin so they never appear in the process list
printf '%s\n' "${ARGS[@]+"${ARGS[@]}"}" | docker exec -i "$C" "$PY" -c '
import sys, re
path = sys.argv[1]
updates = dict(l.rstrip("\n").split("=", 1) for l in sys.stdin if "=" in l)
lines = open(path).read().splitlines()
seen = set()
for i, l in enumerate(lines):
    k = l.split("=", 1)[0].strip()
    if k in updates and not l.lstrip().startswith("#"):
        lines[i] = f"{k}={updates[k]}"; seen.add(k)
lines += [f"{k}={v}" for k, v in updates.items() if k not in seen]
open(path, "w").write("\n".join(lines) + "\n")
print("updated:", ", ".join(updates) or "nothing")
' "$F"
docker exec "$C" sh -c "chown \$(stat -c %U:%G /paperclip) $F && chmod 600 $F"
docker exec "$C" "$PY" /paperclip/fams-support-agent/scripts/settings.py
