# Duplicate Detection

A "duplicate" isn't defined by one rule. Run all five rules below and
reason about the overlap. Each pair a rule matches is joined into one
**duplicate group**, which is one physical event. In each group the
**lowest `ID` is the original**, every other row is an extra copy, and the
extra copies' volume is the amount the totals are inflated by.

The daily job runs exactly these rules in code
(`fams-integrity-agent/scripts/integrity_checks.py` → `check_duplicates`,
checks C01/C02). The SQL below does the same thing for one account during
an investigation. All of it is read-only. Run it through
`fams-integrity-agent/scripts/run_query.py`.

## Fixes to the original three checks (2026-10-02)

| Gap in the old checks | Fix |
|---|---|
| Checks 1 and 2 partitioned on `UnqTrID` without excluding `'N/A'`/NULL, so every unreconciled row with the same volume and equipment looked like a duplicate | Rules 1 and 2 only use rows with a real `UnqTrID`. Rows without one are caught by rules 3–5 instead |
| Check 2 required an identical `Createdate`, so it missed the confirmed TWK/PMB dual-pipeline bug, where the two writes land seconds apart | Rule 4 (same `TransactionID`) and rule 5 (same equipment + volume within 120 s) |
| Check 3 grouped on `Volume + Createdate` across the whole account, including zero-volume rows | Rule 3 adds `StoreID`, and every rule uses `Volume > 0` only |
| `ROW_NUMBER() … ORDER BY Volume, UnqTrID` was not deterministic, so the row marked as the duplicate could change between runs | `ORDER BY ID`: the lowest ID is always the original |
| The three counts were added together, so one pair matched by two checks was counted twice | Groups are merged and each event is reported once, listing the rules that matched |
| Two rows with the same `TransactionID` but **different** volumes counted as a duplicate (or were missed) | Reported separately as a **TransactionID collision** (C02). That is the Richards Bay pattern, not a double import |
| A pair split across the window boundary was missed | The search reaches into the previous day (the daily job uses a 72 h lookback). The pair is reported if any row in it falls inside the window |

## The five rules

All rules apply to `UsageDispensing`, with `AccountID = {AccountID}` and
`Volume > 0`. Set `{StartDate}` one day before the window you care about so
that pairs crossing the boundary are found.

```sql
-- R1: same real UnqTrID + Volume + EquipmentID
WITH r AS (
  SELECT ID, AccountID, StoreID, EquipmentID, TransactionID, UnqTrID, Volume, Createdate, Recnumber,
         COUNT(*)  OVER (PARTITION BY UnqTrID, Volume, EquipmentID) AS n,
         ROW_NUMBER() OVER (PARTITION BY UnqTrID, Volume, EquipmentID ORDER BY ID) AS rn
  FROM UsageDispensing
  WHERE AccountID = {AccountID} AND Createdate >= {StartDate} AND Volume > 0
    AND UnqTrID IS NOT NULL AND UnqTrID NOT IN ('', 'N/A', '0'))
SELECT * FROM r WHERE n > 1 ORDER BY UnqTrID, rn;

-- R2: same real UnqTrID + EquipmentID + Createdate
--     (as R1, but PARTITION BY UnqTrID, EquipmentID, Createdate)

-- R3: same StoreID + Volume + Createdate (catches rows with no or garbage IDs)
WITH r AS (
  SELECT ID, AccountID, StoreID, EquipmentID, TransactionID, UnqTrID, Volume, Createdate, Recnumber,
         COUNT(*)  OVER (PARTITION BY StoreID, Volume, Createdate) AS n,
         ROW_NUMBER() OVER (PARTITION BY StoreID, Volume, Createdate ORDER BY ID) AS rn
  FROM UsageDispensing
  WHERE AccountID = {AccountID} AND Createdate >= {StartDate} AND Volume > 0)
SELECT * FROM r WHERE n > 1 ORDER BY Createdate, rn;

-- R4: same TransactionID. One distinct volume = duplicate; several = COLLISION
WITH r AS (
  SELECT ID, AccountID, StoreID, EquipmentID, TransactionID, UnqTrID, Volume, Createdate, Recnumber,
         COUNT(*) OVER (PARTITION BY TransactionID) AS n,
         MIN(Volume) OVER (PARTITION BY TransactionID) AS vmin,
         MAX(Volume) OVER (PARTITION BY TransactionID) AS vmax
  FROM UsageDispensing
  WHERE AccountID = {AccountID} AND Createdate >= {StartDate} AND Volume > 0
    AND TransactionID IS NOT NULL AND TransactionID NOT IN ('', 'N/A', '0'))
SELECT *, CASE WHEN vmin = vmax THEN 'duplicate' ELSE 'collision' END AS kind
FROM r WHERE n > 1 ORDER BY TransactionID, ID;

-- R5: same Store + Equipment + Volume within 120 seconds of the previous one (IDs ignored)
WITH r AS (
  SELECT ID, AccountID, StoreID, EquipmentID, TransactionID, UnqTrID, Volume, Createdate, Recnumber,
         LAG(Createdate) OVER (PARTITION BY StoreID, EquipmentID, Volume ORDER BY Createdate, ID) AS prev_time,
         LAG(ID)         OVER (PARTITION BY StoreID, EquipmentID, Volume ORDER BY Createdate, ID) AS prev_id
  FROM UsageDispensing
  WHERE AccountID = {AccountID} AND Createdate >= {StartDate} AND Volume > 0 AND EquipmentID > 0)
SELECT * FROM r WHERE prev_time IS NOT NULL AND DATEDIFF(second, prev_time, Createdate) <= 120
ORDER BY Createdate;
```

