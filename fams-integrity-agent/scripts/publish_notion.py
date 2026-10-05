#!/usr/bin/env python3
"""
Publish the daily integrity results to the clients' Notion portal.

For every account of a client and every operational day in the run's window,
this upserts ONE page in that site's "Data Integrity Reports" database:

  ShipTech:  FAMS Client Portal > Shiptech (pty) ltd Portal > Sites > <site> > Data Integrity Reports
  RAM / PMC: FAMS Client Portal > FAMS Clients > Sites > <site> > Data Integrity Reports

Page = Name "DD Mon YYYY", Date, Status (Clean / Issues Found), Usage %,
Transfer %, Receiving %, ATG %, and a body in the same layout the previous
nightly job used (KPI table, 7-day trend, findings, totaliser breaks, tanks,
per-finding detail, PDF link). A run covers 48 h = two days, so each day is
written by two consecutive runs; the later run simply replaces the page
content (upsert by Date), it never creates a duplicate.

Everything comes from run_checks.py output (findings.json + evidence CSVs) -
no database access, no recomputing. The client PDF is uploaded once to Azure
Blob (secret FAMS_BLOB_CONNECTION_STRING) and linked from every site page with
a read-only SAS URL.

Safety: writes only into the data sources listed in config.json -> notion.sites;
never deletes or moves a page; on update it only replaces that page's own
child blocks. The Notion token is read from notion.token_file (or NOTION_TOKEN)
and never printed.

Usage:
  python publish_notion.py --run-dir $H/runs/2026-10-06 --pdf ShipTech=/path/FAMS-Integrity-ShipTech-2026-10-06.pdf
  python publish_notion.py --run-dir ... --client ShipTech --dry-run     # writes the page JSON, no network
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(os.path.dirname(HERE), "config", "config.json")
EVIDENCE_COLS = ["Macaddress", "ID", "UsageDispensingID", "TransactionID", "TrId", "Device", "DeviceID",
                 "StoreID", "EquipmentID", "TankID", "Volume", "MissingVolume_L", "Delta_L", "Logged_L", "ATG_L",
                 "PctDiff", "Unexplained_L", "Unit", "GapMinutes", "LastSeen", "SourceTable", "Role", "CreateDate"]
TIME_COLS = ("CreateDate", "NextCreateDate", "GapStart", "GapEnd", "LastSeen", "Opening_Time")


# ----------------------------------------------------------------------------
# formatting + block builders
# ----------------------------------------------------------------------------
def fnum(v, dp=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n/a"
    try:
        return f"{float(v):,.{dp}f}"
    except (TypeError, ValueError):
        return str(v)


def fpct(v):
    return "n/a" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{float(v):.1f}%"


def cell(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v)


def rt(text, bold=False, link=None, color=None):
    text = "" if text is None else str(text)
    parts = [text[i:i + 1900] for i in range(0, len(text), 1900)] or [""]
    out = []
    for p in parts:
        o = {"type": "text", "text": {"content": p}}
        if link:
            o["text"]["link"] = {"url": link}
        ann = {}
        if bold:
            ann["bold"] = True
        if color:
            ann["color"] = color
        if ann:
            o["annotations"] = ann
        out.append(o)
    return out


def para(text, **kw):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt(text, **kw)}}


def heading(text, level=2):
    k = f"heading_{level}"
    return {"object": "block", "type": k, k: {"rich_text": rt(text)}}


def callout(text, emoji="📋", color="gray_background"):
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": rt(text), "icon": {"type": "emoji", "emoji": emoji}, "color": color}}


def divider():
    return {"object": "block", "type": "divider", "divider": {}}


def table(headers, rows, max_rows):
    shown = rows[:max_rows]
    children = [{"object": "block", "type": "table_row", "table_row": {"cells": [rt(h, bold=True) for h in headers]}}]
    for r in shown:
        children.append({"object": "block", "type": "table_row",
                         "table_row": {"cells": [rt(cell(c)) for c in r]}})
    blocks = [{"object": "block", "type": "table",
               "table": {"table_width": len(headers), "has_column_header": True, "has_row_header": False,
                         "children": children}}]
    if len(rows) > max_rows:
        blocks.append(para(f"{len(rows) - max_rows} more row(s) in the PDF / technical workbook.", color="gray"))
    return blocks


def day_label(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y")


def rows_in_day(ev, day):
    s, e = pd.Timestamp(day["start"]), pd.Timestamp(day["end"])
    for c in TIME_COLS:
        if c in ev.columns:
            t = pd.to_datetime(ev[c], errors="coerce")
            return ev[(t >= s) & (t < e)]
    return ev


# ----------------------------------------------------------------------------
# page content
# ----------------------------------------------------------------------------
def page_properties(day, status):
    def n(v):
        return None if v is None else float(v)
    return {
        "Name": {"title": rt(day_label(day["date"]))},
        "Date": {"date": {"start": day["date"]}},
        "Status": {"select": {"name": status}},
        "Usage %": {"number": n(day["usage_pct"])},
        "Transfer %": {"number": n(day["transfer_pct"])},
        "Receiving %": {"number": n(day["receiving_pct"])},
        "ATG %": {"number": n(day["atg_pct"])},
    }


def build_blocks(doc, run_dir, acc, site, day, trend_rows, pdf_url, max_rows):
    w = doc["window"]
    fids = set(day["finding_ids"])
    fs = [f for f in doc["findings"] if f["finding_id"] in fids]
    inv = [f for f in fs if f["status"] == "Investigate"]
    mon = [f for f in fs if f["status"] == "Monitor"]
    ok = [f for f in fs if f["status"] == "No action required"]
    boundary = w["boundary"]
    b = []
    b.append(callout(
        f"FAMS Data Integrity Check - {site} - {day_label(day['date'])} "
        f"({day['date']} {boundary[:5]} to the next day {boundary[:5]} SAST). Produced by the FAMS Data Integrity "
        f"Agent as part of the 48-hour check {w['start_sast']} to {w['end_sast']} "
        f"(generated {doc['generated_at_sast']} SAST). Findings are unconfirmed until verified in the field; "
        "'possible cause' wording is deliberate. No financial values are reported.", "⛽"))
    b += table(["Dispensed (L)", "Reconciliation %", "Investigate Items", "Transfer Volume (L)",
                "Receiving Volume (L)", "Possible Fuel Loss", "Comm. Failures", "Monitor Items"],
               [[fnum(day["dispensed_L"]), fpct(day["usage_pct"]), day["investigate"],
                 f"{fnum(day['transfer_L'])} ({day['transfer_txn']} txn)",
                 f"{fnum(day['receiving_L'])} ({day['receiving_txn']} txn)",
                 day["possible_fuel_loss"], day["comm_failures"], day["monitor"]]], max_rows)
    if trend_rows:
        b.append(heading("Last 7 days", 3))
        b += table(["Date", "Usage %", "Transfer %", "Receiving %", "ATG %"], trend_rows, max_rows)

    b.append(heading("Items for management (Investigate)", 2))
    if inv:
        b += table(["Category", "Affected (48 h)", "Rows this day", "Note"],
                   [[f["category"], f["affected"], f.get("day_rows", {}).get(day["date"], "-"), f["note"]] for f in inv],
                   max_rows)
    else:
        b.append(para("No Investigate items for this site on this day."))

    breaks = []
    for f in inv:
        if f["check"] == "C12" and f.get("evidence_file"):
            ev = rows_in_day(pd.read_csv(os.path.join(run_dir, f["evidence_file"])), day)
            ev = ev.sort_values("MissingVolume_L", ascending=False, na_position="last")
            for r in ev.to_dict("records"):
                breaks.append([cell(r.get("Macaddress")), cell(r.get("ID")), cell(r.get("TransactionID")),
                               fnum(r.get("Volume")),
                               fnum(r.get("MissingVolume_L")) if pd.notna(r.get("MissingVolume_L")) else "backwards",
                               cell(r.get("CreateDate"))[:19]])
    if breaks:
        b.append(heading("Totaliser flow breaks", 3))
        b += table(["Macaddress", "ID", "TransactionID", "Volume (L)", "Missing volume (L)", "Time"], breaks, max_rows)

    b.append(heading("Monitoring items", 2))
    if mon:
        b += table(["Category", "Affected (48 h)", "Note"], [[f["category"], f["affected"], f["note"]] for f in mon],
                   max_rows)
        b.append(para("Monitor items are data-confidence or pattern warnings - no action is required unless the "
                      "same site is also flagged under Investigate.", color="gray"))
    else:
        b.append(para("No Monitor items for this site on this day."))

    if day["tanks"]:
        b.append(heading("Tanks", 3))
        b += table(["Tank", "Opening (L)", "Closing (L)", "Capacity (L, est.)", "Closing %", "Deliveries"],
                   [[t.get("TankID"), fnum(t.get("Opening_L")), fnum(t.get("Closing_L")), fnum(t.get("Capacity_L_est")),
                     fpct(t.get("ClosingPctFull")), f"{t.get('Deliveries', 0)} ({fnum(t.get('Delivered_L_est'))} L)"]
                    for t in day["tanks"]], max_rows)
    b.append(para(f"Reconciliation - Usage: {fpct(day['usage_pct'])}  Transfer: {fpct(day['transfer_pct'])}  "
                  f"Receiving: {fpct(day['receiving_pct'])}  ATG: {fpct(day['atg_pct'])}", bold=True))

    for f in inv:
        b.append(heading(f"⚠️ {f['category']}", 3))
        b.append(para(f["note"]))
        if f.get("evidence_file"):
            ev = rows_in_day(pd.read_csv(os.path.join(run_dir, f["evidence_file"])), day)
            cols = [c for c in EVIDENCE_COLS if c in ev.columns][:7]
            if len(ev) and cols:
                b += table(cols, [[cell(r[c])[:60] for c in cols] for r in ev[cols].to_dict("records")], min(15, max_rows))
    if ok:
        b.append(heading("No action required", 3))
        for f in ok:
            b.append(para(f"{f['category']}: {f['note']}"))

    gaps = doc.get("data_gaps") or []
    b.append(heading("Data quality", 3))
    b.append(para("All data sources were available and every check ran." if not gaps else
                  "Unverifiable with current data: " + "; ".join(f"{g['scope']} - {g['gap']}" for g in gaps)))
    if pdf_url:
        b.append(para("📄 Download full report (PDF)", link=pdf_url))
    else:
        b.append(para("Full report (PDF): not attached to this page this run - available from FAMS on request.",
                      color="gray"))
    return b


def trend_from_pages(pages):
    rows = []
    for p in pages:
        pr = p.get("properties", {})
        d = (pr.get("Date", {}).get("date") or {}).get("start")
        if not d:
            continue

        def num(k):
            v = pr.get(k, {}).get("number")
            return fpct(v)
        rows.append([datetime.strptime(d[:10], "%Y-%m-%d").strftime("%d %b"), num("Usage %"), num("Transfer %"),
                     num("Receiving %"), num("ATG %")])
    return list(reversed(rows))


# ----------------------------------------------------------------------------
# Notion REST client (only the calls this script needs)
# ----------------------------------------------------------------------------
class NotionClient:
    BASE = "https://api.notion.com/v1"

    def __init__(self, token, version, allowed_sources):
        self._token = token
        self.version = version
        self.allowed = set(allowed_sources)
        self._last = 0.0

    def _call(self, method, path, body=None):
        for attempt in range(6):
            wait = 0.35 - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(self.BASE + path, method=method,
                                         data=None if body is None else json.dumps(body).encode(),
                                         headers={"Authorization": f"Bearer {self._token}",
                                                  "Notion-Version": self.version,
                                                  "Content-Type": "application/json"})
            try:
                self._last = time.time()
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                    continue
                detail = e.read().decode(errors="replace")[:400]
                raise RuntimeError(f"Notion {method} {path.split('?')[0]} -> HTTP {e.code}: {detail}") from None
        raise RuntimeError("Notion API: retries exhausted")

    def _check(self, ds):
        if ds not in self.allowed:
            raise PermissionError(f"data source {ds} is not in config notion.sites - refusing to write")

    def pages_on(self, ds, date):
        r = self._call("POST", f"/data_sources/{ds}/query",
                       {"filter": {"property": "Date", "date": {"equals": date}},
                        "sorts": [{"timestamp": "created_time", "direction": "ascending"}]})
        return r.get("results", [])

    def recent_before(self, ds, date, n):
        r = self._call("POST", f"/data_sources/{ds}/query",
                       {"filter": {"property": "Date", "date": {"before": date}},
                        "sorts": [{"property": "Date", "direction": "descending"}], "page_size": n})
        return r.get("results", [])

    def create(self, ds, props, blocks):
        self._check(ds)
        first, rest = chunk(blocks)[0], chunk(blocks)[1:]
        page = self._call("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": ds},
                                             "properties": props, "children": first})
        for c in rest:
            self._call("PATCH", f"/blocks/{page['id']}/children", {"children": c})
        return page

    def replace(self, ds, page, props, blocks):
        self._check(ds)
        pid = page["id"]
        self._call("PATCH", f"/pages/{pid}", {"properties": props})
        cursor, old = None, []
        while True:
            q = f"/blocks/{pid}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            r = self._call("GET", q)
            old += [x["id"] for x in r.get("results", [])]
            if not r.get("has_more"):
                break
            cursor = r.get("next_cursor")
        for bid in old:                      # only this page's own content blocks
            self._call("DELETE", f"/blocks/{bid}")
        for c in chunk(blocks):
            self._call("PATCH", f"/blocks/{pid}/children", {"children": c})
        return page


def chunk(blocks, max_elems=800, max_top=90):
    """Split into append requests under Notion's 1000-element / 100-children limits."""
    out, cur, n = [], [], 0
    for b in blocks:
        size = 1 + len(b.get("table", {}).get("children", []))
        if cur and (n + size > max_elems or len(cur) >= max_top):
            out.append(cur)
            cur, n = [], 0
        cur.append(b)
        n += size
    if cur:
        out.append(cur)
    return out or [[]]


