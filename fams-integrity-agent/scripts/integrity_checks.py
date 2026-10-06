"""
FAMS daily integrity checks - pure functions over DataFrames.

No database access here (that's fams_sources.py), no report rendering
(that's the agent, from findings.json). Every check takes the loaded data
bundle `d` plus the config and returns a list of findings. Each check traces
back to a canonical file in fams-integrity or fams-daily-report - the
CHECK_REGISTRY at the bottom says which.

A finding is a dict:
    check      - check id (e.g. "C11")
    status     - "Investigate" | "Monitor" | "No action required"
    account_id - int (or None for client-wide)
    category   - short human label used in the report tables
    affected   - short string: litres / count / device involved
    litres     - float or None
    count      - int or None
    note       - what happened + possible cause + recommended next step
                 (language discipline: "possible cause", never "theft")
    evidence   - DataFrame of every underlying row (goes to the workbook)

Grouping discipline: one finding per account+category (or per device /
store / tank where that is the natural unit) - never one per row.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np
import pandas as pd

SENTINEL_MIN = 4294967.0          # 2^32/1000 - uint32 overflow sentinel
INVALID_IDS = {"", "N/A", "NA", "NULL", "NONE", "0", "NAN"}
MAC_PREFIX = re.compile(r"^[0-9A-Fa-f]{12}")
BT_MSG = re.compile(r"TrId:\s*([A-Za-z0-9]+).*?with\s+([\d.]+)\s*L", re.IGNORECASE)
INFOREC_TXID = re.compile(r"""transactionI[Dd]["']?\s*[:=]\s*["']?([A-Za-z0-9]+)""")


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def F(check, status, account_id, category, note, affected="", litres=None, count=None, evidence=None, **extra):
    f = {"check": check, "status": status, "account_id": None if account_id is None else int(account_id),
         "category": category, "affected": affected,
         "litres": None if litres is None else round(float(litres), 2),
         "count": None if count is None else int(count), "note": note,
         "evidence": evidence if evidence is not None else pd.DataFrame()}
    f.update(extra)
    return f


def empty(df):
    return df is None or len(df) == 0


def has(df, *cols):
    return df is not None and all(c in df.columns for c in cols)


def valid_id(s: pd.Series) -> pd.Series:
    return s.notna() & ~s.astype(str).str.strip().str.upper().isin(INVALID_IDS)


def in_window(df, d):
    if empty(df) or "CreateDate" not in df.columns:
        return df.iloc[0:0] if df is not None else None
    return df[(df["CreateDate"] >= d.window_start) & (df["CreateDate"] < d.window_end)]


def num(s):
    return pd.to_numeric(s, errors="coerce")


def valid_totaliser(s: pd.Series) -> pd.Series:
    v = num(s)
    return v.notna() & (v != 0) & (v < SENTINEL_MIN)


def tele_entries(raw):
    """TelementryData JSON -> list of entry dicts (tolerant of the shapes seen in exports)."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []
    if isinstance(obj, dict):
        inner = obj.get("TelementryData")
        if isinstance(inner, list):
            return [e for e in inner if isinstance(e, dict)]
        return [obj]
    if isinstance(obj, list):
        return [e for e in obj if isinstance(e, dict)]
    return []


def get_ci(entry: dict, *keys):
    low = {str(k).lower(): v for k, v in entry.items()}
    for k in keys:
        if k.lower() in low:
            return low[k.lower()]
    return None


def device_of(row):
    for c in ("DeviceID", "DeviceAlias"):
        v = row.get(c) if hasattr(row, "get") else None
        if v is not None and not (isinstance(v, float) and np.isnan(v)) and str(v).strip():
            return str(v)
    return None


def txid_from_inforec(raw):
    if not isinstance(raw, str) or not raw:
        return None
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            v = get_ci(obj, "transactionID")
            if v:
                return str(v)
    except Exception:
        pass
    m = INFOREC_TXID.search(raw)
    return m.group(1) if m else None


def acct_cfg_ids(cfg, key, account_id):
    return {int(x) for x in cfg.get(key, {}).get(str(int(account_id)), [])}


def notif_entries(d):
    """Flatten IOTData_Notification into one row per TelementryData entry (cached on d)."""
    if getattr(d, "_notif_flat", None) is not None:
        return d._notif_flat
    rows = []
    if not empty(d.notif) and "TelementryData" in d.notif.columns:
        for r in d.notif.to_dict("records"):
            for e in tele_entries(r.get("TelementryData")):
                t = get_ci(e, "Type", "TypeID")
                try:
                    t = int(t) if t is not None else None
                except (TypeError, ValueError):
                    t = None
                rows.append({
                    "AccountID": r.get("AccountID"), "NotifID": r.get("ID"), "CreateDate": r.get("CreateDate"),
                    "Device": device_of(r), "RowTypeID": r.get("TypeID"),
                    "EntryType": t if t is not None else r.get("TypeID"),
                    "TrId": get_ci(e, "TrId", "TrID", "trid"), "msg": get_ci(e, "msg", "message"),
                })
    d._notif_flat = pd.DataFrame(rows, columns=["AccountID", "NotifID", "CreateDate", "Device", "RowTypeID",
                                               "EntryType", "TrId", "msg"])
    if len(d._notif_flat):
        d._notif_flat["CreateDate"] = pd.to_datetime(d._notif_flat["CreateDate"], errors="coerce")
        d._notif_flat["EntryType"] = num(d._notif_flat["EntryType"])
    return d._notif_flat


# ----------------------------------------------------------------------------
# C01 duplicates (5 rules, merged into groups) + C02 TransactionID collision
# fams-integrity algorithms/duplicate-detection.md
# ----------------------------------------------------------------------------
def check_duplicates(d, cfg):
    out = []
    disp = d.disp
    if empty(disp) or not has(disp, "ID", "AccountID", "Volume", "CreateDate"):
        return out
    near_s = cfg["tolerances"]["duplicate_near_time_seconds"]
    off_pat = re.compile(cfg["recnumber_offload_batch_pattern"])
    df = disp[num(disp["Volume"]) > 0].copy()
    df["Volume"] = num(df["Volume"]).round(3)
    df = df.sort_values(["CreateDate", "ID"]).reset_index(drop=True)
    for c in ("UnqTrID", "TransactionID", "EquipmentID", "StoreID", "Recnumber"):
        if c not in df.columns:
            df[c] = np.nan

    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    rules = defaultdict(set)

    def by_keys(sub, keys, rule):
        for _, g in sub.groupby(keys, dropna=True):
            if len(g) > 1:
                ids = list(g["ID"])
                for i in ids[1:]:
                    union(ids[0], i)
                for i in ids:
                    rules[i].add(rule)

    uq = df[valid_id(df["UnqTrID"])]
    by_keys(uq, ["AccountID", "UnqTrID", "Volume", "EquipmentID"], "R1 UnqTrID+Volume+Equipment")
    by_keys(uq, ["AccountID", "UnqTrID", "EquipmentID", "CreateDate"], "R2 UnqTrID+Equipment+Time")
    by_keys(df, ["AccountID", "StoreID", "Volume", "CreateDate"], "R3 Store+Volume+Time")
    tx = df[valid_id(df["TransactionID"])]
    collisions = []
    for (acc, txid), g in tx.groupby(["AccountID", "TransactionID"]):
        if len(g) < 2:
            continue
        if g["Volume"].nunique() == 1:
            ids = list(g["ID"])
            for i in ids[1:]:
                union(ids[0], i)
            for i in ids:
                rules[i].add("R4 same TransactionID")
        else:
            collisions.append(g)
    # R5 near-time: same store+equipment+volume within N seconds, any IDs
    eq = df[num(df["EquipmentID"]).fillna(0) > 0]
    for _, g in eq.groupby(["AccountID", "StoreID", "EquipmentID", "Volume"]):
        if len(g) < 2:
            continue
        g = g.sort_values("CreateDate")
        t = g["CreateDate"].values
        ids = list(g["ID"])
        for k in range(1, len(g)):
            if (t[k] - t[k - 1]) / np.timedelta64(1, "s") <= near_s:
                union(ids[k - 1], ids[k])
                rules[ids[k - 1]].add(f"R5 Equipment+Volume within {near_s}s")
                rules[ids[k]].add(f"R5 Equipment+Volume within {near_s}s")

    groups = defaultdict(list)
    for i in rules:
        groups[find(i)].append(i)
    rows = df.set_index("ID")
    ev_known, ev_new = defaultdict(list), defaultdict(list)
    for gno, (root, ids) in enumerate(sorted(groups.items()), start=1):
        g = rows.loc[sorted(ids)].reset_index()
        in_win = ((g["CreateDate"] >= d.window_start) & (g["CreateDate"] < d.window_end)).any()
        if not in_win:
            continue
        acc = int(g["AccountID"].iloc[0])
        g["Role"] = ["original (lowest ID)"] + ["duplicate"] * (len(g) - 1)
        # only duplicates inside the window inflate this window's total
        g.loc[(g["Role"] == "duplicate") & ~((g["CreateDate"] >= d.window_start) & (g["CreateDate"] < d.window_end)),
              "Role"] = "duplicate (outside window)"
        g["Group"] = gno
        g["RulesMatched"] = [", ".join(sorted(rules[i])) for i in g["ID"]]
        recs = set(g["Recnumber"].astype(str))
        eqs = set(num(g["EquipmentID"]).dropna().astype(int))
        known = bool(eqs & acct_cfg_ids(cfg, "known_dual_write_equipment_ids", acc)) or (
            any(off_pat.match(r) for r in recs) and "importFams" in recs)
        g["KnownDualWriteBug"] = known
        (ev_known if known else ev_new)[acc].append(g)

    keep = ["Group", "Role", "RulesMatched", "ID", "AccountID", "StoreID", "EquipmentID", "TransactionID",
            "UnqTrID", "Volume", "CreateDate", "Recnumber", "KnownDualWriteBug"]
    for acc, parts in ev_new.items():
        ev = pd.concat(parts)
        excess = ev[ev["Role"] == "duplicate"]
        out.append(F("C01", "Investigate", acc, "Duplicate transactions",
                     f"{ev['Group'].nunique()} duplicate group(s): {len(excess)} extra row(s) inflate dispensed "
                     f"volume by {excess['Volume'].sum():.2f} L. Possible cause: double import of the same "
                     "transaction. Next step: confirm each group in the evidence (lowest ID kept as original) "
                     "and have a human remove the duplicate rows by explicit ID list - this agent never writes.",
                     affected=f"{excess['Volume'].sum():.2f} L / {len(excess)} rows", litres=excess["Volume"].sum(),
                     count=len(excess), evidence=ev[[c for c in keep if c in ev.columns]]))
    for acc, parts in ev_known.items():
        ev = pd.concat(parts)
        excess = ev[ev["Role"] == "duplicate"]
        out.append(F("C01", "Investigate", acc, "Duplicate transactions (known dual-pipeline bug)",
                     f"{ev['Group'].nunique()} group(s) match the known dual-pipeline duplicate-write bug "
                     "(same event written by the 4627x batch-transfer import and by importFams, seconds apart). "
                     f"{excess['Volume'].sum():.2f} L double-counted. Known, unresolved bug - not a new anomaly; "
                     "duplicates still need removal by a human.",
                     affected=f"{excess['Volume'].sum():.2f} L / {len(excess)} rows", litres=excess["Volume"].sum(),
                     count=len(excess), evidence=ev[[c for c in keep if c in ev.columns]]))
    by_acc = defaultdict(list)
    for g in collisions:
        if ((g["CreateDate"] >= d.window_start) & (g["CreateDate"] < d.window_end)).any():
            by_acc[int(g["AccountID"].iloc[0])].append(g)
    for acc, parts in by_acc.items():
        ev = pd.concat(parts)
        out.append(F("C02", "Investigate", acc, "TransactionID collision",
                     f"{len(parts)} TransactionID(s) are shared by rows with DIFFERENT volumes. Possible cause: "
                     "ID re-use/collision (seen at Richards Bay, where it caused a canonical-table override). "
                     "Either row may be overwriting or hiding the other - verify each against the raw device log.",
                     affected=f"{len(parts)} IDs", count=len(parts),
                     evidence=ev[[c for c in keep if c in ev.columns and c not in ("Group", "Role", "RulesMatched", "KnownDualWriteBug")]]))
    return out


# ----------------------------------------------------------------------------
# C03 missing TransactionID, C04 unreconciled UnqTrID, C05 InformationRec quality
# ----------------------------------------------------------------------------
def check_identifiers(d, cfg):
    out = []
    w = in_window(d.disp, d)
    if empty(w):
        return out
    w = w[num(w["Volume"]) > 0].copy()
    infrec = w["InformationRec"] if "InformationRec" in w.columns else pd.Series([None] * len(w), index=w.index)
    w["ProposedFromInformationRec"] = infrec.map(txid_from_inforec)
    cols = [c for c in ["ID", "AccountID", "StoreID", "EquipmentID", "TransactionID", "UnqTrID", "Volume",
                        "CreateDate", "Recnumber", "ProposedFromInformationRec"] if c in w.columns]
    if "TransactionID" in w.columns:
        miss = w[~valid_id(w["TransactionID"])]
        for acc, g in miss.groupby("AccountID"):
            out.append(F("C03", "Investigate", acc, "Missing TransactionID",
                         f"{len(g)} dispensing row(s) ({num(g['Volume']).sum():.2f} L) have no usable TransactionID, so "
                         "they cannot be reconciled against IOT/Android. "
                         f"{g['ProposedFromInformationRec'].notna().sum()} have a candidate ID inside InformationRec "
                         "(see evidence) - a human can backfill per fams-integrity algorithms/duplicate-detection.md.",
                         affected=f"{num(g['Volume']).sum():.2f} L / {len(g)} rows", litres=num(g["Volume"]).sum(),
                         count=len(g), evidence=g[cols]))
    if "UnqTrID" in w.columns:
        miss = w[~valid_id(w["UnqTrID"])]
        for acc, g in miss.groupby("AccountID"):
            out.append(F("C04", "Monitor", acc, "Unreconciled UnqTrID",
                         f"{len(g)} row(s) still carry UnqTrID 'N/A'/NULL - reconciliation did not complete for them. "
                         "Candidate IDs from InformationRec are in the evidence for a human backfill.",
                         affected=f"{len(g)} rows", count=len(g), evidence=g[cols]))
    if "InformationRec" in w.columns:
        tol = cfg["tolerances"]["infrec_truncation_pct"]
        for acc, g in w.groupby("AccountID"):
            s = g["InformationRec"].astype(str)
            trunc = s.str.contains("Over Character Limit", case=False, na=False)
            blank = g["InformationRec"].isna() | (s.str.strip() == "")
            pct = (trunc | blank).mean() * 100
            if pct > tol:
                out.append(F("C05", "Monitor", acc, "InformationRec truncated/blank",
                             f"{pct:.1f}% of rows have an InformationRec that is truncated ('Over Character Limit') "
                             f"or blank (tolerance {tol}%). The raw record needed for backfill and dispute "
                             "investigation is lost for these rows. Possible cause: payload over the column limit.",
                             affected=f"{pct:.1f}% of {len(g)} rows", count=int((trunc | blank).sum()),
                             evidence=g[trunc | blank][[c for c in cols if c != "ProposedFromInformationRec"]]))
    return out


# ----------------------------------------------------------------------------
# C06-C08 dispensing reconciliation: UsageDispensing (source of truth) vs backups IOT/Android, both directions
# fams-daily-report analyze.py classify_dispensing; fams-integrity atg-reconciliation.md
# ----------------------------------------------------------------------------
def classify_dispensing(d, cfg):
    """Returns (window dispensing rows with Classification, findings)."""
    out = []
    tol = cfg["tolerances"]["volume_tolerance_pct"]
    silence_min = cfg["tolerances"]["backup_feed_silence_minutes"]
    w = in_window(d.disp, d)
    if empty(w):
        return (w if w is not None else pd.DataFrame()), out
    w = w.copy()
    w["Volume"] = num(w["Volume"])
    iot = d.iot if not empty(d.iot) else pd.DataFrame(columns=["TransactionID", "Volume", "AccountID", "CreateDate"])
    andr = d.android if not empty(d.android) else pd.DataFrame(columns=["TransactionID", "Volume", "AccountID", "CreateDate"])
    key = lambda df: set(zip(df["AccountID"].astype("Int64"), df["TransactionID"].astype(str)))  # noqa: E731
    iot_k, and_k = key(iot), key(andr)
    wk = list(zip(w["AccountID"].astype("Int64"), w["TransactionID"].astype(str)))
    w["MatchedIOT"] = [k in iot_k for k in wk]
    w["MatchedAndroid"] = [k in and_k for k in wk]
    raw_times = pd.concat([iot[["AccountID", "CreateDate"]], andr[["AccountID", "CreateDate"]]]).dropna()

    def classify(r):
        if r["MatchedIOT"] or r["MatchedAndroid"]:
            return "Reconciled"
        if not (r["Volume"] > 0):
            return "Zero-volume, informational"
        if not r["_ValidTx"]:
            return "Missing TransactionID (see C03)"
        eq = num(pd.Series([r.get("EquipmentID")]))[0]
        if pd.notna(eq) and int(eq) in acct_cfg_ids(cfg, "known_offload_equipment_ids", r["AccountID"]):
            return "Confirmed offloading (known tank-linked equipment)"
        return "Unexplained - no backup record"

    w["_ValidTx"] = valid_id(w["TransactionID"])
    w["Classification"] = w.apply(classify, axis=1)
    w = w.drop(columns="_ValidTx")
    w["CheckFlags"] = ""

    # volume mismatch: IOT first, then Android for rows IOT didn't match
    mism = []
    for src, label, flag in ((iot, "IOT", "MatchedIOT"), (andr, "Android", "MatchedAndroid")):
        if empty(src):
            continue
        s = src.assign(TxKey=src["TransactionID"].astype(str), SrcVolume=num(src["Volume"]))[
            ["AccountID", "TxKey", "SrcVolume"]].drop_duplicates(["AccountID", "TxKey"])
        cand = w[w[flag] & (w["Classification"] == "Reconciled")].assign(TxKey=lambda x: x["TransactionID"].astype(str))
        if label == "Android":
            cand = cand[~cand["MatchedIOT"]]
        m = cand.reset_index().merge(s, on=["AccountID", "TxKey"])
        m["PctDiff"] = (m["Volume"] - m["SrcVolume"]).abs() / m["Volume"].replace(0, np.nan) * 100
        bad = m[m["PctDiff"] > tol]
        if len(bad):
            w.loc[bad["index"], "Classification"] = "Volume mismatch"
            mism.append(bad.assign(ComparedWith=label))

    # backup-feed (IOT+Android) silence annotation for unexplained rows (telemetry-outage false positive)
    unexpl_idx = w.index[w["Classification"] == "Unexplained - no backup record"]
    silence = pd.Series(False, index=w.index)
    for i in unexpl_idx:
        t, acc = w.at[i, "CreateDate"], w.at[i, "AccountID"]
        rt = raw_times[raw_times["AccountID"] == acc]["CreateDate"]
        before, after = rt[rt <= t], rt[rt >= t]
        gap_b = (t - before.max()).total_seconds() / 60 if len(before) else np.inf
        gap_a = (after.min() - t).total_seconds() / 60 if len(after) else np.inf
        silence[i] = gap_b > silence_min and gap_a > silence_min
    w["DuringBackupFeedSilence"] = silence
    w["PossibleOffloadPattern"] = (w["Classification"] == "Unexplained - no backup record") & \
        w["TransactionID"].astype(str).str.match(MAC_PREFIX)

    cols = [c for c in ["ID", "AccountID", "StoreID", "EquipmentID", "TransactionID", "UnqTrID", "Volume",
                        "CreateDate", "Recnumber", "MatchedIOT", "MatchedAndroid", "DuringBackupFeedSilence",
                        "PossibleOffloadPattern"] if c in w.columns]
    for acc, g in w[w["Classification"] == "Unexplained - no backup record"].groupby("AccountID"):
        g_out = g[g["DuringBackupFeedSilence"]]
        g_in = g[~g["DuringBackupFeedSilence"]]
        pending = acct_cfg_ids(cfg, "pending_offload_equipment_ids", acc)
        if len(g_in):
            note = (f"{len(g_in)} non-zero dispensing transaction(s) ({g_in['Volume'].sum():.2f} L) have no matching "
                    "UsageDispensingIOT or UsageDispensingAndroid record, while those feeds were otherwise reporting. "
                    "UsageDispensing is the source of truth, so the transaction stands; what is missing is its backup "
                    "evidence. Possible causes: backup record not created/uploaded, ID mismatch, or offloading recorded "
                    "as dispensing.")
            po = g_in[g_in["PossibleOffloadPattern"]]
            if len(po):
                eqs = sorted({str(int(e)) for e in num(po["EquipmentID"]).dropna()})
                note += (f" {len(po)} have a device-MAC-prefixed TransactionID (EquipmentID {', '.join(eqs)}) - the "
                         "tank-linked offload pattern; a pattern, not proof.")
            pe = g_in[num(g_in["EquipmentID"]).isin(pending)]
            if len(pe):
                note += (f" {len(pe)} are on EquipmentID(s) pending owner confirmation as tank-linked offload units "
                         f"({', '.join(str(x) for x in sorted(pending))}) - still counted until confirmed.")
            out.append(F("C06", "Investigate", acc, "Unexplained dispensing", note,
                         affected=f"{g_in['Volume'].sum():.2f} L / {len(g_in)} txns", litres=g_in["Volume"].sum(),
                         count=len(g_in), evidence=g_in[cols]))
        if len(g_out):
            out.append(F("C06", "Monitor", acc, "Unexplained dispensing during backup-feed outage",
                         f"{len(g_out)} transaction(s) ({g_out['Volume'].sum():.2f} L) fall inside a stretch where "
                         f"neither IOT nor Android reported anything for >{silence_min} min either side, while "
                         "UsageDispensing kept logging. Possible cause: device/connectivity outage (confirmed pattern "
                         "at Estcourt and Richards Bay) rather than lost fuel. Check the telemetry-gap finding for this "
                         "account and confirm the outage before treating as a loss.",
                         affected=f"{g_out['Volume'].sum():.2f} L / {len(g_out)} txns", litres=g_out["Volume"].sum(),
                         count=len(g_out), evidence=g_out[cols]))
    if mism:
        mm = pd.concat(mism)
        for acc, g in mm.groupby("AccountID"):
            out.append(F("C07", "Investigate", acc, "Volume mismatch (UsageDispensing vs backup)",
                         f"{len(g)} transaction(s) differ by more than {tol}% between UsageDispensing and the "
                         "backup record (IOT first, else Android) of the same TransactionID. UsageDispensing is the source of "
                         "truth; the difference needs explaining. Possible causes: manual edit, BT link loss "
                         "mid-transaction, or decode error. Check the totaliser evidence for each.",
                         affected=f"{g['Volume'].sum():.2f} L / {len(g)} txns", litres=g["Volume"].sum(),
                         count=len(g), evidence=g[[c for c in ["ID", "AccountID", "StoreID", "EquipmentID",
                                                               "TransactionID", "CreateDate", "Volume", "ComparedWith",
                                                               "SrcVolume", "PctDiff"] if c in g.columns]]))
    known = w[w["Classification"].str.startswith("Confirmed offloading")]
    for acc, g in known.groupby("AccountID"):
        out.append(F("C06", "No action required", acc, "Known tank-linked offload equipment",
                     f"{len(g)} transaction(s) ({g['Volume'].sum():.2f} L) on owner-confirmed offload equipment "
                     "excluded from the dispensing-anomaly count.", litres=g["Volume"].sum(), count=len(g),
                     evidence=g[cols]))

    # C08 reverse direction: backup record (IOT/Android) with no UsageDispensing row
    canon = set(zip(d.disp["AccountID"].astype("Int64"), d.disp["TransactionID"].astype(str))) if not empty(d.disp) else set()
    for tbl in (d.transfer, d.receiving):
        if not empty(tbl) and has(tbl, "AccountID", "TransactionID"):
            canon |= set(zip(tbl["AccountID"].astype("Int64"), tbl["TransactionID"].astype(str)))
    for src, label in ((d.iot, "UsageDispensingIOT"), (d.android, "UsageDispensingAndroid")):
        sw = in_window(src, d)
        if empty(sw) or not has(sw, "AccountID", "TransactionID", "Volume"):
            continue
        sw = sw[(num(sw["Volume"]) > 0) & valid_id(sw["TransactionID"])]
        if "TypeID" in sw.columns:
            sw = sw[~num(sw["TypeID"]).isin([4])]
        miss = sw[[k not in canon for k in zip(sw["AccountID"].astype("Int64"), sw["TransactionID"].astype(str))]]
        for acc, g in miss.groupby("AccountID"):
            out.append(F("C08", "Investigate", acc, f"Backup record missing from UsageDispensing ({label})",
                         f"{len(g)} {label} transaction(s) ({num(g['Volume']).sum():.2f} L) never reached "
                         "UsageDispensing/UsageTransfer/UsageReceiving (searched across the whole fetched range, not "
                         "just the window). UsageDispensing is the source of truth for client reporting, so these litres are "
                         "missing from it. Possible cause: import/decode failure.", affected=f"{num(g['Volume']).sum():.2f} L / {len(g)} txns",
                         litres=num(g["Volume"]).sum(), count=len(g),
                         evidence=g[[c for c in ["ID", "AccountID", "DeviceID", "StoreID", "TransactionID", "TypeID",
                                                 "ProductID", "Volume", "CreateDate"] if c in g.columns]]))
    return w, out


# ----------------------------------------------------------------------------
# C09 FMS TypeID outside {1,2,3,4}
# ----------------------------------------------------------------------------
def check_fms_typeids(d, cfg):
    w = in_window(d.fms, d)
    if empty(w) or "TypeID" not in w.columns:
        return []
    bad = w[~num(w["TypeID"]).isin([1, 2, 3, 4])]
    return [F("C09", "Monitor", acc, "Unknown IOTData_FMS TypeID",
              f"{len(g)} FMS record(s) carry TypeID {sorted(set(g['TypeID'].astype(str)))} outside the documented "
              "1=Dispensing, 2=Transfer, 3=Offloading, 4=Complete. Not guessed - treated as Unknown.",
              affected=f"{len(g)} rows", count=len(g),
              evidence=g[[c for c in ["ID", "AccountID", "DeviceID", "TransactionID", "TypeID", "CreateDate"] if c in g.columns]])
            for acc, g in bad.groupby("AccountID")]


# ----------------------------------------------------------------------------
# C10 manual-entry candidates (Recnumber)
# ----------------------------------------------------------------------------
def check_recnumber(d, cfg):
    out = []
    w = in_window(d.disp, d)
    if empty(w) or "Recnumber" not in w.columns:
        return out
    pats = [re.compile(p) for p in cfg["recnumber_known_patterns"]]
    off = re.compile(cfg["recnumber_offload_batch_pattern"])
    cols = [c for c in ["ID", "AccountID", "StoreID", "EquipmentID", "TransactionID", "Volume", "CreateDate", "Recnumber"] if c in w.columns]
    rec = w["Recnumber"].astype(str).str.strip()
    blank = w["Recnumber"].isna() | rec.isin(["", "nan", "None"])
    is_off = rec.str.match(off) & ~blank
    known = rec.map(lambda r: any(p.match(r) for p in pats)) & ~is_off & ~blank
    for acc, g in w[is_off].groupby("AccountID"):
        allowed = acct_cfg_ids(cfg, "known_offload_equipment_ids", acc) | acct_cfg_ids(cfg, "pending_offload_equipment_ids", acc)
        on_known = num(g["EquipmentID"]).isin(allowed)
        if on_known.any():
            k = g[on_known]
            out.append(F("C10", "Monitor", acc, "Recnumber 4627x batch series (known pattern)",
                         f"{len(k)} row(s) in the 4627x transfer/offload batch series on known/pending offload "
                         "equipment - continuing the known pattern, not a manual entry. Surfaced because the account "
                         "owner has not signed off the whole series.", count=len(k), litres=num(k["Volume"]).sum(),
                         affected=f"{len(k)} rows", evidence=k[cols]))
        if (~on_known).any():
            n = g[~on_known]
            out.append(F("C10", "Investigate", acc, "Recnumber 4627x series on unexpected equipment",
                         f"{len(n)} 4627x-series row(s) on EquipmentID(s) not in the known/pending offload list. "
                         "Possible new tank-linked unit or a manual entry - confirm with the account owner.",
                         count=len(n), litres=num(n["Volume"]).sum(), affected=f"{len(n)} rows", evidence=n[cols]))
    manual = w[~known & ~is_off & ~blank]
    for acc, g in manual.groupby("AccountID"):
        out.append(F("C10", "Investigate", acc, "Possible manual entry",
                     f"{len(g)} row(s) with Recnumber {sorted(set(g['Recnumber'].astype(str)))[:8]} outside the known "
                     "batch-import formats. Historically no manual dispensing entries exist - a candidate, not proof. "
                     "If this is a legitimate new batch format, add it to recnumber_known_patterns in config.",
                     count=len(g), litres=num(g["Volume"]).sum(), affected=f"{len(g)} rows", evidence=g[cols]))
    for acc, g in w[blank].groupby("AccountID"):
        out.append(F("C10", "Monitor", acc, "Recnumber blank",
                     f"{len(g)} row(s) have no Recnumber (no provenance).", count=len(g), affected=f"{len(g)} rows",
                     evidence=g[cols]))
    return out


# ----------------------------------------------------------------------------
# C11 ProductID / ProdID = 0
# ----------------------------------------------------------------------------
def check_product_zero(d, cfg):
    out = []
    srcs = (("UsageDispensing", d.disp, "StoreID"), ("UsageDispensingIOT", d.iot, "DeviceID"),
            ("UsageDispensingAndroid", d.android, "InformationMac"), ("UsageTransfer", d.transfer, "StoreID"),
            ("UsageReceiving", d.receiving, "StoreID"))
    parts = defaultdict(list)
    for label, df, unit in srcs:
        w = in_window(df, d)
        if empty(w) or "ProductID" not in w.columns:
            continue
        p = num(w["ProductID"])
        bad = w[(p == 0) | w["ProductID"].isna()]
        if "Volume" in bad.columns:
            bad = bad[num(bad["Volume"]).fillna(0) > 0]
        if len(bad):
            parts_cols = [c for c in ["ID", "AccountID", "StoreID", "DeviceID", "InformationMac", "EquipmentID",
                                      "TransactionID", "ProductID", "Volume", "CreateDate"] if c in bad.columns]
            for acc, g in bad.groupby("AccountID"):
                parts[acc].append(g[parts_cols].assign(SourceTable=label))
    fw = in_window(d.fms, d)
    if not empty(fw) and "TelementryData" in fw.columns:
        rows = []
        for r in fw.to_dict("records"):
            for e in tele_entries(r.get("TelementryData")):
                v = get_ci(e, "prodId", "ProdID", "productId", "ProductID")
                if v is not None and str(v).strip() in ("0", "0.0"):
                    rows.append({"ID": r.get("ID"), "AccountID": r.get("AccountID"), "DeviceID": device_of(r),
                                 "TransactionID": r.get("TransactionID"), "ProductID": 0,
                                 "CreateDate": r.get("CreateDate"), "SourceTable": "IOTData_FMS (TelementryData)"})
        if rows:
            fr = pd.DataFrame(rows)
            for acc, g in fr.groupby("AccountID"):
                parts[acc].append(g)
    for acc, ps in parts.items():
        ev = pd.concat(ps, ignore_index=True)
        units = sorted({str(x) for c in ("StoreID", "DeviceID", "InformationMac") if c in ev.columns
                        for x in ev[c].dropna().unique()})
        vol = num(ev["Volume"]).sum() if "Volume" in ev.columns else None
        out.append(F("C11", "Investigate", acc, "ProductID = 0",
                     f"{len(ev)} record(s) across {sorted(ev['SourceTable'].unique())} carry ProductID/ProdID 0 (or "
                     f"blank) on store/device {', '.join(units[:10])}. Breaks per-product reporting, nozzle identity "
                     "and the totaliser chain. Possible cause: nozzle/product not configured on the device or in "
                     "PerStoreProduct. Next step: check the product mapping for these devices.",
                     affected=f"{len(ev)} records", litres=vol, count=len(ev), evidence=ev))
    return out


# ----------------------------------------------------------------------------
# C12 totaliser flow continuity per nozzle, C13 sentinel / capture failure
# fams-integrity business-rules/nozzle-validation.md, datasets/calculations.md
# ----------------------------------------------------------------------------
def _chain_breaks(df, key, start_col, end_col, mac_col, tol, d, source, real_start_mask=None):
    """Walk each nozzle's transactions in time order; a break is next.start - prev.end beyond +/- tol."""
    breaks, ambiguous = [], []
    df = df.copy()
    for k in key:
        df[k] = df[k].astype("object").where(df[k].notna(), "(blank)")
    df["_real_start"] = True if real_start_mask is None else real_start_mask.reindex(df.index).fillna(False).astype(bool)
    for nk, g in df.sort_values(["CreateDate", "ID"]).groupby(key, sort=False):
        g = g.reset_index(drop=True)
        if len(g) < 2:
            continue
        pairs = 0
        chain = []
        for i in range(1, len(g)):
            prev, nxt = g.iloc[i - 1], g.iloc[i]
            if not (d.window_start <= nxt["CreateDate"] < d.window_end):
                continue
            pe, ns = num(pd.Series([prev[end_col]]))[0], num(pd.Series([nxt[start_col]]))[0]
            if not (valid_totaliser(pd.Series([pe]))[0] and valid_totaliser(pd.Series([ns]))[0] and nxt["_real_start"]):
                continue
            pairs += 1
            gap = ns - pe
            if abs(gap) > tol:
                chain.append({
                    "Source": source, "Macaddress": prev.get(mac_col), "NozzleKey": " | ".join(str(x) for x in (nk if isinstance(nk, tuple) else (nk,))),
                    "AccountID": prev.get("AccountID"), "StoreID": prev.get("StoreID"), "ProductID": prev.get("ProductID"),
                    "ID": prev.get("ID"), "TransactionID": prev.get("TransactionID"), "CreateDate": prev["CreateDate"],
                    "Volume": num(pd.Series([prev.get("Volume")]))[0], "TotaliserEnd": pe,
                    "NextID": nxt.get("ID"), "NextTransactionID": nxt.get("TransactionID"),
                    "NextCreateDate": nxt["CreateDate"], "NextVolume": num(pd.Series([nxt.get("Volume")]))[0],
                    "NextTotaliserStart": ns, "Gap_L": round(gap, 2),
                    "MissingVolume_L": round(gap, 2) if gap > 0 else None,
                    "BreakType": "Skipped volume (next start above previous end)" if gap > 0
                    else "Totaliser went backwards (next start below previous end)",
                })
        if chain and pairs >= 4 and len(chain) / pairs > 0.3:
            ambiguous.append({"Source": source, "NozzleKey": chain[0]["NozzleKey"], "AccountID": chain[0]["AccountID"],
                              "PairsChecked": pairs, "Breaks": len(chain)})
        else:
            breaks.extend(chain)
    return breaks, ambiguous


def check_totaliser(d, cfg):
    out = []
    tol = cfg["tolerances"]["totaliser_continuity_litres"]
    breaks, ambiguous = [], []
    # Android: confirmed nozzle key (StoreID, ProductID, TrailerMac, InformationMac)
    a = d.android
    if not empty(a) and has(a, "Totalizer", "TotalizerEnd", "CreateDate", "ID"):
        a = a[num(a["Volume"]) > 0] if "Volume" in a.columns else a
        for c in ("StoreID", "ProductID", "TrailerMac", "InformationMac"):
            if c not in a.columns:
                a = a.assign(**{c: np.nan})
        b, amb = _chain_breaks(a, ["AccountID", "StoreID", "ProductID", "TrailerMac", "InformationMac"],
                               "Totalizer", "TotalizerEnd", "InformationMac", tol, d, "UsageDispensingAndroid")
        breaks += b
        ambiguous += amb
    # IOT: TotaliserStart is real only when IOTData_FMS.TotaliserFromComms = 1
    i = d.iot
    if not empty(i) and has(i, "TotaliserStart", "TotaliserEnd", "CreateDate", "ID", "DeviceID"):
        i = i[num(i["Volume"]) > 0] if "Volume" in i.columns else i
        if "TypeID" in i.columns:
            i = i[~num(i["TypeID"]).isin([4])]
        real = pd.Series(False, index=i.index)
        if not empty(d.fms) and "TotaliserFromComms" in d.fms.columns:
            fc = num(d.fms["TotaliserFromComms"])
            by_id = dict(zip(d.fms["ID"], fc)) if "ID" in d.fms.columns else {}
            by_tx = d.fms.assign(fc=fc).groupby("TransactionID")["fc"].max().to_dict() if "TransactionID" in d.fms.columns else {}
            real = pd.Series([(by_id.get(r.get("IOTData_FMSID")) if r.get("IOTData_FMSID") in by_id
                               else by_tx.get(r.get("TransactionID"))) == 1 for r in i.to_dict("records")], index=i.index)
        key = [k for k in cfg.get("iot_nozzle_key", ["DeviceID", "ProductID"]) if k in i.columns]
        b, amb = _chain_breaks(i, ["AccountID"] + key, "TotaliserStart", "TotaliserEnd", "DeviceID", tol, d,
                               "UsageDispensingIOT", real_start_mask=real)
        breaks += b
        ambiguous += amb
    if breaks:
        ev = pd.DataFrame(breaks)
        # same physical break seen by both feeds -> one row
        ev = ev.sort_values("Source").drop_duplicates(["AccountID", "TransactionID", "NextTransactionID"], keep="first")
        disp_id = {}
        if not empty(d.disp) and has(d.disp, "TransactionID", "ID"):
            disp_id = d.disp.drop_duplicates("TransactionID").set_index(d.disp.drop_duplicates("TransactionID")["TransactionID"].astype(str))["ID"].to_dict()
        ev["UsageDispensingID"] = ev["TransactionID"].astype(str).map(disp_id)
        nf = notif_entries(d)
        expl = {}
        if len(nf):
            for tr, g in nf[nf["TrId"].notna()].groupby("TrId"):
                types = set(g["EntryType"].dropna().astype(int))
                why = []
                if 132 in types:
                    why.append("BTLinkLost on this TrId")
                if 1 in types:
                    why.append("Startup/cyclic reset on this TrId")
                if why:
                    expl[str(tr)] = "; ".join(why)
        ev["Explanation"] = ev["TransactionID"].astype(str).map(expl).fillna("")
        order = ["Source", "Macaddress", "ID", "UsageDispensingID", "TransactionID", "Volume", "MissingVolume_L",
                 "BreakType", "CreateDate", "TotaliserEnd", "NextID", "NextTransactionID", "NextCreateDate",
                 "NextVolume", "NextTotaliserStart", "Gap_L", "AccountID", "StoreID", "ProductID", "NozzleKey",
                 "Explanation"]
        ev = ev[order]
        for acc, g in ev.groupby("AccountID"):
            miss = num(g["MissingVolume_L"]).sum()
            out.append(F("C12", "Investigate", acc, "Totaliser flow break",
                         f"{len(g)} break(s) in the per-nozzle totaliser sequence (tolerance {tol} L): "
                         f"{int(g['MissingVolume_L'].notna().sum())} skipped forward ({miss:.2f} L dispensed by the "
                         f"meter but not recorded), {int(g['MissingVolume_L'].isna().sum())} went backwards. The "
                         "flagged transaction (ID / TransactionID) is the one BEFORE the jump - its recorded volume is "
                         "likely short by MissingVolume_L. Possible causes: BT link lost mid-transaction, device reset, "
                         "or an unrecorded dispense. No auto-correction - verify against the device log.",
                         affected=f"{miss:.2f} L missing / {len(g)} breaks", litres=miss, count=len(g), evidence=g))
    if ambiguous:
        am = pd.DataFrame(ambiguous)
        for acc, g in am.groupby("AccountID"):
            out.append(F("C12", "Monitor", acc, "Totaliser chain unverifiable (ambiguous nozzle key)",
                         f"{len(g)} nozzle chain(s) break on more than 30% of consecutive pairs - more likely two "
                         "physical nozzles sharing one key (e.g. two hoses on one device and product) than real "
                         "skips. Not reported as breaks; the nozzle key for this source needs refining.",
                         affected=f"{len(g)} chains", count=len(g), evidence=g))

    # C13 sentinel values reported as real comms readings / capture failure
    sent_rows = []
    if not empty(d.iot) and has(d.iot, "TotaliserStart"):
        w = in_window(d.iot, d)
        s = w[num(w["TotaliserStart"]) >= SENTINEL_MIN]
        if len(s):
            sent_rows.append(s.assign(SourceTable="UsageDispensingIOT", Value=s["TotaliserStart"]))
    if not empty(d.android) and has(d.android, "Totalizer"):
        w = in_window(d.android, d)
        s = w[(num(w["Totalizer"]) >= SENTINEL_MIN) | (num(w.get("TotalizerEnd", pd.Series(dtype=float))) >= SENTINEL_MIN)]
        if len(s):
            sent_rows.append(s.assign(SourceTable="UsageDispensingAndroid", Value=s["Totalizer"]))
    if sent_rows:
        ev = pd.concat(sent_rows, ignore_index=True)
        cols = [c for c in ["SourceTable", "ID", "AccountID", "DeviceID", "InformationMac", "TransactionID", "Volume",
                            "CreateDate", "Value"] if c in ev.columns]
        for acc, g in ev.groupby("AccountID"):
            out.append(F("C13", "Monitor", acc, "Totaliser overflow sentinel",
                         f"{len(g)} reading(s) carry the uint32 overflow value (~4294967.295) as a totaliser - "
                         "confirmed firmware bug pattern (AccountID 354). These transactions cannot be "
                         "totaliser-verified.", affected=f"{len(g)} rows", count=len(g), evidence=g[cols]))
    if not empty(d.android) and has(d.android, "Totalizer", "CreateDate"):
        a = d.android[num(d.android["Volume"]) > 0] if "Volume" in d.android.columns else d.android
        key = [c for c in ["AccountID", "StoreID", "ProductID", "TrailerMac", "InformationMac"] if c in a.columns]
        a = a.assign(_ok=valid_totaliser(a["Totalizer"]))
        rows = []
        for k, g in a.groupby(key, dropna=False):
            hist = g[g["CreateDate"] < d.window_start]
            win = g[(g["CreateDate"] >= d.window_start) & (g["CreateDate"] < d.window_end)]
            if len(hist) >= 10 and hist["_ok"].mean() >= 0.9 and len(win) and (~win["_ok"]).any():
                rows.append(win[~win["_ok"]])
        if rows:
            ev = pd.concat(rows)
            cols = [c for c in ["ID", "AccountID", "StoreID", "ProductID", "InformationMac", "TrailerMac",
                                "TransactionID", "Volume", "CreateDate", "Totalizer", "TotalizerEnd"] if c in ev.columns]
            for acc, g in ev.groupby("AccountID"):
                out.append(F("C13", "Monitor", acc, "Totaliser capture failure",
                             f"{len(g)} transaction(s) on nozzles that normally report a totaliser (>=90% of history) "
                             "came through with 0/invalid totaliser - a genuine capture failure, not that hardware's "
                             "normal behaviour.", affected=f"{len(g)} txns", count=len(g), evidence=g[cols]))
    return out


# ----------------------------------------------------------------------------
# C14 BTLinkLost cross-check and concentration
# fams-integrity anomaly-library/device-integrity.md
# ----------------------------------------------------------------------------
def check_btlinklost(d, cfg):
    out = []
    nf = notif_entries(d)
    if not len(nf):
        return out
    bt = nf[(nf["EntryType"] == 132) | (num(nf["RowTypeID"]) == 132)]
    bt = bt[(bt["CreateDate"] >= d.window_start) & (bt["CreateDate"] < d.window_end)].copy()
    if not len(bt):
        return out
    tol = cfg["tolerances"]["actual_volume_delta_litres"]
    parsed = bt["msg"].astype(str).str.extract(BT_MSG)
    bt["MsgTrId"] = parsed[0]
    bt["MsgVolume_L"] = num(parsed[1])
    bt["TrId"] = bt["TrId"].fillna(bt["MsgTrId"])
    disp = d.disp if not empty(d.disp) else pd.DataFrame(columns=["AccountID", "TransactionID", "ID", "Volume"])
    dmap = disp.drop_duplicates(["AccountID", "TransactionID"]).set_index(["AccountID", disp.drop_duplicates(
        ["AccountID", "TransactionID"])["TransactionID"].astype(str)])
    amap = {}
    if not empty(d.android) and has(d.android, "Totalizer", "TotalizerEnd", "TransactionID"):
        ok = d.android[valid_totaliser(d.android["Totalizer"]) & valid_totaliser(d.android["TotalizerEnd"])]
        amap = dict(zip(ok["TransactionID"].astype(str), (num(ok["TotalizerEnd"]) - num(ok["Totalizer"])).abs()))
    recs = []
    for r in bt.to_dict("records"):
        k = (r["AccountID"], str(r["TrId"]))
        rec = dmap.loc[k] if k in dmap.index else None
        recs.append({**r, "UsageDispensingID": None if rec is None else rec["ID"],
                     "RecordedVolume_L": None if rec is None else num(pd.Series([rec["Volume"]]))[0],
                     "TotaliserActual_L": amap.get(str(r["TrId"]))})
    ev = pd.DataFrame(recs)
    ev["Delta_L"] = ev["TotaliserActual_L"] - ev["RecordedVolume_L"]
    ev = ev[["AccountID", "Device", "CreateDate", "NotifID", "TrId", "msg", "MsgVolume_L", "UsageDispensingID",
             "RecordedVolume_L", "TotaliserActual_L", "Delta_L"]]
    for acc, g in ev.groupby("AccountID"):
        missing = g[g["UsageDispensingID"].isna() & g["TrId"].notna()]
        short = g[g["Delta_L"].abs() > tol]
        if len(short):
            out.append(F("C14", "Investigate", acc, "BTLinkLost - recorded volume differs from meter",
                         f"{len(short)} BT-link-loss transaction(s) where the recorded volume differs from the "
                         f"totaliser-derived actual by more than {tol} L (sum {short['Delta_L'].sum():.2f} L). "
                         "Possible cause: link dropped mid-dispense, so the remainder was not recorded.",
                         affected=f"{short['Delta_L'].sum():.2f} L / {len(short)} txns",
                         litres=short["Delta_L"].abs().sum(), count=len(short), evidence=short))
        if len(missing):
            out.append(F("C14", "Investigate", acc, "BTLinkLost - transaction not in UsageDispensing",
                         f"{len(missing)} BT-link-loss TrId(s) have no UsageDispensing row anywhere in the fetched "
                         "range (already searched across day boundaries). Possible lost transaction.",
                         affected=f"{len(missing)} TrIds", count=len(missing), evidence=missing))
    # concentration + idle-timeout signature
    counts = ev.groupby(["AccountID", "Device"]).size()
    if len(counts):
        med = float(counts.median())
        thr = max(cfg["tolerances"]["btlinklost_outlier_min_events"], 3 * med if len(counts) > 2 else 0)
        done124 = nf[(nf["EntryType"] == 124) | (num(nf["RowTypeID"]) == 124)]
        for (acc, dev), n in counts.items():
            if n < thr:
                continue
            g = ev[(ev["AccountID"] == acc) & (ev["Device"] == dev)].sort_values("CreateDate")
            c = done124[done124["Device"] == dev]["CreateDate"].sort_values()
            lags = []
            for t in g["CreateDate"]:
                prior = c[c <= t]
                if len(prior):
                    lags.append((t - prior.iloc[-1]).total_seconds())
            note = (f"Device {dev} logged {n} BTLinkLost events this window (portfolio median per device "
                    f"{med:.0f}). ")
            if len(lags) >= 5 and np.std(lags) < 3 and 5 <= np.median(lags) <= 120:
                note += (f"Every one fires {np.median(lags):.1f}s (sd {np.std(lags):.1f}s) after the device's last "
                         "DispTransactionComplete - a fixed Bluetooth idle-timeout signature (as at Cato Ridge), not "
                         "RF interference, and the disconnect comes after completion so no data loss is indicated. "
                         "Compare the BT idle-timeout config/firmware with a unit that does not show this.")
            else:
                note += "Disproportionate link loss - recommend a hardware/antenna check on this specific device."
            out.append(F("C14", "Monitor", acc, "BTLinkLost concentration", note, affected=f"{dev}: {n} events",
                         count=int(n), device=dev, evidence=g))
    return out


# ----------------------------------------------------------------------------
# C15 missing EquipmentID (with BTLinkLost co-occurrence)
# ----------------------------------------------------------------------------
def check_missing_equipment(d, cfg):
    out = []
    w = in_window(d.disp, d)
    if empty(w) or "EquipmentID" not in w.columns:
        return out
    bad = w[(num(w["EquipmentID"]).fillna(0) == 0) & (num(w["Volume"]) > 0)].copy()
    if not len(bad):
        return out
    nf = notif_entries(d)
    bt = nf[(nf["EntryType"] == 132) | (num(nf["RowTypeID"]) == 132)] if len(nf) else nf
    win = pd.Timedelta(minutes=cfg["tolerances"]["btlinklost_equipment_gap_minutes"])
    bad["BTLinkLostWithin5min"] = [bool(len(bt) and ((bt["AccountID"] == r["AccountID"]) &
                                                     ((bt["CreateDate"] - r["CreateDate"]).abs() <= win)).any())
                                   for r in bad.to_dict("records")]
    cols = [c for c in ["ID", "AccountID", "StoreID", "TransactionID", "Volume", "CreateDate", "Recnumber",
                        "BTLinkLostWithin5min"] if c in bad.columns]
    for acc, g in bad.groupby("AccountID"):
        stores = sorted({str(s) for s in g.get("StoreID", pd.Series(dtype=str)).dropna()})
        out.append(F("C15", "Monitor", acc, "Missing EquipmentID",
                     f"{len(g)} dispensing row(s) ({num(g['Volume']).sum():.2f} L) with EquipmentID 0/NULL on "
                     f"StoreID {', '.join(stores)}; {int(g['BTLinkLostWithin5min'].sum())} within 5 min of a BTLinkLost "
                     "event on the account (plausible cause: link dropped before the tag was captured). Fuel cannot "
                     "be allocated to a vehicle.", affected=f"{num(g['Volume']).sum():.2f} L / {len(g)} rows",
                     litres=num(g["Volume"]).sum(), count=len(g), evidence=g[cols]))
    return out


# ----------------------------------------------------------------------------
# C16 NoFlow stop without completion
# ----------------------------------------------------------------------------
def check_noflow(d, cfg):
    out = []
    nf = notif_entries(d)
    if not len(nf):
        return out
    nof = nf[((nf["EntryType"] == 3) | (num(nf["RowTypeID"]) == 3)) & nf["TrId"].notna()]
    nof = nof[(nof["CreateDate"] >= d.window_start) & (nof["CreateDate"] < d.window_end)]
    done = set(nf[(nf["EntryType"] == 124) | (num(nf["RowTypeID"]) == 124)]["TrId"].dropna().astype(str))
    canon = set(d.disp["TransactionID"].astype(str)) if not empty(d.disp) and "TransactionID" in d.disp.columns else set()
    orphan = nof[~nof["TrId"].astype(str).isin(done)].copy()
    if not len(orphan):
        return out
    orphan["InUsageDispensing"] = orphan["TrId"].astype(str).isin(canon)
    for acc, g in orphan.groupby("AccountID"):
        lost = int((~g["InUsageDispensing"]).sum())
        out.append(F("C16", "Investigate" if lost else "Monitor", acc, "NoFlow stop without completion",
                     f"{len(g)} NoFlow stop(s) with no DispTransactionComplete for the same TrId on devices "
                     f"{sorted(set(g['Device'].dropna().astype(str)))}; {lost} of those TrIds are also absent from "
                     "UsageDispensing. Possible cause: transaction aborted or record lost after a no-flow stop.",
                     affected=f"{len(g)} TrIds ({lost} not recorded)", count=len(g), evidence=g))
    return out


# ----------------------------------------------------------------------------
# C17 telemetry gaps / devices or accounts that stopped reporting
# fams-integrity investigation/networking.md
# ----------------------------------------------------------------------------
def check_telemetry_gaps(d, cfg, client_accounts):
    out = []
    gap_min = cfg["tolerances"]["telemetry_gap_minutes"]
    for label, df, unit_cols in (("Stock", d.stock, ["StoreID", "TankID"]), ("IOTData_ATG", d.atg, ["DeviceID"])):
        w = in_window(df, d)
        if df is None:
            continue
        units = [c for c in unit_cols if c in df.columns]
        if not units:
            continue
        rows = []
        if not empty(w):
            for k, g in w.groupby(["AccountID"] + units):
                t = g["CreateDate"].sort_values()
                edges = pd.concat([pd.Series([d.window_start]), t, pd.Series([d.window_end])]).reset_index(drop=True)
                diffs = edges.diff().dt.total_seconds() / 60
                for j in np.where(diffs > gap_min)[0]:
                    rows.append({"Table": label, "AccountID": k[0], "Unit": " | ".join(str(x) for x in k[1:]),
                                 "GapStart": edges[j - 1], "GapEnd": edges[j], "GapMinutes": round(diffs[j], 1)})
        if rows:
            ev = pd.DataFrame(rows)
            for acc, g in ev.groupby("AccountID"):
                out.append(F("C17", "Monitor", acc, f"Telemetry gap ({label})",
                             f"{len(g)} gap(s) longer than {gap_min} min in {label} across {g['Unit'].nunique()} "
                             f"unit(s); longest {g['GapMinutes'].max():.0f} min ({g.loc[g['GapMinutes'].idxmax(), 'GapStart']} "
                             f"to {g.loc[g['GapMinutes'].idxmax(), 'GapEnd']}). Readings in these spans are "
                             "unverifiable; any reconciliation shortfall overlapping them may be an outage, not a loss.",
                             affected=f"{len(g)} gaps, max {g['GapMinutes'].max():.0f} min", count=len(g), evidence=g))
        # stopped reporting: seen in lookback, silent for the whole window
        lb = getattr(d, "lookback_slim", {}).get(label)
        if lb is not None and len(lb) and all(u in lb.columns for u in units):
            seen = set(map(tuple, lb[["AccountID"] + units].drop_duplicates().astype(str).values))
            now = set(map(tuple, w[["AccountID"] + units].drop_duplicates().astype(str).values)) if not empty(w) else set()
            gone = sorted(seen - now)
            by_acc = defaultdict(list)
            for g in gone:
                last = lb[(lb[["AccountID"] + units].astype(str) == list(g)).all(axis=1)]["CreateDate"].max()
                by_acc[int(float(g[0]))].append({"Table": label, "Unit": " | ".join(g[1:]), "LastSeen": last})
            for acc, rows2 in by_acc.items():
                out.append(F("C17", "Investigate", acc, f"Stopped reporting ({label})",
                             f"{len(rows2)} unit(s) reported during the {cfg['lookback_hours']}h before the window but "
                             "sent nothing for the whole window. Possible cause: device offline/power/connectivity; "
                             "tank levels for these units are stale, not empty.",
                             affected=f"{len(rows2)} units", count=len(rows2), evidence=pd.DataFrame(rows2)))
    # whole-account silence
    tables = {"UsageDispensing": d.disp, "UsageDispensingIOT": d.iot, "UsageDispensingAndroid": d.android,
              "IOTData_FMS": d.fms, "IOTData_ATG": d.atg, "IOTData_Notification": d.notif, "Stock": d.stock}
    for acc in client_accounts:
        win_rows = sum(int((in_window(t, d)["AccountID"] == acc).sum()) for t in tables.values()
                       if not empty(t) and "AccountID" in t.columns)
        if win_rows:
            continue
        lb_rows = sum(int((t["AccountID"] == acc).sum()) for t in tables.values()
                      if not empty(t) and "AccountID" in t.columns)
        lb_rows += sum(int((t["AccountID"] == acc).sum()) for t in getattr(d, "lookback_slim", {}).values()
                       if t is not None and "AccountID" in t.columns)
        out.append(F("C17", "Investigate" if lb_rows else "Monitor", acc, "No data in window",
                     "No rows at all in any dispensing or telemetry table for the whole window" +
                     (" although the account reported before it - possible site-wide outage."
                      if lb_rows else " or the lookback period - confirm the account is still active."),
                     affected="0 rows", count=0))
    return out


# ----------------------------------------------------------------------------
# C18 tank reconciliation (Stock), C19 erratic telemetry, C20 store variance
# fams-integrity investigation/tank.md; fams-daily-report tank_analysis
# ----------------------------------------------------------------------------
def tank_reconciliation(d, cfg, disp_classified):
    out, tanks, stores = [], [], []
    t = cfg["tolerances"]
    w = in_window(d.stock, d)
    if empty(w) or not has(w, "TankID", "Volume", "CreateDate"):
        return out, pd.DataFrame(), pd.DataFrame()
    w = w.copy()
    w["Volume"] = num(w["Volume"])
    if "StoreID" not in w.columns:
        w["StoreID"] = np.nan
    for (acc, store, tank), g in w.sort_values("CreateDate").groupby(["AccountID", "StoreID", "TankID"], dropna=False):
        g = g.reset_index(drop=True)
        v = g["Volume"].values
        cap = float((g["Volume"] + num(g["Ullage"])).median()) if "Ullage" in g.columns else float(np.nanmax(v))
        jumps = np.diff(v)
        deliveries = [(g.at[k + 1, "CreateDate"], float(jumps[k])) for k in np.where(jumps > t["delivery_jump_litres"])[0]]
        # decline per segment between deliveries (first reading minus segment minimum)
        cuts = [0] + [k + 1 for k in np.where(jumps > t["delivery_jump_litres"])[0]] + [len(v)]
        decline = sum(max(0.0, v[a] - np.nanmin(v[a:b])) for a, b in zip(cuts, cuts[1:]) if b > a)
        roll = pd.Series(v).rolling(12, min_periods=6).std()
        erratic = bool((roll > t["noise_stdev_litres"]).any())
        over = bool("Ullage" in g.columns and (num(g["Ullage"]) < 0).any())
        tanks.append({"AccountID": acc, "StoreID": store, "TankID": tank, "Readings": len(g),
                      "Capacity_L_est": round(cap, 1), "Opening_L": round(v[0], 1), "Opening_Time": g.at[0, "CreateDate"],
                      "Closing_L": round(v[-1], 1), "Closing_Time": g.at[len(g) - 1, "CreateDate"],
                      "Min_L": round(float(np.nanmin(v)), 1), "Max_L": round(float(np.nanmax(v)), 1),
                      "ClosingPctFull": round(v[-1] / cap * 100, 1) if cap else None,
                      "Deliveries": len(deliveries), "Delivered_L_est": round(sum(x for _, x in deliveries), 1),
                      "Decline_L": round(decline, 1), "ErraticTelemetry": erratic, "NegativeUllage": over})
        if erratic:
            idx = np.where(roll > t["noise_stdev_litres"])[0]
            out.append(F("C19", "Monitor", acc, "ATG telemetry noise",
                         f"Tank {tank} (store {store}) readings oscillated beyond {t['noise_stdev_litres']} L rolling "
                         f"stdev between {g.at[idx[0], 'CreateDate']} and {g.at[idx[-1], 'CreateDate']} - reduces "
                         "confidence in this tank's volumes; a probe/data-quality signal, not a confirmed event.",
                         affected=f"Tank {tank}", tank=str(tank),
                         window=f"{g.at[idx[0], 'CreateDate']} to {g.at[idx[-1], 'CreateDate']}"))
        if over:
            out.append(F("C19", "Monitor", acc, "Tank reading above capacity",
                         f"Tank {tank} (store {store}) reported negative ullage (volume above capacity) - sensor or "
                         "configuration issue.", affected=f"Tank {tank}", tank=str(tank)))
    tanks_df = pd.DataFrame(tanks)
    # store-level variance: tank decline vs dispensed + transferred out
    disp = disp_classified if disp_classified is not None and len(disp_classified) else pd.DataFrame(columns=["AccountID", "StoreID", "Volume"])
    xfer = in_window(d.transfer, d)
    for (acc, store), tg in tanks_df.groupby(["AccountID", "StoreID"], dropna=False):
        dsp = float(num(disp[(disp["AccountID"] == acc) & (disp["StoreID"] == store)]["Volume"]).clip(lower=0).sum())
        xf = float(num(xfer[(xfer["AccountID"] == acc) & (xfer["StoreID"] == store)]["Volume"]).sum()) \
            if not empty(xfer) and has(xfer, "StoreID", "Volume") else 0.0
        dec = float(tg["Decline_L"].sum())
        cap = float(tg["Capacity_L_est"].sum())
        unexpl = dec - dsp - xf
        thr = min(t["material_loss_litres"], cap * t["material_loss_pct_of_capacity"] / 100) if cap else t["material_loss_litres"]
        base = max(dec, dsp + xf, 1.0)
        pct = unexpl / base * 100
        stores.append({"AccountID": acc, "StoreID": store, "Tanks": len(tg), "TankDecline_L": round(dec, 1),
                       "Dispensed_L": round(dsp, 1), "TransferredOut_L": round(xf, 1),
                       "Unexplained_L": round(unexpl, 1), "VariancePct": round(pct, 2), "MaterialThreshold_L": round(thr, 1),
                       "ErraticTelemetry": bool(tg["ErraticTelemetry"].any())})
        if unexpl >= thr and pct > t["volume_tolerance_pct"]:
            status = "Monitor" if tg["ErraticTelemetry"].any() else "Investigate"
            out.append(F("C18", status, acc, "Possible unexplained fuel loss",
                         f"Store {store}: tanks declined {dec:.0f} L (deliveries excluded) but only {dsp + xf:.0f} L was "
                         f"dispensed/transferred - {unexpl:.0f} L ({pct:.1f}%) unexplained, above the {thr:.0f} L "
                         "materiality threshold. Unconfirmed: possible unexplained fuel loss, possible unrecorded "
                         "dispensing, or a tank-to-store mapping error" +
                         (" - downgraded to Monitor because this store's telemetry was erratic" if status == "Monitor" else "") +
                         ". Needs field verification (physical dip, meter readings).",
                         affected=f"{unexpl:.0f} L", litres=unexpl, store=str(store),
                         evidence=tg))
        elif -unexpl >= thr and -pct > t["volume_tolerance_pct"]:
            out.append(F("C18", "Monitor", acc, "Dispensed exceeds tank decline",
                         f"Store {store}: {dsp + xf:.0f} L dispensed/transferred but tanks only declined {dec:.0f} L. "
                         "Possible causes: a delivery smaller than the detection threshold, meter over-reading, or "
                         "dispensing from a tank without ATG.", affected=f"{-unexpl:.0f} L", litres=-unexpl,
                         store=str(store), evidence=tg))
    return out, tanks_df, pd.DataFrame(stores)


# ----------------------------------------------------------------------------
# C20 communication health (IOTData_Error) with near-empty downgrade
# ----------------------------------------------------------------------------
def check_comm_health(d, cfg):
    out = []
    w = in_window(d.err, d)
    if empty(w) or "DeviceID" not in w.columns:
        return out
    tol, ne = cfg["tolerances"]["comm_error_tolerance"], cfg["tolerances"]["near_empty_tank_litres"]
    for (acc, dev), g in w.groupby(["AccountID", "DeviceID"]):
        if len(g) <= tol:
            continue
        med = float(num(g["Vol"]).median()) if "Vol" in g.columns else np.nan
        if not np.isnan(med) and med <= ne:
            out.append(F("C20", "Monitor", acc, "Communication errors explained by near-empty tank",
                         f"{len(g)} errors (tolerance {tol}) but tank volume during them was a flat ~{med:.1f} L - the "
                         "known near-empty-tank pattern, not a device fault. Check the refill schedule instead.",
                         affected=f"{dev}: {len(g)} errors", count=len(g), device=str(dev), evidence=g))
        else:
            out.append(F("C20", "Investigate", acc, "Communication failure",
                         f"Device {dev} logged {len(g)} errors, above the {tol}-per-window tolerance. Messages: "
                         f"{sorted(set(g['Message'].astype(str)))[:3] if 'Message' in g.columns else 'n/a'}. "
                         "Recommend a device health/connectivity check.",
                         affected=f"{dev}: {len(g)} errors", count=len(g), device=str(dev), evidence=g))
    return out


# ----------------------------------------------------------------------------
# C21 Transfer/Receiving vs ATG telemetry
# fams-integrity algorithms/atg-reconciliation.md (anchor via Notification TrId, not fillTrId)
# ----------------------------------------------------------------------------
def check_transfer_receiving_atg(d, cfg):
    out = []
    nf = notif_entries(d)
    if not len(nf) or empty(d.atg) or "TelementryData" not in d.atg.columns:
        return out
    ev = []
    for r in d.atg.to_dict("records"):
        if num(pd.Series([r.get("TypeID")]))[0] not in (2, 3, 4, 5):
            continue
        for e in tele_entries(r.get("TelementryData")):
            if get_ci(e, "strtVol") is not None and get_ci(e, "endVol") is not None:
                ev.append({"device": device_of(r), "fillTrId": get_ci(e, "fillTrId"),
                           "strtTime": pd.to_datetime(get_ci(e, "strtTime"), errors="coerce"),
                           "strtVol": num(pd.Series([get_ci(e, "strtVol")]))[0],
                           "endVol": num(pd.Series([get_ci(e, "endVol")]))[0]})
    if not ev:
        return out
    fill = pd.DataFrame(ev)
    tol = cfg["tolerances"]["volume_tolerance_pct"]
    mwin = pd.Timedelta(minutes=cfg["tolerances"]["transfer_atg_match_minutes"])
    anchors = nf[nf["TrId"].notna()]
    rows = []
    for label, tbl in (("UsageTransfer", d.transfer), ("UsageReceiving", d.receiving)):
        w = in_window(tbl, d)
        if empty(w) or not has(w, "TransactionID", "Volume"):
            continue
        for r in w.to_dict("records"):
            m = anchors[anchors["TrId"].astype(str) == str(r["TransactionID"])]
            if not len(m):
                continue
            a = m[m["EntryType"] == 125]
            a = (a if len(a) else m).iloc[0]
            c = fill[fill["device"] == a["Device"]] if a["Device"] else fill
            c = c.assign(delta=(c["strtTime"] - a["CreateDate"]).abs())
            c = c[c["delta"] <= mwin].sort_values("delta")
            logged = float(num(pd.Series([r["Volume"]]))[0])
            base = {"Table": label, "AccountID": r.get("AccountID"), "ID": r.get("ID"),
                    "TransactionID": r["TransactionID"], "CreateDate": r.get("CreateDate"),
                    "Device": a["Device"], "Logged_L": logged}
            if not len(c):
                rows.append({**base, "Result": "unverified"})
                continue
            b = c.iloc[0]
            atg_v = float(b["endVol"] - b["strtVol"])
            pct = abs(atg_v - abs(logged)) / abs(logged) * 100 if logged else None
            rows.append({**base, "ATG_L": round(atg_v, 1), "PctDiff": None if pct is None else round(pct, 2),
                         "ATGFillTrId": b["fillTrId"],
                         "Result": "mismatch" if pct is not None and pct > tol else "match"})
    if not rows:
        return out
    ev = pd.DataFrame(rows)
    for acc, g in ev.groupby("AccountID"):
        mm, un = g[g["Result"] == "mismatch"], g[g["Result"] == "unverified"]
        if len(mm):
            out.append(F("C21", "Investigate", acc, "Transfer/receiving volume disagrees with ATG",
                         f"{len(mm)} transfer/receiving record(s) differ from the tank-measured fill/drop by more than "
                         f"{tol}%. Record book and tank telemetry disagree on how much fuel moved - verify against the "
                         "delivery note / dip. (The ATG fillTrId differing from the TransactionID is a known, separate "
                         "ID-scheme issue, not this finding.)", affected=f"{len(mm)} records", count=len(mm), evidence=mm))
        if len(un):
            out.append(F("C21", "Monitor", acc, "Transfer/receiving not verifiable against ATG",
                         f"{len(un)} record(s) anchored to a notification but with no ATG fill/drop event within "
                         f"{cfg['tolerances']['transfer_atg_match_minutes']} min - logged volume unverified (not clean).",
                         affected=f"{len(un)} records", count=len(un), evidence=un))
    return out


# ----------------------------------------------------------------------------
# C22 raw payload errors (TempTableDataJson.errorid != 0)
# ----------------------------------------------------------------------------
def check_payload_errors(d, cfg):
    out = []
    t = d.tempjson
    if empty(t) or empty(d.stores) or not has(d.stores, "Macaddress", "AccountID"):
        return out
    mac_acc = dict(zip(d.stores["Macaddress"].astype(str), d.stores["AccountID"]))
    t = t.assign(AccountID=t["Macaddress"].astype(str).map(mac_acc))
    for acc, g in t.groupby("AccountID"):
        out.append(F("C22", "Monitor", acc, "Raw payload errors",
                     f"{len(g)} inbound device payload(s) flagged errorid != 0 on "
                     f"{g['Macaddress'].nunique()} device(s). These transactions may not have decoded into FAMS.",
                     affected=f"{len(g)} payloads", count=len(g), evidence=g))
    return out


# ----------------------------------------------------------------------------
# C23 volume outliers per equipment (IQR, skew-safe)
# ----------------------------------------------------------------------------
def check_outliers(d, cfg):
    out = []
    if empty(d.disp) or "EquipmentID" not in d.disp.columns:
        return out
    k, minh = cfg["tolerances"]["outlier_iqr_multiplier"], cfg["tolerances"]["outlier_min_history"]
    df = d.disp[(num(d.disp["Volume"]) > 0) & (num(d.disp["EquipmentID"]).fillna(0) > 0)].copy()
    df["Volume"] = num(df["Volume"])
    flagged = defaultdict(list)
    for (acc, eq), g in df.groupby(["AccountID", "EquipmentID"]):
        if len(g) < minh:
            continue
        q1, q3 = g["Volume"].quantile([0.25, 0.75])
        hi = q3 + k * (q3 - q1)
        w = g[(g["CreateDate"] >= d.window_start) & (g["CreateDate"] < d.window_end) & (g["Volume"] > hi)]
        if len(w):
            flagged[(acc, int(eq) in acct_cfg_ids(cfg, "known_benign_outlier_equipment_ids", acc))].append(
                w.assign(UpperFence_L=round(hi, 1), Median_L=round(g["Volume"].median(), 1)))
    cols = ["ID", "AccountID", "StoreID", "EquipmentID", "TransactionID", "Volume", "CreateDate", "UpperFence_L", "Median_L"]
    for (acc, benign), parts in flagged.items():
        ev = pd.concat(parts)
        ev = ev[[c for c in cols if c in ev.columns]]
        if benign:
            out.append(F("C23", "No action required", acc, "Known benign volume outlier",
                         f"{len(ev)} large transaction(s) on equipment confirmed as long-tailed/benign "
                         "(e.g. Bridgeport 36941).", count=len(ev), evidence=ev))
        else:
            out.append(F("C23", "Monitor", acc, "Volume outlier",
                         f"{len(ev)} transaction(s) on {ev['EquipmentID'].nunique()} equipment unit(s) far above that "
                         f"unit's own history (Q3 + {k}xIQR). Possible causes: different vehicle class on the same tag, "
                         "or a mis-tagged fill.", count=len(ev), litres=ev["Volume"].sum(),
                         affected=f"{len(ev)} txns", evidence=ev))
    return out


# ----------------------------------------------------------------------------
# C24 allocation / cost-centre referential integrity
# ----------------------------------------------------------------------------
def check_fk(d, cfg):
    out = []
    for key, label, note in (
            ("allocation", "Allocation unresolved/undescribed",
             "dispensing row(s) point at an Allocation (Operation/Location) that does not exist or has no "
             "description - a data-setup gap that also affects SARS allocation reporting."),
            ("cost_centre", "Cost centre unresolved",
             "dispensing row(s) carry an EquipmentCostCentreID that does not resolve to an EquipmentCostCentre row.")):
        df = (d.fk or {}).get(key)
        if empty(df):
            continue
        for acc, g in df.groupby("AccountID"):
            out.append(F("C24", "Monitor", acc, label, f"{len(g)} {note}", affected=f"{len(g)} rows",
                         count=len(g), evidence=g))
    return out


# ----------------------------------------------------------------------------
# C25 IOT raw-to-decoded gap: IOTData_FMS dispensing record not decoded
# IOTData_FMS is the raw IOT stream. Each dispensing record (TypeID 1) is decoded
# into UsageDispensingIOT (backup) and into UsageDispensing (source of truth) when
# the transaction isn't already there. Searched across the whole fetched range.
# ----------------------------------------------------------------------------
def check_fms_decode(d, cfg):
    out = []
    w = in_window(d.fms, d)
    if empty(w) or not has(w, "AccountID", "TransactionID", "TypeID"):
        return out
    grace = pd.Timedelta(minutes=cfg["tolerances"].get("decode_grace_minutes", 30))
    w = w[(num(w["TypeID"]) == 1) & valid_id(w["TransactionID"]) & (w["CreateDate"] < d.window_end - grace)]
    if empty(w):
        return out
    k = lambda df: set(zip(df["AccountID"].astype("Int64"), df["TransactionID"].astype(str))) \
        if has(df, "AccountID", "TransactionID") else set()  # noqa: E731
    iot_k, ud_k = k(d.iot), k(d.disp)
    ud_vol = {} if empty(d.disp) else d.disp.assign(V=num(d.disp["Volume"])).groupby(
        [d.disp["AccountID"].astype("Int64"), d.disp["TransactionID"].astype(str)])["V"].sum().to_dict()
    keys = list(zip(w["AccountID"].astype("Int64"), w["TransactionID"].astype(str)))
    w = w.assign(InUsageDispensingIOT=[x in iot_k for x in keys], InUsageDispensing=[x in ud_k for x in keys],
                 UsageDispensingVolume=[ud_vol.get(x) for x in keys])
    w = w.drop_duplicates(["AccountID", "TransactionID"])
    cols = [c for c in ["ID", "AccountID", "DeviceId", "DeviceID", "TransactionID", "TypeID", "CreateDate",
                        "InUsageDispensingIOT", "InUsageDispensing", "UsageDispensingVolume"] if c in w.columns]
    both = w[~w["InUsageDispensingIOT"] & ~w["InUsageDispensing"]]
    for acc, g in both.groupby("AccountID"):
        out.append(F("C25", "Investigate", acc, "Raw IOT dispensing not decoded (missing from UsageDispensing)",
                     f"{len(g)} IOTData_FMS dispensing record(s) (TypeID 1) have no UsageDispensingIOT row and no "
                     "UsageDispensing row for the same TransactionID (searched across the whole fetched range). The "
                     "decoder should have written them to both, so this dispensing is missing from client reporting. "
                     "Possible cause: decode/processing failure. Check the raw TelementryData for the volume.",
                     affected=f"{len(g)} txns", count=len(g), evidence=g[cols]))
    only_iot = w[~w["InUsageDispensingIOT"] & w["InUsageDispensing"]]
    for acc, g in only_iot.groupby("AccountID"):
        lit = pd.to_numeric(g["UsageDispensingVolume"], errors="coerce").sum()
        out.append(F("C25", "Monitor", acc, "Raw IOT dispensing not decoded into UsageDispensingIOT",
                     f"{len(g)} IOTData_FMS dispensing record(s) are in UsageDispensing (source of truth, "
                     f"{lit:.2f} L) but have no UsageDispensingIOT backup row. Reporting is complete; the IOT backup "
                     "layer has a gap. Possible cause: IOT decode failure.",
                     affected=f"{lit:.2f} L / {len(g)} txns", count=len(g), evidence=g[cols]))
    return out


# ----------------------------------------------------------------------------
# C26 Android raw-to-truth gap: TempTableDataJson payload never reached UsageDispensing
# For accounts with Android devices (config android_accounts) TempTableDataJson holds
# the raw payloads behind UsageDispensing. A payload with a TransactionID that is in
# none of UsageDispensing / UsageTransfer / UsageReceiving (whole fetched range) is
# dispensing missing from client reporting.
# ----------------------------------------------------------------------------
def check_android_raw(d, cfg):
    out = []
    t = getattr(d, "tempjson_payloads", None)
    if empty(t) or empty(d.stores) or not has(d.stores, "Macaddress", "AccountID") or "TransactionID" not in t.columns:
        return out
    grace = pd.Timedelta(minutes=cfg["tolerances"].get("decode_grace_minutes", 30))
    mac_acc = dict(zip(d.stores["Macaddress"].astype(str), d.stores["AccountID"]))
    t = t.assign(AccountID=t["Macaddress"].astype(str).map(mac_acc))
    t = t[t["AccountID"].isin(getattr(d, "android_accounts", set())) & valid_id(t["TransactionID"])
          & (t["CreateDate"] < d.window_end - grace)]
    if "Volume" in t.columns:
        t = t.assign(Volume=num(t["Volume"]))
        t = t[~(t["Volume"] <= 0)]          # keep positive or unknown volume
    if empty(t):
        return out
    canon = set()
    for tbl in (d.disp, d.transfer, d.receiving):
        if not empty(tbl) and has(tbl, "AccountID", "TransactionID"):
            canon |= set(zip(tbl["AccountID"].astype("Int64"), tbl["TransactionID"].astype(str)))
    keys = list(zip(t["AccountID"].astype("Int64"), t["TransactionID"].astype(str)))
    miss = t[[k not in canon for k in keys]].drop_duplicates(["AccountID", "TransactionID"])
    cols = [c for c in ["ID", "AccountID", "Macaddress", "TransactionID", "Volume", "CreateDate"] if c in miss.columns]
    for acc, g in miss.groupby("AccountID"):
        lit = num(g["Volume"]).sum() if "Volume" in g.columns else 0.0
        out.append(F("C26", "Investigate", acc, "Android raw payload missing from UsageDispensing",
                     f"{len(g)} TempTableDataJson payload(s) (errorid 0) carry a TransactionID that is in none of "
                     "UsageDispensing / UsageTransfer / UsageReceiving (searched across the whole fetched range). "
                     "TempTableDataJson is the raw source behind UsageDispensing for this Android account, so this "
                     f"dispensing ({lit:.2f} L where the payload states a volume) is missing from client reporting. "
                     "Possible cause: processing failure after upload.",
                     affected=f"{lit:.2f} L / {len(g)} payloads", litres=lit, count=len(g), evidence=g[cols]))
    return out


# Fixed statement of the dispensing data lineage (Hennie, 2026-10-06). Written
# into findings.json; reports must print it as-is and never describe any other
# table as the source of truth.
SOURCE_HIERARCHY = [
    {"layer": "Source of truth", "table": "UsageDispensing", "covers": "Dispensing transactions",
     "note": "All dispensing figures in this report come from UsageDispensing."},
    {"layer": "Source of truth", "table": "UsageTransfer", "covers": "Transfers",
     "note": "Dispensing into a bowser or another tank."},
    {"layer": "Source of truth", "table": "UsageReceiving", "covers": "Receiving / offloading",
     "note": "All receiving and offloading transactions."},
    {"layer": "Source of truth", "table": "Stock", "covers": "Tank levels", "note": "All tank-level figures."},
    {"layer": "Backup", "table": "UsageDispensingAndroid", "covers": "Dispensing",
     "note": "From the Android control unit that links the Android device to the fuel pump."},
    {"layer": "Backup", "table": "UsageDispensingIOT", "covers": "Dispensing", "note": "From the IOT device."},
    {"layer": "Raw", "table": "TempTableDataJson", "covers": "Android dispensing",
     "note": "Raw Android payloads behind UsageDispensing; the main raw source for Android accounts."},
    {"layer": "Raw", "table": "IOTData_FMS", "covers": "IOT dispensing",
     "note": "Raw IOT dispensing records, decoded into UsageDispensingIOT and into UsageDispensing when the "
             "transaction is not already there."},
    {"layer": "Raw", "table": "IOTData_ATG", "covers": "Tank levels (IOT)", "note": "Raw IOT tank-level data."},
    {"layer": "Raw", "table": "IOTData_Notification", "covers": "Alerts", "note": "Raw IOT device alerts."},
    {"layer": "Raw", "table": "IOTData_Error", "covers": "Tank errors", "note": "Raw IOT tank errors."},
]

CHECK_REGISTRY = [
    ("C01", "Duplicate transactions (5 rules, grouped)", "fams-integrity algorithms/duplicate-detection.md"),
    ("C02", "TransactionID collision (same ID, different volume)", "fams-integrity algorithms/duplicate-detection.md"),
    ("C03", "Missing TransactionID (+ backfill candidate)", "fams-integrity anomaly-library/data-quality.md"),
    ("C04", "Unreconciled UnqTrID", "fams-integrity datasets/validation-rules.md"),
    ("C05", "InformationRec truncated/blank", "fams-integrity anomaly-library/data-quality.md"),
    ("C06", "UsageDispensing row with no backup record (IOT/Android) / outage / known offload", "fams-daily-report classify_dispensing"),
    ("C07", "Volume mismatch UsageDispensing vs backup (IOT/Android)", "fams-integrity algorithms/atg-reconciliation.md"),
    ("C08", "Backup record (IOT/Android) missing from UsageDispensing", "fams-integrity anomaly-library/transaction-integrity.md"),
    ("C09", "Unknown IOTData_FMS TypeID", "fams-daily-report business-rules.md"),
    ("C10", "Recnumber: manual-entry candidates, 4627x series", "fams-integrity anomaly-library/equipment-integrity.md"),
    ("C11", "ProductID / ProdID = 0", "new (2026-10)"),
    ("C12", "Totaliser flow continuity per nozzle", "fams-integrity business-rules/nozzle-validation.md"),
    ("C13", "Totaliser overflow sentinel / capture failure", "fams-integrity datasets/calculations.md"),
    ("C14", "BTLinkLost volume cross-check + concentration", "fams-integrity anomaly-library/device-integrity.md"),
    ("C15", "Missing EquipmentID (+ BTLinkLost co-occurrence)", "fams-integrity anomaly-library/data-quality.md"),
    ("C16", "NoFlow stop without completion", "fams-integrity investigation findings (Langpan/A4G)"),
    ("C17", "Telemetry gaps / stopped reporting / no data", "fams-integrity investigation/networking.md"),
    ("C18", "Store tank variance / possible fuel loss", "fams-integrity investigation/tank.md"),
    ("C19", "ATG telemetry noise / above capacity", "fams-daily-report tank_analysis"),
    ("C20", "Communication health (near-empty downgrade)", "fams-daily-report communication_health"),
    ("C21", "Transfer/Receiving vs ATG telemetry", "fams-integrity algorithms/atg-reconciliation.md"),
    ("C22", "Raw payload errors (TempTableDataJson)", "fams-integrity investigation/devices.md"),
    ("C23", "Volume outliers per equipment (IQR)", "fams-integrity algorithms/outlier-detection.md"),
    ("C24", "Allocation / cost-centre referential integrity", "fams-integrity business-rules/allocation-, cost-centre-validation.md"),
    ("C25", "Raw IOT dispensing (IOTData_FMS) not decoded into UsageDispensingIOT / UsageDispensing", "fams-database-core data lineage (2026-10)"),
    ("C26", "Android raw payload (TempTableDataJson) missing from UsageDispensing (Android accounts)", "fams-database-core data lineage (2026-10)"),
]
