#!/usr/bin/env python3
"""Record which Freshdesk tickets the agent has already handled, so a ticket is never
processed (or emailed) twice — even if the webhook fires twice or a run is retried.

  python3 ledger.py check   <ticket_id>                 -> prints "new" or "done:<outcome>"  (exit 0)
  python3 ledger.py claim   <ticket_id>                 -> exit 0 if claimed now, exit 3 if already claimed/done
  python3 ledger.py mark    <ticket_id> <outcome> [--confidence high|medium|low] [--matched 123,456] [--note TEXT]
        outcome: sent | no_match | skipped | error
  python3 ledger.py unseen  <id> [<id> ...]             -> prints the ids not yet in the ledger (one per line)
  python3 ledger.py recent  [N]                          -> last N entries as JSON
  python3 ledger.py release <ticket_id>                  -> remove a stale claim/error so it can be retried
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone

from common import LEDGER_DB


def db():
    LEDGER_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(LEDGER_DB)
    con.execute("""CREATE TABLE IF NOT EXISTS processed (
        ticket_id TEXT PRIMARY KEY, status TEXT NOT NULL, outcome TEXT, confidence TEXT,
        matched_ids TEXT, note TEXT, claimed_at TEXT, finished_at TEXT)""")
    return con


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "claim", "release"):
        sub.add_parser(name).add_argument("ticket_id")
    m = sub.add_parser("mark")
    m.add_argument("ticket_id")
    m.add_argument("outcome", choices=["sent", "no_match", "skipped", "error"])
    m.add_argument("--confidence", default="")
    m.add_argument("--matched", default="")
    m.add_argument("--note", default="")
    u = sub.add_parser("unseen")
    u.add_argument("ids", nargs="+")
    r = sub.add_parser("recent")
    r.add_argument("n", nargs="?", type=int, default=20)
    a = ap.parse_args()
    con = db()

    if a.cmd == "check":
        row = con.execute("SELECT status, outcome FROM processed WHERE ticket_id=?", (a.ticket_id,)).fetchone()
        print("new" if not row else f"{row[0]}:{row[1] or ''}")
    elif a.cmd == "claim":
        try:
            con.execute("INSERT INTO processed (ticket_id, status, claimed_at) VALUES (?, 'claimed', ?)", (a.ticket_id, now()))
            con.commit()
            print("claimed")
        except sqlite3.IntegrityError:
            print("already-claimed")
            sys.exit(3)
    elif a.cmd == "mark":
        con.execute(
            """INSERT INTO processed (ticket_id, status, outcome, confidence, matched_ids, note, claimed_at, finished_at)
               VALUES (?, 'done', ?, ?, ?, ?, ?, ?)
               ON CONFLICT(ticket_id) DO UPDATE SET status='done', outcome=excluded.outcome,
                 confidence=excluded.confidence, matched_ids=excluded.matched_ids, note=excluded.note,
                 finished_at=excluded.finished_at""",
            (a.ticket_id, a.outcome, a.confidence, a.matched, a.note[:2000], now(), now()),
        )
        con.commit()
        print("ok")
    elif a.cmd == "unseen":
        known = {r[0] for r in con.execute(
            f"SELECT ticket_id FROM processed WHERE ticket_id IN ({','.join('?' * len(a.ids))})", a.ids)}
        for i in a.ids:
            if i not in known:
                print(i)
    elif a.cmd == "recent":
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM processed ORDER BY COALESCE(finished_at, claimed_at) DESC LIMIT ?", (a.n,))
        print(json.dumps([dict(x) for x in rows], indent=2))
    elif a.cmd == "release":
        con.execute("DELETE FROM processed WHERE ticket_id=? AND (status='claimed' OR outcome='error')", (a.ticket_id,))
        con.commit()
        print("released")


if __name__ == "__main__":
    main()
