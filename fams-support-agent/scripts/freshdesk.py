#!/usr/bin/env python3
"""Read-only Freshdesk command line for the FAMS Support Agent.

Same five read-only calls as the MCP server (freshdesk_api.py) (GET requests only - nothing here can
reply to, note on, edit or delete a ticket), but usable from Bash. This works no matter how
Paperclip launches Claude Code, so it doesn't depend on MCP servers being loaded.

  $PY $S/freshdesk.py recent [--per-page 30]
  $PY $S/freshdesk.py ticket <id> [--save FILE]      # --save writes the JSON for search_similar.py
  $PY $S/freshdesk.py conversation <id>
  $PY $S/freshdesk.py contact <id>
  $PY $S/freshdesk.py search "<freshdesk filter query>"
"""
import argparse
import json
import sys

import freshdesk_api as fd


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recent"); r.add_argument("--per-page", type=int, default=30); r.add_argument("--page", type=int, default=1)
    t = sub.add_parser("ticket"); t.add_argument("id", type=int); t.add_argument("--save")
    c = sub.add_parser("conversation"); c.add_argument("id", type=int)
    k = sub.add_parser("contact"); k.add_argument("id", type=int)
    s = sub.add_parser("search"); s.add_argument("query")
    a = ap.parse_args()
    try:
        if a.cmd == "recent":
            out = fd.list_recent_tickets(a.per_page, a.page)
        elif a.cmd == "ticket":
            out = fd.get_ticket(a.id)
            if a.save:
                with open(a.save, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False, indent=2)
        elif a.cmd == "conversation":
            out = fd.get_ticket_conversation(a.id)
        elif a.cmd == "contact":
            out = fd.get_contact(a.id)
        else:
            out = fd.search_tickets(a.query)
    except Exception as e:  # keep errors readable for the agent
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
