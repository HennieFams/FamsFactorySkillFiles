"""
Data access for the daily integrity check.

Two interchangeable sources with the same interface:

  DbSource   - live FAMS database, every statement through fams_db.query_df()
               (read-only guard + always-rollback). Table/column names are
               checked against INFORMATION_SCHEMA before use, so a missing
               table or column becomes a recorded data gap, never a crash or
               a silently wrong query.
  DirSource  - a directory of per-table exports (<Table>.csv or <Table>.xlsx,
               any prefix), for manual/offline runs and for tests.

Every returned DataFrame has its column names normalised to one canonical
spelling (CANONICAL below) - e.g. UsageDispensing.Createdate and
IOTData_FMS.CreateDate both become CreateDate, ProdID becomes ProductID -
so the checks never have to care which table spelled a column which way.
"""
from __future__ import annotations

import glob
import os

import pandas as pd

CANONICAL = {c.lower(): c for c in [
    "ID", "AccountID", "StoreID", "EquipmentID", "ProductID", "TransactionID", "UnqTrID",
    "Volume", "OrigVolume", "CreateDate", "Recnumber", "InformationRec", "InformationMac",
    "TrailerMac", "Totalizer", "TotalizerEnd", "TotaliserStart", "TotaliserEnd",
    "TotaliserFromComms", "IOTData_FMSID", "DeviceID", "DeviceAlias", "TypeID", "RecordTypeID",
    "TelementryData", "TankID", "TankNr", "Ullage", "Vol", "Message", "StateInfo", "Macaddress",
    "ErrorID", "DeliveryNote", "InvoiceNr", "EqpTag", "AllocationID", "AllocationID2",
    "EquipmentCostCentreID", "Name", "EventTime", "UsageDispensingID",
]}
ALIASES = {"prodid": "ProductID", "productid": "ProductID", "deviceid": "DeviceID",
           "createdate": "CreateDate", "errorid": "ErrorID", "accountname": "Name"}

# table -> (account filter column, date column)
TABLES = {
    "UsageDispensing":        ("AccountID", "Createdate"),
    "UsageDispensingIOT":     ("AccountID", "Createdate"),
    "UsageDispensingAndroid": ("AccountID", "Createdate"),
    "IOTData_FMS":            ("AccountID", "CreateDate"),
    "IOTData_ATG":            ("AccountID", "CreateDate"),
    "IOTData_Notification":   ("AccountID", "CreateDate"),
    "IOTData_Error":          ("AccountID", "CreateDate"),
    "Stock":                  ("AccountID", "CreateDate"),
    "UsageTransfer":          ("AccountID", "Createdate"),
    "UsageReceiving":         ("AccountID", "Createdate"),
}


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return None
    rename, seen = {}, set()
    for c in df.columns:
        key = str(c).lower()
        canon = ALIASES.get(key) or CANONICAL.get(key) or str(c)
        if canon in seen:          # keep the first spelling if two map to one
            continue
        seen.add(canon)
        rename[c] = canon
    df = df[list(rename)].rename(columns=rename)
    if "CreateDate" in df.columns:
        df["CreateDate"] = pd.to_datetime(df["CreateDate"], errors="coerce")
    return df


