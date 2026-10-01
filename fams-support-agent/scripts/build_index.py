#!/usr/bin/env python3
"""Build the searchable history index (SQLite + FTS5) from the exports in data/raw.

Default input: per-ticket Freshdesk JSON files (ticket_<id>.json, each with an
"original" ticket object and its "conversations"), as uploaded monthly to Blob.
A CSV layout is also supported - see config/column_map.json ("format").

Keeps only resolved/closed tickets, drops outbound agent-initiated tickets,
redacts credentials, and splits each conversation into:
  resolution       - the support agents' public replies (what the customer was told)
  followups        - the customer's later messages (extra symptoms)
  internal_notes   - private notes (for the reviewer only, never customer-facing)

Usage:  python3 build_index.py [--raw-dir DIR] [--db PATH] [--include-unresolved]
"""
import argparse
import csv
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from common import RAW_DIR, INDEX_DB, load_column_map, clean_text, truthy, none_if_null

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

FIELDS = ["ticket_id", "subject", "description", "followups", "resolution", "internal_notes",
          "status", "source", "region", "created", "last_update", "requester_id", "company_id",
          "tags", "agent_reply_count", "source_file"]


def s(v):
    v = none_if_null(v)
    return "" if v is None else str(v).strip()


def split_conversations(convs):
    """convs: iterable of dicts with body, incoming, private, created."""
    agent, cust, notes = [], [], []
    for c in sorted(convs, key=lambda c: s(c.get("created"))):
        text = clean_text(c.get("body"), cut_quoted=True)
        if len(text) < 8:
            continue
        if truthy(c.get("private")):
            notes.append(text)
        elif truthy(c.get("incoming")):
            cust.append(text)
        else:
            agent.append(text)
    return agent, cust, notes


def record(tid, subject, desc, status, source, region, created, updated, req, comp, tags, convs, src, extra_resolution=""):
    agent, cust, notes = split_conversations(convs)
    resolution = "\n---\n".join(agent + ([clean_text(extra_resolution, True)] if extra_resolution else []))
    return {
        "ticket_id": tid,
        "subject": clean_text(subject),
        "description": clean_text(desc, cut_quoted=True)[:4000],
        "followups": "\n---\n".join(cust)[:3000],
        "resolution": resolution[:6000],
        "internal_notes": "\n---\n".join(notes)[:2000],
        "status": status, "source": source, "region": region,
        "created": created, "last_update": updated,
        "requester_id": req, "company_id": comp, "tags": tags,
        "agent_reply_count": len(agent), "source_file": src,
    }


def load_freshdesk_json(raw_dir, cfg, include_unresolved):
    resolved = {str(v) for v in cfg.get("resolved_status_values", [])}
    excl_src = {str(v) for v in cfg.get("exclude_sources", [])}
    stats = defaultdict(int)
    for p in sorted(raw_dir.glob(cfg["file_glob"])):
        stats["files"] += 1
        try:
            d = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as e:  # corrupt file: report, keep going
            print(f"WARN unreadable {p}: {e}", file=sys.stderr)
            stats["unreadable"] += 1
            continue
        if s(d.get("status")) and s(d.get("status")) != "success":
            stats["export_failed"] += 1
            continue
        o = d.get("original") or {}
        tid = s(o.get("id") or d.get("ticket_id"))
        if not tid:
            continue
        status, source = s(o.get("status")), s(o.get("source"))
        if source in excl_src:
            stats["skipped_outbound"] += 1
            continue
        if not include_unresolved and status not in resolved:
            stats["skipped_unresolved"] += 1
            continue
        convs = [{"body": c.get("body_text") or c.get("body"), "incoming": c.get("incoming"),
                  "private": c.get("private"), "created": c.get("created_at")} for c in d.get("conversations") or []]
        tags = o.get("tags") or []
        yield record(tid, o.get("subject"), o.get("description_text") or o.get("description"), status, source,
                     s(o.get("type")), s(o.get("created_at")), s(o.get("updated_at")), s(o.get("requester_id")),
                     s(o.get("company_id")), ",".join(map(str, tags)) if isinstance(tags, list) else s(tags),
                     convs, str(p.relative_to(raw_dir)))
    print(json.dumps({"json_" + k: v for k, v in stats.items()}), file=sys.stderr)


def load_csv(raw_dir, cfg, include_unresolved):
    tcfg, ccfg = cfg["tickets"], cfg.get("conversations") or {}
    tc = tcfg["columns"]
    resolved = {v.lower() for v in tcfg.get("resolved_status_values", [])}
    convs = defaultdict(list)
    if ccfg.get("file_glob"):
        cc = ccfg["columns"]
        for p in sorted(raw_dir.glob(ccfg["file_glob"])):
            with open(p, newline="", encoding="utf-8-sig", errors="replace") as f:
                for row in csv.DictReader(f):
                    tid = s(row.get(cc["ticket_id"]))
                    if tid:
                        convs[tid].append({k: row.get(cc[k]) if cc.get(k) else None for k in ("body", "incoming", "private", "created")})
    g = lambda row, k: s(row.get(tc[k])) if tc.get(k) else ""
    for p in sorted(raw_dir.glob(tcfg["file_glob"])):
        with open(p, newline="", encoding="utf-8-sig", errors="replace") as f:
            for row in csv.DictReader(f):
                tid = g(row, "id")
                if not tid or (not include_unresolved and g(row, "status").lower() not in resolved):
                    continue
                yield record(tid, g(row, "subject"), g(row, "description"), g(row, "status"), g(row, "source"),
                             g(row, "type"), g(row, "created"), g(row, "resolved"), g(row, "requester_id"),
                             g(row, "company_id"), g(row, "tags"), convs.get(tid, []), p.name, g(row, "resolution"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--db", type=Path, default=INDEX_DB)
    ap.add_argument("--include-unresolved", action="store_true")
    args = ap.parse_args()

    cmap = load_column_map()
    fmt = cmap.get("format", "freshdesk_json")
    loader = load_freshdesk_json if fmt == "freshdesk_json" else load_csv
    tickets = {}
    for t in loader(args.raw_dir, cmap[fmt], args.include_unresolved):
        tickets[t["ticket_id"]] = t  # later files win (re-exports)

    if not tickets:
        sys.exit(f"No tickets indexed from {args.raw_dir}. Check config/column_map.json (format, file_glob).")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.db.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.execute(f"CREATE TABLE tickets ({', '.join(c + (' PRIMARY KEY' if c == 'ticket_id' else '') for c in FIELDS)})")
    con.executemany(f"INSERT INTO tickets VALUES ({','.join('?' * len(FIELDS))})",
                    [tuple(t[c] for c in FIELDS) for t in tickets.values()])
    con.execute("CREATE VIRTUAL TABLE tickets_fts USING fts5(ticket_id UNINDEXED, subject, description, followups,"
                " resolution, tags, tokenize='porter unicode61 remove_diacritics 2')")
    con.execute("INSERT INTO tickets_fts SELECT ticket_id, subject, description, followups, resolution, tags FROM tickets")
    stats = {
        "format": fmt,
        "indexed_tickets": len(tickets),
        "with_agent_reply": sum(1 for t in tickets.values() if t["agent_reply_count"]),
        "distinct_requesters": len({t["requester_id"] for t in tickets.values() if t["requester_id"]}),
    }
    con.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO meta VALUES ('stats', ?)", (json.dumps(stats),))
    con.commit()
    con.close()
    tmp.replace(args.db)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
