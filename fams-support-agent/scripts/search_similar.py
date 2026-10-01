#!/usr/bin/env python3
"""Find historical tickets similar to a new one and summarise how consistent their fixes were.

Input (pick one):
  --ticket-json FILE   JSON with at least "subject" and "description" (e.g. saved get_ticket output)
  --subject S --description D
Options:
  --exclude-id ID      ignore this ticket id (the new ticket itself, if already in history)
  --requester-id / --company-id   the new ticket's customer (taken from --ticket-json if given);
                       matches from the same customer don't count as "other users"
  --top N              candidates to return (default 8)

Output: JSON on stdout with ranked candidates, a normalised relevance per candidate,
and "consensus" clusters of candidates whose resolutions resemble each other.
The agent (not this script) makes the final judgement.
"""
import argparse
import json
import re
import sqlite3
import sys

from common import INDEX_DB, keywords, clean_text, none_if_null


def fts_query(terms):
    safe = [re.sub(r'[^a-z0-9_]', '', t) for t in terms]
    return " OR ".join(f'"{t}"' for t in safe if t)


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def tokset(text):
    return {stem(w) for w in keywords(text, limit=200)}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def customer_key(requester_id, company_id):
    """Same company = same customer, even if a different person logged it."""
    return f"c:{company_id}" if company_id else (f"r:{requester_id}" if requester_id else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket-json", help="saved get_ticket output for the new ticket")
    ap.add_argument("--subject", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--exclude-id", default="")
    ap.add_argument("--requester-id", default="", help="new ticket's requester_id (read from --ticket-json if given)")
    ap.add_argument("--company-id", default="", help="new ticket's company_id (read from --ticket-json if given)")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--db", default=str(INDEX_DB))
    args = ap.parse_args()

    subject, description = args.subject, args.description
    if args.ticket_json:
        with open(args.ticket_json, encoding="utf-8") as f:
            t = json.load(f)
        t = t.get("original", t)  # accept the export shape too
        subject = t.get("subject") or subject
        description = t.get("description_text") or t.get("description") or description
        args.exclude_id = args.exclude_id or str(t.get("id", ""))
        args.requester_id = args.requester_id or str(none_if_null(t.get("requester_id")) or "")
        args.company_id = args.company_id or str(none_if_null(t.get("company_id")) or "")
    subject, description = clean_text(subject), clean_text(description, cut_quoted=True)
    if not (subject or description):
        sys.exit("Need a subject and/or description")
    new_customer = customer_key(args.requester_id, args.company_id)

    # Description first: in this helpdesk the subject is often just the customer's company name.
    d_terms = keywords(description, 30)
    terms = d_terms + [w for w in keywords(subject, 10) if w not in d_terms]
    q = fts_query(terms[:35])
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    # bm25 column weights: ticket_id, subject, description, followups, resolution, tags
    rows = con.execute(
        """SELECT t.*, bm25(tickets_fts, 0, 1.5, 4.0, 1.5, 1.0, 1.0) AS score
           FROM tickets_fts JOIN tickets t ON t.ticket_id = tickets_fts.ticket_id
           WHERE tickets_fts MATCH ? AND t.ticket_id != ?
           ORDER BY score LIMIT ?""",
        (q, str(args.exclude_id), max(args.top * 3, 20)),
    ).fetchall()

    query_set = {stem(t) for t in terms}
    cands = []
    for r in rows:
        problem_set = tokset(f"{r['subject']} {r['description']} {r['followups']}")
        overlap = len(query_set & problem_set) / max(1, len(query_set))
        ck = customer_key(r["requester_id"], r["company_id"])
        cands.append({
            "ticket_id": r["ticket_id"],
            "subject": r["subject"],
            "description": r["description"][:600],
            "customer_followups": r["followups"][:400],
            "agent_replies": r["resolution"][:1500],
            "internal_notes": r["internal_notes"][:300],
            "has_agent_reply": bool(r["resolution"]),
            "customer_key": ck,
            "same_customer_as_new": bool(new_customer) and ck == new_customer,
            "region": r["region"],
            "created": r["created"],
            "bm25": round(r["score"], 3),
            "term_overlap": round(overlap, 2),
        })
    cands.sort(key=lambda c: (-c["term_overlap"], c["bm25"]))
    cands = cands[: args.top]

    # cluster candidates whose agent replies look alike (greedy, Jaccard >= 0.2)
    sets = {c["ticket_id"]: tokset(c["agent_replies"]) for c in cands if c["has_agent_reply"]}
    clusters, assigned = [], set()
    for c in cands:
        tid = c["ticket_id"]
        if tid not in sets or tid in assigned:
            continue
        group = [tid]
        assigned.add(tid)
        for d in cands:
            o = d["ticket_id"]
            if o in sets and o not in assigned and jaccard(sets[tid], sets[o]) >= 0.2:
                group.append(o)
                assigned.add(o)
        members = [x for x in cands if x["ticket_id"] in group]
        others = {m["customer_key"] for m in members if m["customer_key"] and not m["same_customer_as_new"]}
        clusters.append({
            "ticket_ids": group,
            "size": len(group),
            "distinct_other_customers": len(others),
            "mean_term_overlap": round(sum(m["term_overlap"] for m in members) / len(members), 2),
        })
    clusters.sort(key=lambda g: (-g["distinct_other_customers"], -g["size"], -g["mean_term_overlap"]))

    print(json.dumps({
        "new_ticket_customer_key": new_customer,
        "query_terms": terms[:35],
        "candidates": cands,
        "resolution_clusters": clusters,
        "hint": "Shortlist only. Strong signal = a cluster with >=2 distinct_other_customers, "
                "mean_term_overlap >= 0.3, and agent replies that state the same concrete fix. "
                "Read every description and reply before deciding.",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
