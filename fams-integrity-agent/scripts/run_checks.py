#!/usr/bin/env python3
"""
FAMS daily integrity check - deterministic engine.

Computes each client's window, pulls the data (read-only), runs every check
in integrity_checks.py and writes, per client:

  <out>/<Client>/findings.json          everything the PDF + workbook need
                                        (window, KPIs, portfolio rows, grouped
                                        findings, data gaps, checks run)
  <out>/<Client>/evidence/*.csv         full evidence behind every finding
  <out>/<Client>/dispensing_detail.csv  every window dispensing row + classification
  <out>/<Client>/tank_reconciliation.csv / store_reconciliation.csv
  <out>/<Client>/data_gaps.csv

The agent builds the report FROM findings.json - it must not recompute
numbers or re-query the database to "improve" them.

Usage:
  python run_checks.py                                  # live DB, all clients, now
  python run_checks.py --client ShipTech --run-time "2026-10-02 06:20"
  python run_checks.py --source dir --data-dir ./exports  # offline / manual mode

--run-time is SAST if no offset is given. Exit code 0 even when findings
exist; non-zero only when the run itself could not complete.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import integrity_checks as ic  # noqa: E402
from fams_sources import DbSource, DirSource  # noqa: E402

SAST = ZoneInfo("Africa/Johannesburg")
UTC = ZoneInfo("UTC")
STATUSES = ("Investigate", "Monitor", "No action required")


def compute_window(run_time_sast: pd.Timestamp, boundary_hour: int, hours: int):
    anchor = run_time_sast.normalize() + pd.Timedelta(hours=boundary_hour)
    if anchor > run_time_sast:
        anchor -= pd.Timedelta(days=1)
    return anchor - pd.Timedelta(hours=hours), anchor


def to_db(ts_sast: pd.Timestamp, db_tz: ZoneInfo) -> pd.Timestamp:
    """Aware SAST timestamp -> naive timestamp in the database's own timezone."""
    return ts_sast.tz_convert(db_tz).tz_localize(None)


def strip_common_prefix(names: dict) -> dict:
    vals = [v for v in names.values() if v]
    if len(vals) < 2:
        return names
    pre = os.path.commonprefix(vals)
    cut = max(pre.rfind(" - "), pre.rfind(" – "))
    if cut <= 0:
        return names
    return {k: (v[cut + 3:].strip() if v else v) for k, v in names.items()}


