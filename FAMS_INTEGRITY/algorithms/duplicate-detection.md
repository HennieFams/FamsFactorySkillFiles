# Duplicate Detection

Three complementary checks — a "duplicate" isn't defined by one rule alone;
run all three and reason about overlap before deleting anything. Always
show the SELECT preview to the user before any DELETE.

**Check 1 — same UnqTrID + same volume + same equipment:**
```sql
WITH dup AS (
    SELECT InformationRec, EquipmentID, Volume, Createdate, ID, AccountID, StoreID, UnqTrID,
           ROW_NUMBER() OVER (PARTITION BY UnqTrID, Volume, EquipmentID ORDER BY Volume, UnqTrID) AS rnk
    FROM UsageDispensing
    WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}'
)
SELECT * FROM dup WHERE rnk > 1 ORDER BY Createdate;
```

**Check 2 — same UnqTrID + same equipment + same Createdate (volume > 0 only):**
```sql
WITH dup AS (
    SELECT InformationRec, EquipmentID, Volume, Createdate, ID, AccountID, StoreID, UnqTrID, Recnumber,
           ROW_NUMBER() OVER (PARTITION BY UnqTrID, EquipmentID, Createdate ORDER BY Volume, UnqTrID) AS rnk
    FROM UsageDispensing
    WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}' AND Volume > 0
)
SELECT * FROM dup WHERE rnk > 1 ORDER BY Createdate;
```

**Check 3 — same volume + same Createdate (catches cases with no/garbage UnqTrID):**
```sql
WITH dup AS (
    SELECT InformationRec, EquipmentID, Volume, Createdate, ID, AccountID, StoreID, UnqTrID,
           ROW_NUMBER() OVER (PARTITION BY Volume, Createdate ORDER BY Volume, UnqTrID) AS rnk
    FROM UsageDispensing
    WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}'
)
SELECT * FROM dup WHERE rnk > 1 ORDER BY Createdate;
```

**Deciding what's safe to delete** (only after user reviews the preview):
- Prefer deleting the *duplicate* row, keeping the one with `Recnumber` in
  (`'manualAdd'`, `'importFams'`) if the two disagree on provenance.
- Always delete by an explicit ID list, never a bulk condition:
  ```sql
  DELETE FROM UsageDispensing
  WHERE ID IN ({ExplicitIDList})
    AND AccountID = {AccountID}
    AND Createdate >= '{StartDate}';
  ```

## Related: TransactionID backfill

Some rows never got `UnqTrID` populated. The JSON key name is inconsistent
across accounts — check which one an account uses first (see
`datasets/field-definitions.md`):

```sql
-- 1. Detect which key format this account's JSON uses
SELECT TOP 20 InformationRec,
       JSON_VALUE(InformationRec, '$.transactionID') AS try_lower_D,
       JSON_VALUE(InformationRec, '$.transactionId')  AS try_lower_d,
       JSON_VALUE(InformationRec, '$.TransactionID')  AS try_upper_T
FROM UsageDispensing
WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}'
  AND (UnqTrID = 'N/A' OR UnqTrID IS NULL);

-- 2. Preview
SELECT ID, AccountID, Createdate,
       JSON_VALUE(InformationRec, '$.transactionID') AS proposed_UnqTrID
FROM UsageDispensing
WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}'
  AND (UnqTrID = 'N/A' OR UnqTrID IS NULL)
ORDER BY Createdate;

-- 3. Only after user confirms:
UPDATE UsageDispensing
SET UnqTrID = JSON_VALUE(InformationRec, '$.transactionID')
WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}'
  AND (UnqTrID = 'N/A' OR UnqTrID IS NULL);
```