## Reading the result

- **Known dual-pipeline bug** (TWK Interlink 29307, PMB 37571): a group
  where one row's `Recnumber` is in the `4627x` batch series and the other
  is `importFams`, seconds apart, with the same ID and volume. Cite the
  known bug. Don't describe it as a new duplicate. The extra row still
  inflates totals and still needs removing.
- **Rule 5 alone** (no shared ID) is the weakest evidence. The same vehicle
  filling twice within two minutes is rare but possible, so check the raw
  device log before calling it a duplicate.
- **Collision**: either row may be hiding or overwriting the other. Trace
  both through `UsageDispensingAndroid`/`UsageDispensingIOT` and the raw
  payload (`algorithms/atg-reconciliation.md`).

## Removing duplicates: a human runs it, not the agent

The tooling is read-only and refuses `DELETE`. Give the user:

1. the preview (the group's rows from the queries above),
2. the explicit list of IDs to remove (never the lowest ID in a group),
3. the statement for them to run in SSMS after review. If two rows in a
   group disagree on provenance, keep the one whose `Recnumber` is in
   (`'manualAdd'`, `'importFams'`):

```sql
DELETE FROM UsageDispensing
WHERE ID IN ({ExplicitIDList})
  AND AccountID = {AccountID}
  AND Createdate >= '{StartDate}';
```

## Related: TransactionID / UnqTrID backfill

Some rows never got `UnqTrID` populated. The JSON key name varies between
accounts, so check which one an account uses first (see
`datasets/field-definitions.md`). The daily job's C03/C04 evidence already
contains the candidate ID taken from `InformationRec`
(`ProposedFromInformationRec`).

```sql
-- 1. Find out which key this account's JSON uses (read-only)
SELECT TOP 20 InformationRec,
       JSON_VALUE(InformationRec, '$.transactionID') AS try_lower_D,
       JSON_VALUE(InformationRec, '$.transactionId')  AS try_lower_d,
       JSON_VALUE(InformationRec, '$.TransactionID')  AS try_upper_T
FROM UsageDispensing
WHERE AccountID = {AccountID} AND Createdate >= {StartDate}
  AND (UnqTrID = 'N/A' OR UnqTrID IS NULL);

-- 2. Preview (read-only)
SELECT ID, AccountID, Createdate,
       JSON_VALUE(InformationRec, '$.transactionID') AS proposed_UnqTrID
FROM UsageDispensing
WHERE AccountID = {AccountID} AND Createdate >= {StartDate}
  AND (UnqTrID = 'N/A' OR UnqTrID IS NULL)
ORDER BY Createdate;
```

```sql
-- 3. For the HUMAN to run in SSMS after reviewing the preview:
UPDATE UsageDispensing
SET UnqTrID = JSON_VALUE(InformationRec, '$.transactionID')
WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}'
  AND (UnqTrID = 'N/A' OR UnqTrID IS NULL);
```
