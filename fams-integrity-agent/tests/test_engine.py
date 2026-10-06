"""
End-to-end tests for the daily check engine on a synthetic export set.

Every planted problem must be found with the right check/status, and the
known false-positive traps (N/A UnqTrID grouping, non-comms totaliser
starts, interleaved nozzles, near-empty comm errors) must NOT fire.

Run:  python -m pytest -q fams-integrity-agent/tests
"""
import copy
import json
import os
import sys

import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
CONFIG = os.path.join(os.path.dirname(HERE), "config", "config.json")
sys.path.insert(0, SCRIPTS)

import run_checks
import integrity_checks as ic  # noqa: E402
from fams_sources import DirSource  # noqa: E402

ACC = 9001
RUN = pd.Timestamp("2026-10-02 06:30", tz="Africa/Johannesburg")
W0 = pd.Timestamp("2026-09-30 06:00")          # window start (06:00 boundary)
T = lambda h, m=0, s=0: W0 + pd.Timedelta(hours=h, minutes=m, seconds=s)  # noqa: E731


def base_cfg():
    with open(CONFIG) as fh:
        cfg = json.load(fh)
    cfg = copy.deepcopy(cfg)
    cfg["clients"] = [{"name": "Test Client (PTY) LTD", "short": "TestCo", "boundary_hour_sast": 6,
                       "accounts": {str(ACC): "Test Depot", "9002": "Quiet Depot"}}]
    return cfg