class DbSource:
    kind = "database"

    def __init__(self):
        import fams_db  # noqa: F401  (import here so DirSource works without a driver)
        self.db = fams_db
        self._cols = {}

    def columns(self, table: str) -> list[str]:
        if table not in self._cols:
            df = self.db.query_df(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
                [table])
            self._cols[table] = list(df["COLUMN_NAME"]) if len(df) else []
        return self._cols[table]

    def _resolve(self, table, wanted):
        cols = {c.lower(): c for c in self.columns(table)}
        return [cols[w.lower()] for w in wanted if w.lower() in cols]

    def fetch(self, table, account_ids, start=None, end=None, columns=None, extra_where=None):
        """Rows for these accounts with start <= date < end. None if the table is absent."""
        acct_col, date_col = TABLES[table]
        avail = self.columns(table)
        if not avail:
            return None
        lower = {c.lower(): c for c in avail}
        if acct_col.lower() not in lower or date_col.lower() not in lower:
            return None
        sel = "*" if columns is None else ", ".join(f"[{c}]" for c in self._resolve(table, columns))
        sql = (f"SELECT {sel} FROM [{table}] WHERE [{lower[acct_col.lower()]}] IN "
               f"({', '.join('?' for _ in account_ids)})")
        params = [int(a) for a in account_ids]
        if start is not None:
            sql += f" AND [{lower[date_col.lower()]}] >= ?"
            params.append(start.to_pydatetime())
        if end is not None:
            sql += f" AND [{lower[date_col.lower()]}] < ?"
            params.append(end.to_pydatetime())
        if extra_where:
            sql += f" AND ({extra_where})"
        return normalise(self.db.query_df(sql, params))

    def stores(self, account_ids):
        if not self.columns("Store"):
            return None
        return normalise(self.db.query_df(
            f"SELECT * FROM [Store] WHERE [AccountID] IN ({', '.join('?' for _ in account_ids)})",
            [int(a) for a in account_ids]))

    def account_names(self, account_ids):
        cols = {c.lower(): c for c in self.columns("Account")}
        idc = cols.get("accountid") or cols.get("id")
        namec = cols.get("name") or cols.get("accountname")
        if not (idc and namec):
            return {}
        df = self.db.query_df(
            f"SELECT [{idc}] AS AccountID, [{namec}] AS Name FROM [Account] WHERE [{idc}] IN "
            f"({', '.join('?' for _ in account_ids)})", [int(a) for a in account_ids])
        return {int(r.AccountID): str(r.Name) for r in df.itertuples()}

    def temp_json_errors(self, macs, start, end):
        cols = {c.lower(): c for c in self.columns("TempTableDataJson")}
        if not macs or not {"macaddress", "createdate", "errorid"} <= set(cols):
            return None
        sql = (f"SELECT [{cols['macaddress']}], [{cols['createdate']}], [{cols['errorid']}] "
               f"FROM [TempTableDataJson] WHERE [{cols['macaddress']}] IN ({', '.join('?' for _ in macs)}) "
               f"AND [{cols['createdate']}] >= ? AND [{cols['createdate']}] < ? AND [{cols['errorid']}] <> 0")
        return normalise(self.db.query_df(sql, list(macs) + [start.to_pydatetime(), end.to_pydatetime()]))

    def temp_json_payloads(self, macs, start, end):
        """Android raw payloads (errorid = 0) with TransactionID/Volume extracted in SQL.
        The transactionID key spelling varies per account, so all three are tried."""
        cols = {c.lower(): c for c in self.columns("TempTableDataJson")}
        if not macs or not {"macaddress", "createdate", "jsondata"} <= set(cols):
            return None
        j = f"[{cols['jsondata']}]"
        jv = lambda path: f"JSON_VALUE({j}, '{path}')"  # noqa: E731
        tx = f"COALESCE({jv('$.transactionID')}, {jv('$.transactionId')}, {jv('$.TransactionID')})"
        vol = f"COALESCE({jv('$.DispensedVolume')}, {jv('$.Volume')})"
        idc = f"[{cols['id']}] AS ID, " if "id" in cols else ""
        sql = (f"SELECT {idc}[{cols['macaddress']}] AS Macaddress, [{cols['createdate']}] AS CreateDate, "
               f"CASE WHEN ISJSON({j}) = 1 THEN {tx} END AS TransactionID, "
               f"CASE WHEN ISJSON({j}) = 1 THEN {vol} END AS Volume "
               f"FROM [TempTableDataJson] WHERE [{cols['macaddress']}] IN ({', '.join('?' for _ in macs)}) "
               f"AND [{cols['createdate']}] >= ? AND [{cols['createdate']}] < ?")
        if "errorid" in cols:
            sql += f" AND ([{cols['errorid']}] = 0 OR [{cols['errorid']}] IS NULL)"
        return normalise(self.db.query_df(sql, list(macs) + [start.to_pydatetime(), end.to_pydatetime()]))

    def fk_checks(self, account_ids, start, end):
        """Allocation / cost-centre referential checks (business-rules/ in fams-integrity)."""
        out = {}
        ph = ", ".join("?" for _ in account_ids)
        base = [int(a) for a in account_ids] + [start.to_pydatetime(), end.to_pydatetime()]
        if self.columns("Allocation"):
            out["allocation"] = normalise(self.db.query_df(
                "SELECT u.ID, u.AccountID, u.StoreID, u.EquipmentID, u.TransactionID, u.Createdate, u.Volume, "
                "u.AllocationID, a1.ID AS Alloc1Found, a1.Description AS OperationDesc, "
                "u.AllocationID2, a2.ID AS Alloc2Found, a2.Description AS LocationDesc "
                "FROM UsageDispensing u "
                "LEFT JOIN Allocation a1 ON u.AllocationID = a1.ID "
                "LEFT JOIN Allocation a2 ON u.AllocationID2 = a2.ID "
                f"WHERE u.AccountID IN ({ph}) AND u.Createdate >= ? AND u.Createdate < ? "
                "AND ((u.AllocationID > 0 AND (a1.ID IS NULL OR a1.Description IS NULL OR a1.Description = '')) "
                "  OR (u.AllocationID2 > 0 AND (a2.ID IS NULL OR a2.Description IS NULL OR a2.Description = '')))",
                base))
        if self.columns("EquipmentCostCentre"):
            out["cost_centre"] = normalise(self.db.query_df(
                "SELECT u.ID, u.AccountID, u.StoreID, u.EquipmentID, u.TransactionID, u.Createdate, u.Volume, "
                "u.EquipmentCostCentreID FROM UsageDispensing u "
                "LEFT JOIN EquipmentCostCentre c ON u.EquipmentCostCentreID = c.ID "
                f"WHERE u.AccountID IN ({ph}) AND u.Createdate >= ? AND u.Createdate < ? "
                "AND u.EquipmentCostCentreID > 0 AND c.ID IS NULL", base))
        return out


