#!/usr/bin/env python3
"""
Email each client's integrity PDF to the four FAMS recipients.

One POST per recipient per client (the endpoint takes a single address), so a
normal run is 3 clients x 4 recipients = 12 sends. Recipients, endpoint and
subject come from config.json -> email. The one-line body is built from that
client's findings.json (no recomputing).

Safe to re-run: every send is recorded in <run-dir>/email_log.json and a
(client, recipient) pair that already succeeded is never sent again unless
--resend is given. A failed send is retried once automatically; anything still
failing is reported and the script exits 2.

Usage:
  python send_reports.py --run-dir $H/runs/2026-10-06 \
      --pdf ShipTech=<pdf> --pdf RAM-Couriers=<pdf> --pdf PMC-Phalaborwa=<pdf>
  python send_reports.py --run-dir ... --to hennie@fams.co.za     # test: one recipient only
  python send_reports.py --run-dir ... --dry-run                  # show what would be sent
Without --pdf, the PDF is looked up as <run-dir>/<Client>/*.pdf or
<run-dir>/reports/*<Client>*.pdf (exactly one match required).
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(os.path.dirname(HERE), "config", "config.json")


def find_pdf(run_dir: str, client: str, date: str) -> str:
    cands = glob.glob(os.path.join(run_dir, client, "*.pdf")) or \
        glob.glob(os.path.join(run_dir, "reports", f"*{client}*.pdf"))
    dated = [c for c in cands if date in os.path.basename(c)]
    cands = dated or cands
    if len(cands) != 1:
        raise FileNotFoundError(f"{client}: expected exactly one PDF, found {len(cands)}; pass --pdf {client}=<path>")
    return cands[0]


def summary_line(doc: dict) -> str:
    k = doc.get("kpis", {})
    n_acc = len(doc.get("accounts", []))
    w = doc.get("window", {})
    gaps = len(doc.get("data_gaps", []))
    line = (f"{doc.get('client', doc.get('client_short'))}: {k.get('investigate', 0)} Investigate, "
            f"{k.get('monitor', 0)} Monitor across {n_acc} account(s), "
            f"window {w.get('start_sast', '?')} to {w.get('end_sast', '?')}.")
    if gaps:
        line += f" {gaps} data gap(s) - some checks unverifiable."
    return line + " Full detail in the attached PDF."


def html_body(doc: dict) -> str:
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<p>{esc(summary_line(doc))}</p><p>FAMS Data Integrity Agent</p>"


def post(endpoint: str, payload: dict, timeout: int) -> tuple[int | None, str]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(endpoint, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(300).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(300).decode("utf-8", "replace")
    except Exception as e:  # network / timeout
        return None, f"{type(e).__name__}: {e}"


def load_log(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return {"sends": []}


def already_sent(log: dict, client: str, to: str, pdf: str) -> bool:
    return any(s["client"] == client and s["to"] == to and s["ok"] and s["pdf"] == os.path.basename(pdf)
               for s in log["sends"])


def run(args, poster=post) -> int:
    with open(args.config) as fh:
        cfg = json.load(fh)
    ec = cfg["email"]
    recipients = args.to or ec["recipients"]
    pdfs = dict(p.split("=", 1) for p in args.pdf)
    clients = args.client or sorted(d for d in os.listdir(args.run_dir)
                                    if os.path.exists(os.path.join(args.run_dir, d, "findings.json")))
    if not clients:
        print(f"No findings.json under {args.run_dir}", file=sys.stderr)
        return 2
    log_path = os.path.join(args.run_dir, "email_log.json")
    log = load_log(log_path)
    results, failed = [], 0
    for c in clients:
        with open(os.path.join(args.run_dir, c, "findings.json")) as fh:
            doc = json.load(fh)
        date = doc["window"]["report_date"]
        try:
            pdf = pdfs.get(c) or find_pdf(args.run_dir, c, date)
        except FileNotFoundError as e:
            results.append({"client": c, "to": "*", "status": "no PDF", "detail": str(e)})
            failed += 1
            continue
        subject = ec["subject"].format(client=doc.get("client", c), date=date)
        with open(pdf, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        for to in recipients:
            if not args.resend and already_sent(log, c, to, pdf):
                results.append({"client": c, "to": to, "status": "already sent"})
                continue
            if args.dry_run:
                results.append({"client": c, "to": to, "status": "dry-run", "subject": subject,
                                "pdf": os.path.basename(pdf), "body": summary_line(doc)})
                continue
            payload = {"email": to, "subject": subject, "body": html_body(doc),
                       "fileName": os.path.basename(pdf), "fileContentBase64": b64}
            for attempt in (1, 2):
                code, text = poster(ec["endpoint"], payload, int(ec.get("timeout_seconds", 60)))
                ok = code is not None and 200 <= code < 300
                if ok or attempt == 2:
                    break
                time.sleep(5)
            entry = {"client": c, "to": to, "pdf": os.path.basename(pdf), "subject": subject,
                     "http": code, "ok": ok, "attempts": attempt, "detail": text[:200],
                     "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            log["sends"].append(entry)
            with open(log_path, "w") as fh:
                json.dump(log, fh, indent=2)
            results.append({"client": c, "to": to, "status": f"HTTP {code}" if code else "error",
                            "ok": ok, **({} if ok else {"detail": text[:200]})})
            failed += 0 if ok else 1
    sent = sum(1 for r in results if r.get("ok"))
    print(json.dumps({"sent": sent, "failed": failed,
                      "skipped_already_sent": sum(r["status"] == "already sent" for r in results),
                      "results": results}, indent=2))
    return 2 if failed else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--client", action="append", help="client short name (repeatable); default: all in run-dir")
    ap.add_argument("--pdf", action="append", default=[], help="Client=path/to/report.pdf (repeatable)")
    ap.add_argument("--to", action="append", help="override recipients (testing)")
    ap.add_argument("--resend", action="store_true", help="send again even if already sent")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    sys.exit(run(ap.parse_args()))


if __name__ == "__main__":
    main()