def disp_row(i, tx, vol, t, eq=500, unq=None, rec="importFams", store=10, prod=1, mac="AABBCCDDEEFF"):
    return {"ID": i, "AccountID": ACC, "StoreID": store, "EquipmentID": eq, "ProductID": prod, "Volume": vol,
            "Createdate": t, "TransactionID": tx, "UnqTrID": unq if unq is not None else tx, "Recnumber": rec,
            "InformationMac": mac, "InformationRec": json.dumps({"transactionID": tx})}


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    p = tmp_path_factory.mktemp("exports")
    disp, android, iot, fms = [], [], [], []
    # nozzle A: continuous totaliser chain with ONE planted skip (T03 end 1100 -> T04 start 1150)
    tot = 1000.0
    for n in range(1, 9):
        tx = f"TXA{n:02d}"
        vol = 50.0
        t = T(2 * n)
        start = tot + (50.0 if n == 4 else 0.0)
        disp.append(disp_row(100 + n, tx, vol, t))
        android.append({"ID": 700 + n, "AccountID": ACC, "StoreID": 10, "ProductID": 1, "TrailerMac": "T1",
                        "InformationMac": "AABBCCDDEEFF", "TransactionID": tx, "Volume": vol, "Createdate": t,
                        "Totalizer": start, "TotalizerEnd": start + vol})
        tot = start + vol
    # nozzle B (same controller, other hose): its own continuous chain - must not interleave with A
    tot = 5000.0
    for n in range(1, 6):
        tx = f"TXB{n:02d}"
        t = T(2 * n, 30)
        disp.append(disp_row(200 + n, tx, 20.0, t, eq=501))
        android.append({"ID": 800 + n, "AccountID": ACC, "StoreID": 10, "ProductID": 1, "TrailerMac": "T2",
                        "InformationMac": "AABBCCDDEEFF", "TransactionID": tx, "Volume": 20.0, "Createdate": t,
                        "Totalizer": tot, "TotalizerEnd": tot + 20.0})
        tot += 20.0
    # IOT device: break on a NON-comms start (must be ignored) and a real comms break of 30 L
    iot_rows = [("IOT1", 0, 2000.0, 40.0, 1), ("IOT2", 1, 2040.0, 40.0, 1), ("IOT3", 2, 2500.0, 40.0, 0),
                ("IOT4", 3, 2570.0, 40.0, 1)]
    for k, (tx, h, s, v, comms) in enumerate(iot_rows):
        t = T(30 + h)
        disp.append(disp_row(300 + k, tx, v, t, eq=600, mac="112233445566"))
        iot.append({"ID": 900 + k, "AccountID": ACC, "IOTData_FMSID": 950 + k, "TransactionID": tx,
                    "DeviceID": "112233445566", "ProductID": 1, "TypeID": 1, "Volume": v, "Createdate": t,
                    "TotaliserStart": s, "TotaliserEnd": s + v})
        fms.append({"ID": 950 + k, "AccountID": ACC, "TransactionID": tx, "DeviceId": "112233445566", "TypeID": 1,
                    "CreateDate": t, "TotaliserFromComms": comms, "TelementryData": json.dumps({"TelementryData": [{"prodId": 1}]})})
    # duplicates: known dual-write (same TX, 10 s apart, 4627x + importFams)
    disp.append(disp_row(400, "68B6B33CE0186AA38F90", 900.0, T(5), eq=29307, rec="46275"))
    disp.append(disp_row(401, "68B6B33CE0186AA38F90", 900.0, T(5, 0, 10), eq=29307, rec="importFams"))
    # new duplicate with garbage IDs, same equipment + volume 30 s apart
    disp.append(disp_row(402, "DUPX1", 77.7, T(6), eq=700, unq="N/A"))
    disp.append(disp_row(403, "DUPX2", 77.7, T(6, 0, 30), eq=700, unq="N/A"))
    # trap: N/A UnqTrID, same equipment+volume, far apart -> NOT a duplicate
    disp.append(disp_row(404, "NAX1", 60.0, T(7), eq=701, unq="N/A"))
    disp.append(disp_row(405, "NAX2", 60.0, T(20), eq=701, unq="N/A"))
    # TransactionID collision (different volumes)
    disp.append(disp_row(406, "COLL1", 10.0, T(8), eq=702))
    disp.append(disp_row(407, "COLL1", 99.0, T(9), eq=703))
    # missing TransactionID, ProductID 0, manual entry, missing equipment, unexplained
    disp.append(disp_row(408, None, 33.0, T(10), eq=704, unq="N/A"))
    disp[-1]["InformationRec"] = json.dumps({"transactionId": "RECOVER1"})
    disp.append(disp_row(409, "PROD0", 25.0, T(11), eq=705, prod=0))
    disp.append(disp_row(410, "MAN1", 45.0, T(12), eq=706, rec="manualAdd"))
    disp.append(disp_row(411, "NOEQ", 15.0, T(13), eq=0))
    disp.append(disp_row(412, "UNEXPL1", 300.0, T(4, 10), eq=707))
    for r in disp[-6:]:
        if r["TransactionID"] in ("PROD0", "MAN1", "NOEQ", "COLL1"):
            iot.append({"ID": 990 + len(iot), "AccountID": ACC, "TransactionID": r["TransactionID"], "DeviceID": "112233445566",
                        "ProductID": r["ProductID"], "TypeID": 1, "Volume": r["Volume"], "Createdate": r["Createdate"]})
    for tx, v in (("DUPX1", 77.7), ("DUPX2", 77.7), ("NAX1", 60.0), ("NAX2", 60.0), ("68B6B33CE0186AA38F90", 900.0)):
        iot.append({"ID": 1100 + len(iot), "AccountID": ACC, "TransactionID": tx, "DeviceID": "112233445566",
                    "ProductID": 1, "TypeID": 1, "Volume": v, "Createdate": T(5)})
    # C25: raw IOTData_FMS dispensing never decoded anywhere, and one decoded into UsageDispensing only
    fms.append({"ID": 980, "AccountID": ACC, "TransactionID": "FMSLOST", "DeviceId": "112233445566", "TypeID": 1,
                "CreateDate": T(17), "TotaliserFromComms": 0, "TelementryData": "{}"})
    fms.append({"ID": 981, "AccountID": ACC, "TransactionID": "FMSUDONLY", "DeviceId": "112233445566", "TypeID": 1,
                "CreateDate": T(18), "TotaliserFromComms": 0, "TelementryData": "{}"})
    disp.append(disp_row(413, "FMSUDONLY", 12.0, T(18), eq=708))
    android.append({"ID": 890, "AccountID": ACC, "StoreID": 10, "ProductID": 1, "TrailerMac": "T9",
                    "InformationMac": "AABBCCDDEEFF", "TransactionID": "FMSUDONLY", "Volume": 12.0,
                    "Createdate": T(18), "Totalizer": 0, "TotalizerEnd": 0})
    # FMS record inside the decode grace period at the window end: not checked
    fms.append({"ID": 982, "AccountID": ACC, "TransactionID": "FMSLATE", "DeviceId": "112233445566", "TypeID": 1,
                "CreateDate": W0 + pd.Timedelta(hours=47, minutes=50), "TotaliserFromComms": 0, "TelementryData": "{}"})
    # backup IOT record never imported into UsageDispensing
    iot.append({"ID": 1300, "AccountID": ACC, "TransactionID": "LOST1", "DeviceID": "112233445566", "ProductID": 1,
                "TypeID": 1, "Volume": 120.0, "Createdate": T(14)})
    # notifications: BTLinkLost on TXA03 (the short transaction) + NoFlow without completion
    notif = [
        {"ID": 1, "AccountID": ACC, "DeviceId": "AABBCCDDEEFF", "TypeID": 132, "CreateDate": T(6, 1),
         "TelementryData": json.dumps({"TelementryData": [{"TrId": "TXA03", "Type": 132,
                                                           "msg": "BT Link lost on Prod:1, on TrId:TXA03 with 50.00L "}]})},
        {"ID": 2, "AccountID": ACC, "DeviceId": "AABBCCDDEEFF", "TypeID": 3, "CreateDate": T(15),
         "TelementryData": json.dumps({"TelementryData": [{"TrId": "GHOST1", "Type": 3, "msg": "NO FLOW STOP"}]})},
        {"ID": 3, "AccountID": ACC, "DeviceId": "AABBCCDDEEFF", "TypeID": 3, "CreateDate": T(16),
         "TelementryData": json.dumps({"TelementryData": [{"TrId": "TXA05", "Type": 3}]})},
        {"ID": 4, "AccountID": ACC, "DeviceId": "AABBCCDDEEFF", "TypeID": 124, "CreateDate": T(16, 1),
         "TelementryData": json.dumps({"TelementryData": [{"TrId": "TXA05", "Type": 124}]})},
    ]
    # Stock: tank declines 6000 L over the window, only ~2 kL dispensed at store 10 -> possible loss;
    # 3-hour reading gap -> telemetry gap
    stock = []
    times = [T(h) for h in range(0, 48) if not 20 <= h < 23]
    for k, t in enumerate(times):
        stock.append({"ID": k, "AccountID": ACC, "StoreID": 10, "TankID": 1, "CreateDate": t,
                      "Volume": 20000 - k * (6000 / len(times)), "Ullage": k * (6000 / len(times)) + 5000})
    # ATG device seen only in lookback -> stopped reporting
    atg = [{"ID": 1, "AccountID": ACC, "DeviceId": "ATGDEAD", "TypeID": 1, "CreateDate": W0 - pd.Timedelta(hours=5),
            "TelementryData": "{}"}]
    # comm errors: one real failure, one near-empty
    err = [{"ID": i, "AccountID": ACC, "DeviceID": "DEVBAD", "CreateDate": T(1, i), "Message": "probe timeout", "Vol": 800}
           for i in range(15)]
    err += [{"ID": 100 + i, "AccountID": ACC, "DeviceID": "DEVEMPTY", "CreateDate": T(2, i), "Message": "low", "Vol": 2.0}
            for i in range(12)]

    for name, rows in (("UsageDispensing", disp), ("UsageDispensingAndroid", android), ("UsageDispensingIOT", iot),
                       ("IOTData_FMS", fms), ("IOTData_Notification", notif), ("Stock", stock),
                       ("IOTData_ATG", atg), ("IOTData_Error", err)):
        pd.DataFrame(rows).to_csv(p / f"Test_{name}.csv", index=False)

    out = tmp_path_factory.mktemp("out")
    cfg = base_cfg()
    cfg["known_dual_write_equipment_ids"] = {}
    doc = run_checks.run_client(DirSource(str(p)), cfg["clients"][0], cfg, RUN, str(out))
    return doc, out