class DirSource:
    """Per-table exports in a directory: <anything><Table>.csv|.xlsx."""
    kind = "directory"

    def __init__(self, path):
        self.path = path
        self._cache = {}

    def _load(self, table):
        if table in self._cache:
            return self._cache[table]
        df = None
        for ext in (".csv", ".xlsx"):
            hits = sorted(glob.glob(os.path.join(self.path, f"*{table}{ext}")))
            # avoid UsageDispensing matching UsageDispensingIOT etc.
            hits = [h for h in hits if os.path.basename(h)[: -len(ext)].endswith(table)]
            if hits:
                df = pd.read_csv(hits[0]) if ext == ".csv" else pd.read_excel(hits[0])
                break
        self._cache[table] = normalise(df) if df is not None else None
        return self._cache[table]

    def fetch(self, table, account_ids, start=None, end=None, columns=None, extra_where=None):
        df = self._load(table)
        if df is None:
            return None
        if "AccountID" in df.columns:
            df = df[df["AccountID"].isin([int(a) for a in account_ids])]
        if "CreateDate" in df.columns:
            if start is not None:
                df = df[df["CreateDate"] >= start]
            if end is not None:
                df = df[df["CreateDate"] < end]
        if columns is not None:
            keep = [c for c in df.columns if c.lower() in {x.lower() for x in columns}
                    or c in {ALIASES.get(x.lower(), x) for x in columns}]
            df = df[keep]
        return df.copy()

    def stores(self, account_ids):
        df = self._load("Store")
        return None if df is None else df[df["AccountID"].isin([int(a) for a in account_ids])].copy()

    def account_names(self, account_ids):
        df = self._load("Account")
        if df is None or "Name" not in df.columns:
            return {}
        idc = "AccountID" if "AccountID" in df.columns else "ID"
        return {int(r[idc]): str(r["Name"]) for _, r in df.iterrows() if int(r[idc]) in {int(a) for a in account_ids}}

    def temp_json_errors(self, macs, start, end):
        df = self._load("TempTableDataJson")
        if df is None or not {"Macaddress", "CreateDate", "ErrorID"} <= set(df.columns):
            return None
        return df[df["Macaddress"].isin(macs) & (df["CreateDate"] >= start) & (df["CreateDate"] < end)
                  & (df["ErrorID"] != 0)].copy()

    def temp_json_payloads(self, macs, start, end):
        df = self._load("TempTableDataJson")
        if df is None or not {"Macaddress", "CreateDate"} <= set(df.columns):
            return None
        df = df[df["Macaddress"].isin(macs) & (df["CreateDate"] >= start) & (df["CreateDate"] < end)].copy()
        if "ErrorID" in df.columns:
            df = df[df["ErrorID"].fillna(0) == 0]
        if "Jsondata" in df.columns and "TransactionID" not in df.columns:
            import json as _json

            def pick(raw, keys):
                try:
                    o = _json.loads(raw)
                except Exception:
                    return None
                return next((o[k] for k in keys if isinstance(o, dict) and o.get(k) is not None), None)
            df["TransactionID"] = df["Jsondata"].map(lambda r: pick(r, ["transactionID", "transactionId", "TransactionID"]))
            df["Volume"] = df["Jsondata"].map(lambda r: pick(r, ["DispensedVolume", "Volume"]))
        return df

    def fk_checks(self, account_ids, start, end):
        return {}