# ----------------------------------------------------------------------------
# PDF upload
# ----------------------------------------------------------------------------
def upload_pdf(cfg, client_short, report_date, path, warnings):
    pu = cfg.get("pdf_upload", {})
    conn = os.environ.get(pu.get("env", "FAMS_BLOB_CONNECTION_STRING"))
    if not path or not os.path.exists(path):
        warnings.append(f"{client_short}: no PDF supplied - pages published without a PDF link")
        return None
    if not conn:
        warnings.append(f"{client_short}: {pu.get('env')} not set - pages published without a PDF link")
        return None
    try:
        from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas
        svc = BlobServiceClient.from_connection_string(conn)
        name = f"{pu.get('prefix', 'paperclip')}/{client_short}/FAMS-Integrity-{client_short}-{report_date}.pdf"
        blob = svc.get_blob_client(pu.get("container", "reconciliation-reports"), name)
        with open(path, "rb") as fh:
            blob.upload_blob(fh, overwrite=True, content_settings=ContentSettings(content_type="application/pdf"))
        sas = generate_blob_sas(account_name=svc.account_name, container_name=blob.container_name, blob_name=name,
                                account_key=svc.credential.account_key, permission=BlobSasPermissions(read=True),
                                expiry=datetime.now(timezone.utc) + timedelta(days=int(pu.get("link_days", 365))))
        return f"{blob.url}?{sas}"
    except Exception as e:  # never leak the connection string
        msg = str(e).replace(conn, "***")[:200]
        warnings.append(f"{client_short}: PDF upload failed ({type(e).__name__}: {msg}) - pages published without a PDF link")
        return None