def cats(doc, check=None, status=None):
    return [f for f in doc["findings"] if (check is None or f["check"] == check)
            and (status is None or f["status"] == status)]


def ev(out, f):
    return pd.read_csv(os.path.join(out, "TestCo", f["evidence_file"]))


def test_window_and_no_failed_checks(result):
    doc, _ = result
    assert doc["window"]["start_sast"] == "2026-09-30 06:00 SAST"
    assert doc["window"]["end_sast"] == "2026-10-02 06:00 SAST"
    assert all(r["result"] == "ran" for r in doc["checks_run"]), doc["data_gaps"]


def test_midnight_boundary():
    s, e = run_checks.compute_window(RUN, 0, 48)
    assert str(s) == "2026-09-30 00:00:00+02:00" and str(e) == "2026-10-02 00:00:00+02:00"
    s, e = run_checks.compute_window(pd.Timestamp("2026-10-02 05:59", tz="Africa/Johannesburg"), 6, 48)
    assert str(e) == "2026-10-01 06:00:00+02:00"


def test_duplicates(result):
    doc, out = result
    known = [f for f in cats(doc, "C01") if "known dual-pipeline" in f["category"]]
    new = [f for f in cats(doc, "C01") if "known" not in f["category"]]
    assert len(known) == 1 and known[0]["litres"] == 900.0
    assert len(new) == 1 and new[0]["litres"] == 77.7
    ids = set(ev(out, new[0])["ID"])
    assert ids == {402, 403}, "N/A-UnqTrID rows far apart must not be grouped as duplicates"
    assert cats(doc, "C02") and set(ev(out, cats(doc, "C02")[0])["ID"]) == {406, 407}