def safe(gaps, label, fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:  # a failed fetch/check is a data gap, never a silent pass
        gaps.append({"scope": label, "gap": f"FAILED - {type(e).__name__}: {str(e)[:300]}",
                     "effect": "Related checks could not run; treat as unverifiable, not clean."})
        traceback.print_exc(file=sys.stderr)
        return None


def load(src, accts, cfg, ws, we, fetch_end, lb_start, gaps):
    d = SimpleNamespace(window_start=ws, window_end=we, fetch_end=fetch_end, lookback_start=lb_start)
    margin = ws - pd.Timedelta(hours=1)
    plan = {
        "disp": ("UsageDispensing", lb_start), "iot": ("UsageDispensingIOT", lb_start),
        "android": ("UsageDispensingAndroid", lb_start), "fms": ("IOTData_FMS", margin),
        "atg": ("IOTData_ATG", margin), "notif": ("IOTData_Notification", margin),
        "err": ("IOTData_Error", ws), "stock": ("Stock", ws),
        "transfer": ("UsageTransfer", ws), "receiving": ("UsageReceiving", ws),
    }
    d.available = {}
    for attr, (table, start) in plan.items():
        df = safe(gaps, table, src.fetch, table, accts, start, fetch_end)
        setattr(d, attr, df)
        d.available[table] = None if df is None else int(len(df))
        if df is None:
            gaps.append({"scope": table, "gap": "Table not available to this run",
                         "effect": "Checks that depend on it are unverifiable with current data - not clean."})
    d.lookback_slim = {
        "Stock": safe(gaps, "Stock (lookback)", src.fetch, "Stock", accts, lb_start, ws,
                      columns=["AccountID", "StoreID", "TankID", "CreateDate"]),
        "IOTData_ATG": safe(gaps, "IOTData_ATG (lookback)", src.fetch, "IOTData_ATG", accts, lb_start, ws,
                            columns=["AccountID", "DeviceID", "CreateDate"]),
    }
    d.stores = safe(gaps, "Store", src.stores, accts)
    macs = sorted(set(d.stores["Macaddress"].dropna().astype(str))) if d.stores is not None and "Macaddress" in d.stores.columns else []
    d.tempjson = safe(gaps, "TempTableDataJson", src.temp_json_errors, macs, ws, we) if macs else None
    d.fk = safe(gaps, "Allocation/CostCentre", src.fk_checks, accts, ws, we) or {}
    if src.kind == "directory":
        gaps.append({"scope": "Allocation / EquipmentCostCentre", "gap": "Referential checks need the live database",
                     "effect": "C24 not run in directory mode."})
    return d


def run_client(src, client, cfg, run_time_sast, out_root):
    db_tz = ZoneInfo(cfg.get("db_timezone", "Africa/Johannesburg"))
    accts = [int(a) for a in client["accounts"]]
    ws_s, we_s = compute_window(run_time_sast, int(client["boundary_hour_sast"]), int(cfg["window_hours"]))
    ws, we = to_db(ws_s, db_tz), to_db(we_s, db_tz)
    fetch_end = to_db(run_time_sast, db_tz)
    lb_start = ws - pd.Timedelta(hours=int(cfg["lookback_hours"]))
    gaps = []
    print(f"[{client['short']}] window {ws_s:%Y-%m-%d %H:%M} to {we_s:%Y-%m-%d %H:%M} SAST, {len(accts)} account(s)",
          file=sys.stderr)

    d = load(src, accts, cfg, ws, we, fetch_end, lb_start, gaps)

    names = {int(k): v for k, v in client["accounts"].items()}
    missing = [a for a, v in names.items() if not v]
    if missing:
        db_names = safe(gaps, "Account", src.account_names, missing) or {}
        names.update({a: db_names.get(a) for a in missing})
        names = strip_common_prefix(names)
    names = {a: (v or f"Account {a}") for a, v in names.items()}

    findings = []
    run = []

    def do(cid, fn, *a):
        r = safe(gaps, f"check {cid}", fn, d, cfg, *a)
        run.append({"check": cid, "result": "failed" if r is None else "ran"})
        return r

    findings += do("C01/C02", ic.check_duplicates) or []
    findings += do("C03-C05", ic.check_identifiers) or []
    res = do("C06-C08", ic.classify_dispensing)
    disp_cls, recon = (res if res else (pd.DataFrame(), []))
    findings += recon
    findings += do("C09", ic.check_fms_typeids) or []
    findings += do("C10", ic.check_recnumber) or []
    findings += do("C11", ic.check_product_zero) or []
    findings += do("C12/C13", ic.check_totaliser) or []
    findings += do("C14", ic.check_btlinklost) or []
    findings += do("C15", ic.check_missing_equipment) or []
    findings += do("C16", ic.check_noflow) or []
    findings += do("C17", ic.check_telemetry_gaps, accts) or []
    tr = do("C18/C19", ic.tank_reconciliation, disp_cls)
    tank_f, tanks_df, stores_df = tr if tr else ([], pd.DataFrame(), pd.DataFrame())
    findings += tank_f
    findings += do("C20", ic.check_comm_health) or []
    findings += do("C21", ic.check_transfer_receiving_atg) or []
    findings += do("C22", ic.check_payload_errors) or []
    findings += do("C23", ic.check_outliers) or []
    findings += do("C24", ic.check_fk) or []
    findings = [f for f in findings if f["account_id"] in accts or f["account_id"] is None]

    # ---- KPIs (exact definitions from SKILL.md) ----
    def acct_kpis(acc_filter):
        dc = disp_cls[disp_cls["AccountID"].isin(acc_filter)] if len(disp_cls) else disp_cls
        fs = [f for f in findings if f["account_id"] in acc_filter]
        raw_total = float(pd.to_numeric(dc["Volume"], errors="coerce").clip(lower=0).sum()) if len(dc) else 0.0
        dup_excess = sum(f["litres"] or 0 for f in fs if f["check"] == "C01")
        total = raw_total - dup_excess
        # unexplained = no raw evidence (C06, incl. outage share) + rows with no TransactionID at all (C03)
        unexpl = sum(f["litres"] or 0 for f in fs if f["check"] in ("C06", "C03") and f["status"] != "No action required")
        outage = sum(f["litres"] or 0 for f in fs if f["check"] == "C06" and f["status"] == "Monitor")
        mism = sum(f["litres"] or 0 for f in fs if f["check"] == "C07")
        recon = (total - unexpl - mism) / total * 100 if total > 0 else None
        return {
            "anomalies_detected": sum(1 for f in fs if f["status"] in ("Investigate", "Monitor")),
            "investigate": sum(1 for f in fs if f["status"] == "Investigate"),
            "monitor": sum(1 for f in fs if f["status"] == "Monitor"),
            "total_fuel_dispensed_L": round(total, 2),
            "raw_dispensed_before_duplicate_removal_L": round(raw_total, 2),
            "duplicate_excess_L": round(dup_excess, 2),
            "reconciliation_pct": None if recon is None else round(recon, 2),
            "reconciliation_numerator_L": round(total - unexpl - mism, 2),
            "reconciliation_denominator_L": round(total, 2),
            "unexplained_L": round(unexpl, 2), "of_which_during_raw_feed_outage_L": round(outage, 2),
            "mismatch_L": round(mism, 2),
            "sites_with_possible_fuel_loss": len({f["account_id"] for f in fs if f["check"] == "C18" and f["status"] == "Investigate"}),
            "sites_with_communication_failures": len({(f["account_id"], f.get("device")) for f in fs if f["check"] == "C20"}),
            "tanks_at_risk_of_running_dry": 0,
            "run_dry_caveat": "Insufficient history for a run-dry forecast from a single 48-hour check.",
        }

    kpis = acct_kpis(accts)
    portfolio = []
    for a in accts:
        k = acct_kpis([a])
        portfolio.append({"AccountID": a, "Account": names[a], "Dispensed_L": k["total_fuel_dispensed_L"],
                          "Recon_pct": k["reconciliation_pct"] if k["reconciliation_pct"] is not None else "n/a",
                          "Anomalies": k["anomalies_detected"], "Investigate": k["investigate"],
                          "CommFail": k["sites_with_communication_failures"]})

    # ---- write outputs ----
    out_dir = os.path.join(out_root, client["short"])
    ev_dir = os.path.join(out_dir, "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    order = {s: i for i, s in enumerate(STATUSES)}
    findings.sort(key=lambda f: (order[f["status"]], f["account_id"] or 0, f["check"]))
    serial = []
    for n, f in enumerate(findings, start=1):
        ev = f.pop("evidence")
        f["finding_id"] = f"{client['short']}-{n:03d}"
        f["account"] = names.get(f["account_id"], "") if f["account_id"] else ""
        if ev is not None and len(ev):
            fn = f"{f['finding_id']}_{f['check']}.csv"
            ev.to_csv(os.path.join(ev_dir, fn), index=False)
            f["evidence_file"] = f"evidence/{fn}"
            f["evidence_rows"] = int(len(ev))
            f["evidence_sample"] = json.loads(ev.head(15).to_json(orient="records", date_format="iso"))
        else:
            f["evidence_file"], f["evidence_rows"], f["evidence_sample"] = None, 0, []
        serial.append(f)
    if len(disp_cls):
        flagged = {}
        for f in serial:
            if f["evidence_file"]:
                ev = pd.read_csv(os.path.join(out_dir, f["evidence_file"]))
                if "ID" in ev.columns:
                    for i in ev["ID"].dropna():
                        flagged.setdefault(str(i), []).append(f"{f['check']} {f['category']}")
        disp_cls = disp_cls.assign(FlaggedBy=disp_cls["ID"].astype(str).map(lambda i: "; ".join(flagged.get(i, []))))
        drop = [c for c in ("InformationRec",) if c in disp_cls.columns]
        disp_cls.drop(columns=drop).to_csv(os.path.join(out_dir, "dispensing_detail.csv"), index=False)
    tanks_df.to_csv(os.path.join(out_dir, "tank_reconciliation.csv"), index=False)
    stores_df.to_csv(os.path.join(out_dir, "store_reconciliation.csv"), index=False)
    pd.DataFrame(gaps, columns=["scope", "gap", "effect"]).to_csv(os.path.join(out_dir, "data_gaps.csv"), index=False)

    fmt = "%Y-%m-%d %H:%M"
    doc = {
        "client": client["name"], "client_short": client["short"],
        "generated_at_sast": datetime.now(SAST).strftime("%Y-%m-%d %H:%M:%S"),
        "source": src.kind,
        "window": {
            "boundary": f"{int(client['boundary_hour_sast']):02d}:00 SAST",
            "start_sast": ws_s.strftime(fmt) + " SAST", "end_sast": we_s.strftime(fmt) + " SAST",
            "start_utc": ws_s.tz_convert(UTC).strftime(fmt) + " UTC", "end_utc": we_s.tz_convert(UTC).strftime(fmt) + " UTC",
            "report_date": we_s.strftime("%Y-%m-%d"),
            "db_timezone_assumed": str(db_tz),
        },
        "accounts": [{"AccountID": a, "Account": names[a]} for a in accts],
        "kpis": kpis,
        "portfolio": portfolio,
        "findings": serial,
        "accounts_without_findings": [names[a] for a in accts
                                      if not any(f["account_id"] == a and f["status"] != "No action required" for f in serial)],
        "data_sources": d.available,
        "data_gaps": gaps,
        "checks_run": run,
        "check_registry": [{"check": c, "description": desc, "source": s} for c, desc, s in ic.CHECK_REGISTRY],
    }
    with open(os.path.join(out_dir, "findings.json"), "w") as fh:
        json.dump(doc, fh, indent=2, default=str)
    print(f"[{client['short']}] {kpis['investigate']} Investigate, {kpis['monitor']} Monitor -> {out_dir}", file=sys.stderr)
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(os.path.dirname(HERE), "config", "config.json"))
    ap.add_argument("--client", action="append", help="client short name (repeatable); default all")
    ap.add_argument("--run-time", help="run time, SAST unless an offset is given (default: now)")
    ap.add_argument("--source", choices=["db", "dir"], default="db")
    ap.add_argument("--data-dir", help="export directory for --source dir")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    with open(args.config) as fh:
        cfg = json.load(fh)
    rt = pd.Timestamp(args.run_time) if args.run_time else pd.Timestamp.now(tz=SAST)
    rt = rt.tz_localize(SAST) if rt.tzinfo is None else rt.tz_convert(SAST)

    src = DirSource(args.data_dir) if args.source == "dir" else DbSource()
    clients = [c for c in cfg["clients"] if not args.client or c["short"] in args.client]
    if not clients:
        sys.exit(f"No client matches {args.client}")
    summary = []
    for c in clients:
        doc = run_client(src, c, cfg, rt, args.out)
        summary.append({"client": c["short"], "window": f"{doc['window']['start_sast']} to {doc['window']['end_sast']}",
                        **{k: doc["kpis"][k] for k in ("investigate", "monitor", "total_fuel_dispensed_L", "reconciliation_pct")},
                        "data_gaps": len(doc["data_gaps"])})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