# ----------------------------------------------------------------------------
def read_token(cfg):
    tok = os.environ.get("NOTION_TOKEN")
    if tok:
        return tok.strip()
    path = cfg.get("notion", {}).get("token_file", "/paperclip/notion-mcp/token")
    with open(path) as fh:
        return fh.read().strip()


def publish_client(cfg, run_dir, client_short, pdf_path, notion, dry_run=False, only=None):
    cdir = os.path.join(run_dir, client_short)
    with open(os.path.join(cdir, "findings.json")) as fh:
        doc = json.load(fh)
    ncfg = cfg["notion"]
    max_rows = int(ncfg.get("max_table_rows", 40))
    warnings, log = [], []
    pdf_url = None if dry_run else upload_pdf(cfg, client_short, doc["window"]["report_date"], pdf_path, warnings)
    names = {str(a["AccountID"]): a["Account"] for a in doc["accounts"]}
    for acc, days in doc.get("days", {}).items():
        if only and acc not in only:
            continue
        site = ncfg["sites"].get(acc)
        if not site:
            warnings.append(f"Account {acc} ({names.get(acc)}) has no Notion site in config - skipped")
            continue
        ds = site["data_source_id"]
        for day in sorted(days, key=lambda x: x["date"]):
            status = "Clean" if day["investigate"] + day["monitor"] == 0 else "Issues Found"
            props = page_properties(day, status)
            entry = {"account": int(acc), "site": site["site"], "date": day["date"], "status": status}
            try:
                trend = [] if dry_run else trend_from_pages(
                    notion.recent_before(ds, day["date"], int(ncfg.get("trend_days", 7))))
                blocks = build_blocks(doc, cdir, int(acc), site["site"], day, trend, pdf_url, max_rows)
                if dry_run:
                    pdir = os.path.join(cdir, "notion_preview")
                    os.makedirs(pdir, exist_ok=True)
                    fn = os.path.join(pdir, f"{acc}_{day['date']}.json")
                    with open(fn, "w") as fh:
                        json.dump({"data_source_id": ds, "properties": props, "children": blocks}, fh, indent=1)
                    entry.update(action="dry-run", file=fn, blocks=len(blocks))
                else:
                    existing = notion.pages_on(ds, day["date"])
                    if existing:
                        page = notion.replace(ds, existing[0], props, blocks)
                        entry["action"] = "updated"
                        if len(existing) > 1:
                            warnings.append(f"{site['site']} {day['date']}: {len(existing)} pages share this date - "
                                            "updated the oldest, left the others untouched (review and archive by hand)")
                    else:
                        page = notion.create(ds, props, blocks)
                        entry["action"] = "created"
                    entry["url"] = page.get("url")
            except Exception as e:
                entry.update(action="failed", error=f"{type(e).__name__}: {str(e)[:300]}")
            log.append(entry)
    out = {"client": client_short, "window": doc["window"], "pdf_url_set": bool(pdf_url),
           "pages": log, "warnings": warnings}
    with open(os.path.join(cdir, "publish_log.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="the --out directory of run_checks.py")
    ap.add_argument("--client", action="append", help="client short name (repeatable); default: all in run-dir")
    ap.add_argument("--pdf", action="append", default=[], help="Client=path/to/report.pdf (repeatable)")
    ap.add_argument("--account", action="append", help="limit to these AccountIDs (testing)")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--dry-run", action="store_true", help="write page JSON to <client>/notion_preview, no network")
    args = ap.parse_args()
    with open(args.config) as fh:
        cfg = json.load(fh)
    pdfs = dict(p.split("=", 1) for p in args.pdf)
    clients = args.client or sorted(d for d in os.listdir(args.run_dir)
                                    if os.path.exists(os.path.join(args.run_dir, d, "findings.json")))
    notion = None
    if not args.dry_run:
        notion = NotionClient(read_token(cfg), cfg["notion"].get("api_version", "2025-09-03"),
                              [s["data_source_id"] for s in cfg["notion"]["sites"].values()])
    summary = []
    for c in clients:
        r = publish_client(cfg, args.run_dir, c, pdfs.get(c), notion, args.dry_run, set(args.account or []))
        acts = pd.Series([p["action"] for p in r["pages"]]).value_counts().to_dict() if r["pages"] else {}
        summary.append({"client": c, "pages": acts, "pdf_link": r["pdf_url_set"], "warnings": r["warnings"]})
    print(json.dumps(summary, indent=2))
    if any(p["action"] == "failed" for c in clients
           for p in json.load(open(os.path.join(args.run_dir, c, "publish_log.json")))["pages"]):
        sys.exit(2)


if __name__ == "__main__":
    main()