def test_totaliser_continuity(result):
    doc, out = result
    f = cats(doc, "C12", "Investigate")
    assert len(f) == 1
    e = ev(out, f[0])
    assert len(e) == 2, e
    a = e[e["Source"] == "UsageDispensingAndroid"].iloc[0]
    assert a["TransactionID"] == "TXA03" and a["MissingVolume_L"] == 50.0 and a["Macaddress"] == "AABBCCDDEEFF"
    assert a["UsageDispensingID"] == 103 and "BTLinkLost" in a["Explanation"]
    i = e[e["Source"] == "UsageDispensingIOT"].iloc[0]
    assert i["TransactionID"] == "IOT3" and i["MissingVolume_L"] == 30.0, "non-comms start (IOT3) must be skipped"
    assert {"Macaddress", "ID", "Volume", "TransactionID", "MissingVolume_L"} <= set(e.columns)


def test_product_zero(result):
    doc, out = result
    f = cats(doc, "C11", "Investigate")
    assert len(f) == 1
    assert set(ev(out, f[0])["SourceTable"]) == {"UsageDispensing", "UsageDispensingIOT"}


def test_identifier_and_recon_checks(result):
    doc, out = result
    c03 = cats(doc, "C03")[0]
    assert ev(out, c03)["ProposedFromInformationRec"].iloc[0] == "RECOVER1"
    assert any(f["category"] == "Possible manual entry" for f in cats(doc, "C10"))
    assert cats(doc, "C15", "Monitor")
    un = cats(doc, "C06", "Investigate")
    assert un and "UNEXPL1" in set(ev(out, un[0])["TransactionID"])
    c08 = cats(doc, "C08")
    assert c08 and set(ev(out, c08[0])["TransactionID"]) == {"LOST1"}


def test_notifications(result):
    doc, out = result
    nf = cats(doc, "C16")
    assert nf and set(ev(out, nf[0])["TrId"]) == {"GHOST1"}, "TXA05 had a completion and must not be flagged"
    assert nf[0]["status"] == "Investigate"


def test_tank_comm_gaps(result):
    doc, _ = result
    assert cats(doc, "C18", "Investigate"), "planted ~6000 L decline vs ~1.6 kL dispensed"
    statuses = {f["status"] for f in cats(doc, "C20")}
    assert statuses == {"Investigate", "Monitor"}
    cat17 = {f["category"] for f in cats(doc, "C17")}
    assert "Telemetry gap (Stock)" in cat17 and "Stopped reporting (IOTData_ATG)" in cat17
    quiet = [f for f in cats(doc, "C17") if f["account_id"] == 9002]
    assert quiet and quiet[0]["category"] == "No data in window"


def test_kpis(result):
    doc, _ = result
    k = doc["kpis"]
    assert k["duplicate_excess_L"] == pytest.approx(977.7)
    assert k["total_fuel_dispensed_L"] == pytest.approx(k["raw_dispensed_before_duplicate_removal_L"] - 977.7)
    assert k["reconciliation_denominator_L"] == k["total_fuel_dispensed_L"]
    assert k["tanks_at_risk_of_running_dry"] == 0
    assert k["sites_with_communication_failures"] == 2
    row = [r for r in doc["portfolio"] if r["AccountID"] == 9002][0]
    assert row["Recon_pct"] == "n/a"


def test_every_db_statement_passes_the_read_only_guard(tmp_path):
    """Drive the DbSource with a fake connection: every SQL it emits must pass assert_read_only."""
    import fams_db
    import fams_sources

    seen = []

    class FakeDb:
        @staticmethod
        def query_df(sql, params=None, allow_procs=False):
            fams_db.assert_read_only(sql)
            seen.append(sql)
            if "INFORMATION_SCHEMA" in sql:
                table = params[0]
                cols = {"Store": ["ID", "AccountID", "Macaddress"], "Account": ["ID", "name"],
                        "TempTableDataJson": ["ID", "Macaddress", "CreateDate", "errorid", "Jsondata"],
                        "Allocation": ["ID", "Description"], "EquipmentCostCentre": ["ID"]}.get(
                    table, ["ID", "AccountID", "Createdate", "CreateDate", "Volume", "TransactionID"])
                return pd.DataFrame({"COLUMN_NAME": cols})
            if "FROM [Store]" in sql:
                return pd.DataFrame({"ID": [1], "AccountID": [ACC], "Macaddress": ["AABBCCDDEEFF"]})
            return pd.DataFrame()

    src = fams_sources.DbSource.__new__(fams_sources.DbSource)
    src.db, src._cols = FakeDb, {}
    cfg = base_cfg()
    cfg["clients"][0]["accounts"]["9003"] = None
    cfg["android_accounts"] = [ACC]
    doc = run_checks.run_client(src, cfg["clients"][0], cfg, RUN, str(tmp_path))
    assert len(seen) > 15
    assert any("TempTableDataJson" in s for s in seen) and any("LEFT JOIN Allocation" in s for s in seen)
    assert any("JSON_VALUE" in s and "ISJSON" in s for s in seen)   # C26 payload query passed the guard
    assert not [g for g in doc["data_gaps"] if "FAILED" in g["gap"]], doc["data_gaps"]


