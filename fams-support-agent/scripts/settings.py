#!/usr/bin/env python3
"""Print the agent's non-secret settings (from config/agent.env) as JSON.
The agent runs this at the start of every run instead of reading env vars."""
import json
import os

import common  # noqa: F401  (loads config/agent.env)

KEYS = ["SUPPORT_AGENT_START_AT", "SUPPORT_REVIEWER_EMAIL", "SUPPORT_EMAIL_MODE",
        "FRESHDESK_DOMAIN", "AZURE_BLOB_PREFIX", "NOTION_SUPPORT_PAGE_ID"]
SECRETS = ["FRESHDESK_API_KEY", "AZURE_BLOB_CONTAINER_SAS_URL", "SENDGRID_PROXY_BASE", "NOTION_API_KEY"]

out = {k: os.environ.get(k, "") for k in KEYS}
out["secrets_present"] = {k: bool(os.environ.get(k)) for k in SECRETS}
out["home"] = str(common.HOME)
print(json.dumps(out, indent=2))
