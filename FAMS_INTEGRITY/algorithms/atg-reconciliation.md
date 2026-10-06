# ATG / Cross-Source Reconciliation

Compares `UsageDispensing` (source of truth) with its backups
`UsageDispensingIOT` (backup 1) and `UsageDispensingAndroid` (backup 2) for the
same TransactionID — the primary integrity signal in this system. When they
disagree, `UsageDispensing` stands in reporting and the difference is a finding.

**IOT vs Android log mismatch beyond tolerance:**
```sql
SELECT IOT.AccountID,
       IOT.ID AS IOTID, IOT.Volume AS IOTVolume, IOT.TransactionID AS IOTTransactionID, IOT.Createdate AS IOTDate,
       logg.Recnumber AS LogRecnumber, logg.ID AS LogID, logg.Volume AS LogVolume,
       ABS(logg.TotalizerEnd - logg.Totalizer) AS LogVolumeTotalizer,
       logg.TransactionID AS LogTransactionID, logg.Createdate AS LogDate
FROM UsageDispensingIOT IOT
LEFT JOIN UsageDispensingAndroid logg
  ON IOT.TransactionID = logg.TransactionID AND IOT.AccountID = logg.AccountID
WHERE IOT.AccountID = {AccountID} AND IOT.Createdate >= '{StartDate}'
  AND ABS(IOT.Volume - logg.Volume) > 0.1
ORDER BY IOT.Createdate;
```

**Three-way compare for a store:**
```sql
SELECT u.Volume AS UDVolume, IOT.Volume AS IOTVolume, logg.Volume AS AndroidVolume,
       u.AccountID, u.Recnumber AS UDRecnumber, u.ID AS UDID, u.OrigVolume AS UDVolumeOrig,
       u.TransactionID AS UDTransactionID, u.Createdate AS UDDate,
       IOT.ID AS IOTID, IOT.TransactionID AS IOTTransactionID, IOT.Createdate AS IOTDate,
       logg.Recnumber AS LogRecnumber, logg.ID AS LogID,
       ABS(logg.TotalizerEnd - logg.Totalizer) AS LogVolumeTotalizer,
       logg.TransactionID AS LogTransactionID, logg.Createdate AS LogDate
FROM UsageDispensing u
LEFT JOIN UsageDispensingIOT IOT ON u.TransactionID = IOT.TransactionID AND u.AccountID = IOT.AccountID
LEFT JOIN UsageDispensingAndroid logg ON u.TransactionID = logg.TransactionID AND u.AccountID = logg.AccountID
WHERE u.AccountID = {AccountID} AND u.Createdate >= '{StartDate}'
  AND u.Volume > 0 AND u.StoreID IN ({StoreIDList})
-- filter on u (the source of truth), not IOT: a WHERE on IOT turns the LEFT JOIN into
-- an inner join and silently drops UsageDispensing rows that have no IOT backup
ORDER BY u.Createdate;
```

**Trace a specific transaction across all three tables:**
```sql
SELECT * FROM UsageDispensing        WHERE AccountID = {AccountID} AND TransactionID = '{TransactionID}' AND Createdate >= '{StartDate}';
SELECT * FROM UsageDispensingAndroid WHERE AccountID = {AccountID} AND TransactionID = '{TransactionID}' AND Createdate >= '{StartDate}';
SELECT * FROM UsageDispensingIOT     WHERE AccountID = {AccountID} AND TransactionID = '{TransactionID}' AND Createdate >= '{StartDate}';
```

**Trace to the raw payload to settle a disputed transaction.** For accounts
with Android devices the raw table behind `UsageDispensing` is
`TempTableDataJson`; for IOT the raw table is `IOTData_FMS` (by
`TransactionID`). IOT-only accounts have no `TempTableDataJson` rows:
```sql
SELECT JSON_VALUE(Jsondata, '$.transactionID')   AS TransactionID,
       JSON_VALUE(Jsondata, '$.oldLitres')       AS OldLitres,
       JSON_VALUE(Jsondata, '$.DispensedVolume') AS DispensedVolume,
       JSON_VALUE(Jsondata, '$.Volume')          AS Volume
FROM TempTableDataJson
WHERE Macaddress IN (SELECT Macaddress FROM Store WHERE AccountID = {AccountID})
  AND CreateDate >= '{StartDate}' AND errorid = 0
ORDER BY CreateDate;
```

## Transfer/Receiving vs. ATG telemetry cross-check

A second, independent reconciliation path, alongside the three-way
dispensing compare above — this one for `UsageTransfer`/`UsageReceiving`
rather than `UsageDispensing`. First built and validated in
`fams-daily-report` (2026-08-21), then graduated here as the canonical
source per this skill's own relationship to that one.

**The idea**: a `UsageTransfer`/`UsageReceiving` row's `TransactionID`
matches an `IOTData_Notification` row's `TrId` (inside its `TelementryData`
JSON blob) **exactly** — confirmed from a real ShipTech PMB example on
2026-08-18. That notification pins down the real device and real-world
start time of the event (prefer a `TypeID=125` "DispStartNow" entry - see
`datasets/field-definitions.md`'s RecordTypeId/TypeID table). From there,
the nearest `IOTData_ATG` fill/drop event (`TypeID` 2-5) on that same
device gives an independently-measured volume (`endVol - strtVol`) for the
same physical event, comparable against the logged `Volume`.

**Known, unresolved discrepancy**: for that same physical event,
`IOTData_ATG.fillTrId` is a *different-but-related* ID from the actual
`TransactionID` (same device-MAC prefix, different trailing suffix) - the
account owner has flagged this as a known bug, explanation still pending.
Because of this, **do not join `UsageTransfer`/`UsageReceiving` to
`IOTData_ATG` by `TransactionID == fillTrId`** — anchor via
`IOTData_Notification.TrId` (device + time) instead, then match the ATG
event by device + nearest `strtTime`, not by ID equality. Treat the ID
mismatch itself as a separate, still-open data-quality note - it is not
evidence the volume comparison is unreliable, since the notification
anchor is confirmed reliable independent of it.

**Matching logic (pseudocode, mirrors `fams-daily-report/scripts/analyze.py`
`transfer_receiving_atg_reconciliation()`):**
```
for each UsageTransfer/UsageReceiving row:
    notif = IOTData_Notification row where TrId == row.TransactionID
            (prefer TypeID=125 "DispStartNow" if multiple)
    if no notif: unverifiable, skip
    candidate_atg_events = IOTData_ATG fill/drop events (TypeID 2-5)
                           on notif.device, within N minutes of notif.time
    if no candidate: "Monitor" - logged volume unverified this run
    else:
        atg_volume = nearest_candidate.endVol - nearest_candidate.strtVol
        if abs(atg_volume - row.Volume) / row.Volume > tolerance_pct:
            "Investigate" - logged volume disagrees with ATG telemetry
```

A volume difference above tolerance here means the record book and tank
telemetry disagree on how much fuel actually moved - report it as a
possible discrepancy needing field verification (delivery note, dip-stick
check), same "possible cause" language discipline as any other finding in
this skill. A transaction that can't be anchored to a notification, or has
no ATG event within the matching window, is unverified, not clean by
default.