def test_per_day_site_metrics(result):
    doc, _ = result
    days = doc["days"][str(ACC)]
    assert [x["date"] for x in days] == ["2026-09-30", "2026-10-01"]
    assert all(x["start"].endswith("06:00:00") for x in days)
    total = sum(x["dispensed_L"] for x in days)
    assert total == pytest.approx(doc["kpis"]["total_fuel_dispensed_L"])
    # the totaliser break (TXA03 at T(6)) is on day 1 only; the IOT break (T(32)) on day 2
    tot = [f for f in doc["findings"] if f["check"] == "C12" and f["status"] == "Investigate"][0]
    assert tot["days"] == ["2026-09-30", "2026-10-01"] and tot["day_rows"] == {"2026-09-30": 1, "2026-10-01": 1}
    assert all(tot["finding_id"] in x["finding_ids"] for x in days)
    assert days[0]["tanks"] and days[0]["atg_pct"] is not None
    quiet = doc["days"]["9002"]
    assert quiet[0]["usage_pct"] is None and quiet[0]["dispensed_L"] == 0


def test_c25_fms_decode_gap(result):
    doc, out = result
    inv = cats(doc, "C25", "Investigate")
    mon = cats(doc, "C25", "Monitor")
    assert len(inv) == 1 and len(mon) == 1
    assert set(ev(out, inv[0])["TransactionID"]) == {"FMSLOST"}
    assert set(ev(out, mon[0])["TransactionID"]) == {"FMSUDONLY"}
    assert mon[0]["affected"].startswith("12.00 L")


def test_source_hierarchy_in_findings(result):
    doc, _ = result
    h = doc["source_hierarchy"]
    assert h[0]["layer"] == "Source of truth" and h[0]["table"] == "UsageDispensing"
    truth = [x["table"] for x in h if x["layer"] == "Source of truth"]
    assert truth == ["UsageDispensing", "UsageTransfer", "UsageReceiving", "Stock"]
    assert {x["table"] for x in h if x["layer"] == "Backup"} == {"UsageDispensingIOT", "UsageDispensingAndroid"}
    assert "TempTableDataJson" in {x["table"] for x in h if x["layer"] == "Raw"}


def test_c26_android_raw_payload_missing():
    import types
    W1 = W0 + pd.Timedelta(hours=48)
    stores = pd.DataFrame({"AccountID": [ACC, 9002], "Macaddress": ["AND1", "IOTONLY"]})
    disp = pd.DataFrame({"AccountID": [ACC], "TransactionID": ["OK1"], "Volume": [10.0], "CreateDate": [T(1)]})
    rec = pd.DataFrame({"AccountID": [ACC], "TransactionID": ["RCV1"], "Volume": [5000.0], "CreateDate": [T(2)]})
    pay = pd.DataFrame({
        "ID": [1, 2, 3, 4, 5, 6, 7],
        "Macaddress": ["AND1", "AND1", "AND1", "AND1", "AND1", "IOTONLY", "AND1"],
        "TransactionID": ["OK1", "RCV1", "LOSTA", "LOSTA", None, "X9", "LATE1"],
        "Volume": ["10", "5000", "88.5", "88.5", "3", "7", "4"],
        "CreateDate": [T(1), T(2), T(3), T(3, 0, 5), T(4), T(5), W1 - pd.Timedelta(minutes=10)]})
    d = types.SimpleNamespace(tempjson_payloads=pay, stores=stores, android_accounts={ACC}, disp=disp,
                              transfer=None, receiving=rec, window_start=W0, window_end=W1)
    cfg = base_cfg()
    out = ic.check_android_raw(d, cfg)
    assert len(out) == 1 and out[0]["check"] == "C26" and out[0]["status"] == "Investigate"
    assert out[0]["account_id"] == ACC and out[0]["count"] == 1 and out[0]["litres"] == 88.5
