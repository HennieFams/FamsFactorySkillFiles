#!/bin/sh
# GIT_ASKPASS helper for scripts/devops.mjs. Root-owned (install.sh). Azure DevOps accepts
# any username with a PAT as the password; the token never appears in a URL or git config.
case "$1" in
  Username*) echo "fams-agents" ;;
  *) cat /paperclip/fams-vue-agents/secrets/devops.pat ;;
esac
