# Totaliser Continuity (per-nozzle flow)

**Rule:** on one physical nozzle, totaliser readings must run continuously
from one transaction to the next. Each transaction's start reading must
equal the previous transaction's end reading. A jump means fuel passed the
meter without being recorded (forward jump), or the meter was reset or a
record is wrong (backward jump). Skipped values are not allowed, and every
jump is reported.

Origin: the Harrismith case (2026-09-04, TrId `ncqtMSymN5Px`): FAMS
recorded 86.73 L, but the meter showed 400 L had been dispensed. The BT
link was lost mid-transaction, and the next transaction's real start
reading exposed the gap. The rule was made universal on 2026-10-02 and
runs every day as check **C12** (`FAMS_INTEGRITY_CHECK/scripts/integrity_checks.py`
→ `check_totaliser`).

## Definitions

- **Nozzle key**
  - `UsageDispensingAndroid`: `(AccountID, StoreID, ProductID, TrailerMac, InformationMac)`
    (see `business-rules/nozzle-validation.md`). Do not use `EquipmentID`.
  - `UsageDispensingIOT`: `(AccountID, DeviceID, ProductID)`. Configurable
    as `iot_nozzle_key` in the daily job's `config.json`.
- **Start / end**
  - Android: `Totalizer` / `TotalizerEnd`.
  - IOT: `TotaliserStart` / `TotaliserEnd`. On IOT, **`TotaliserEnd` is
    always computed** (`TotaliserStart + dispensed volume`), and
    `TotaliserStart` is a real meter reading only when the matching
    `IOTData_FMS.TotaliserFromComms = 1`. A pair is only checked when the
    *next* transaction's start is real.
- **Excluded readings**: `0` (not captured), values of `4294967.0` or more
  (the uint32 overflow value; see C13), and zero-volume rows. If either
  reading in a pair is invalid, that pair can't be verified. It is not
  counted as clean and not reported as a break.
- **Tolerance**: 2 L (`totaliser_continuity_litres`). This absorbs
  whole-litre resolution and rounding.

## What gets reported

The report shows one row per break, against the transaction **before** the
jump (the one whose recorded volume is probably short):

| Column | Meaning |
|---|---|
| Macaddress | `InformationMac` (Android) or `DeviceID` (IOT) |
| ID | ID of the source row (Android/IOT) for that transaction |
| UsageDispensingID | the canonical row's ID, matched on TransactionID |
| TransactionID | that transaction |
| Volume | its recorded volume |
| MissingVolume_L | `next start − this end` for a forward jump; blank for a backward one |
| Next… | the next transaction's ID, TransactionID, time and start reading |
| Explanation | BTLinkLost (Notification TypeID 132) or a Startup/cyclic reset (TypeID 1) on that TrId, when present |

If a nozzle chain breaks on more than 30% of its pairs (and on at least 4
of them), the cause is almost certainly two physical hoses sharing one key,
not real skips. That chain is reported once as a Monitor item ("ambiguous
nozzle key") and its breaks are not listed. When this happens, refine the
nozzle key rather than reporting noise.

## SQL for one account (investigation)

```sql
WITH a AS (
  SELECT ID, AccountID, StoreID, ProductID, TrailerMac, InformationMac, TransactionID, Volume, Createdate,
         Totalizer, TotalizerEnd,
         LEAD(ID)            OVER (PARTITION BY StoreID, ProductID, TrailerMac, InformationMac ORDER BY Createdate, ID) AS NextID,
         LEAD(TransactionID) OVER (PARTITION BY StoreID, ProductID, TrailerMac, InformationMac ORDER BY Createdate, ID) AS NextTransactionID,
         LEAD(Totalizer)     OVER (PARTITION BY StoreID, ProductID, TrailerMac, InformationMac ORDER BY Createdate, ID) AS NextStart
  FROM UsageDispensingAndroid
  WHERE AccountID = {AccountID} AND Createdate >= {StartDate} AND Volume > 0)
SELECT InformationMac AS Macaddress, ID, TransactionID, Volume, Createdate, TotalizerEnd,
       NextID, NextTransactionID, NextStart, NextStart - TotalizerEnd AS MissingVolume_L
FROM a
WHERE NextStart IS NOT NULL
  AND TotalizerEnd > 0 AND TotalizerEnd < 4294967 AND NextStart > 0 AND NextStart < 4294967
  AND ABS(NextStart - TotalizerEnd) > 2
ORDER BY Createdate;
```

(`PARTITION BY` treats NULLs as one group, the same as the daily job.)

## No auto-correction

Never "fix" a recorded volume from the totaliser. Report it, cite any BT
link loss or reset as the possible cause, and recommend checking the
device's own log (LOG608 or equivalent) for that transaction.
