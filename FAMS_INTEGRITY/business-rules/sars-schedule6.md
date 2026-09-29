# SARS Schedule 6 Rebate Reporting

This is a real, implemented rule — not a placeholder. Source of truth:
`scripts/stored-procedures/get_ReportinglogbookRev6SARS.sql` (the stored
proc is on Rev 7 of its internal fix history; object name is still
`get_ReportinglogbookRev6SARS`). Call signature:

```sql
EXEC get_ReportinglogbookRev6SARS @account = 278, @from = '2025-10-01', @to = '2025-11-01';
```

## What the report is

A combined logbook of three record types over a date range, per account:
1. **Dispensing** (RecordTypeID 1) — from `UsageDispensing`
2. **Transfer** (RecordTypeID 2) — from `GetFueltransfers`
3. **StockReceivedManual** (RecordTypeID 3) — from `GetFuelReceivingManual`

Deduplicated by `(FillID, AccountID)` keeping the earliest `Date` (`rnk = 1`
via `ROW_NUMBER()`), and filtered to `TankID IS NOT NULL`.

Note: this proc's own `RecordTypeID` (1/2/3 above) is a **synthetic tag
this stored procedure assigns** to distinguish the three source queries in
its combined result set — it is not the same column as the raw
`IOTData_*` tables' `RecordTypeId`/`TypeID` (see `datasets/field-
definitions.md`). The two happen to agree on ordering (1=Dispensing,
2=Transfer, 3≈Offloading/StockReceived), which is a useful cross-check,
but they're populated by entirely different code paths - don't assume one
explains or validates the other beyond that coincidental agreement.

## Eligible / Non-Eligible determination

This is the core SARS rebate-qualification rule. Evaluated top-to-bottom,
first match wins:

1. If `PerEquipmentAssetAllocationDesc` (the per-equipment/allocation
   description, sourced via `PerEquipmentAssetAllocation`) contains the
   text **"Not qualified"** → **Non-Eligible**, regardless of any rebate
   ID present. This is a hard override — e.g. a WingerdBestuur vehicle
   with a linked rebate record is still Non-Eligible if its allocation
   description says "Not qualified".
2. Else if `EquipmentRebate.ID` (`ERID`) `> 0` → **Eligible**
3. Else if `AllocationRebate` on Allocation1 (`AR1ID`) `> 0` → **Eligible**
4. Else if `AllocationRebate` on Allocation2 (`AR2ID`) `> 0` → **Eligible**
5. Else → **Non-Eligible**

```sql
CASE
    WHEN ISNULL(PerEquipmentAssetAllocationDesc, '') LIKE '%Not qualified%' THEN 'Non-Eligible'
    WHEN ISNULL(ERID,  0) > 0 THEN 'Eligible'
    WHEN ISNULL(AR1ID, 0) > 0 THEN 'Eligible'
    WHEN ISNULL(AR2ID, 0) > 0 THEN 'Eligible'
    ELSE 'Non-Eligible'
END
```

**History of this rule** (why it looks like this): an earlier revision
compared a rebate ID to the literal value `1`, which only matched the one
rebate record whose primary key happened to be `1` — a bug. It also didn't
check for the "Not qualified" allocation description at all, so a vehicle
could show Eligible purely because *some* rebate record was linked, even
when its allocation was explicitly disqualified. Both were fixed together:
the "Not qualified" check now runs first and unconditionally overrides, and
the rebate checks now use `> 0` so any valid linked rebate counts, not just
one specific row.

**If asked to touch this logic again:** preserve the override-first
ordering. Do not go back to `= 1`/single-ID comparisons — that regresses
the original bug.

## Asset Allocation Description resolution (PEA lookup)

`PerEquipmentAssetAllocationDesc` — which feeds directly into the
Eligible/Non-Eligible check above — is not a simple join. It comes from a
ranked subquery over `PerEquipmentAssetAllocation` (aliased PEA) that:

1. De-duplicates multiple PEA rows for the same
   `(EquipmentAssetID, Allocation1ID, Allocation2ID)` combination
   (`ROW_NUMBER() ... ORDER BY ID ASC`, keep `dedup_rn = 1`).
2. Tries an **exact match** first: `EquipmentAssetID` + `Allocation1ID`
   (Operation) + `Allocation2ID` (Location) all match (`MatchType = 1`).
3. Falls back to an **Allocation1-only match** (`MatchType = 2`) when no
   exact Allocation1+Allocation2 row exists — i.e. the Operation has a PEA
   record but the specific Location doesn't. This is what lets the
   description populate for combinations like `CDW947NC` under
   `PekanVervoer / Tiller / DruiweVervoer / Dis`, where only the Operation
   level was mapped.
4. Exact match always wins over fallback when both exist.

**Why this matters for integrity review:** if a customer complains that
"Asset Allocation Desc is blank" for some Operation/Location pairs, the
root cause is almost always a missing `PerEquipmentAssetAllocation` row at
the Allocation2 (Location) level with no Allocation1-level fallback either
— i.e. that Operation was never mapped in PEA at all. That's a data-setup
gap on the customer's side, not a bug in this query.

## Apparent duplicate descriptions in the Excel output

If a customer sees the same `AssetAllocationDesc` repeated across many rows
in the "Per Equipment" / individual sheet, this has been confirmed (via
direct data analysis) to be legitimate: the same vehicle has multiple fills
in the period, and each fill legitimately carries the same allocation
description. There is no duplicate `FillID` in the result set. **Do not
"fix" this by touching the stored proc** — if it needs addressing, it's an
Excel/report-template presentation change (suppress repeated values in a
grouped view), not a data issue.

## Related concepts used by this report

- **Eqp_OpeningBalance / Eqp_ClosingBalance / Eqp_Ltthatcanbeused /
  Eqp_Usage** — per-fill tank-style balance tracking for equipment with a
  max-litres capacity (`PerEquipmentStore.Maxlitres1`), computed via
  `LAG`/`LEAD` window functions over each equipment's fill history. See
  `algorithms/atg-reconciliation.md` for the general LAG/LEAD balance
  pattern — this is the equipment-level analogue of the tank-level ATG
  balancing in this same report (STEP 3).
- **ATG tank balancing** (STEP 3 of the proc) — daily opening/closing stock
  per tank from `Stock`, with delivery detection via a **>3500 litre
  jump** heuristic. See `investigation/tank.md` for how this is used
  outside the SARS report context too.
- **TankOpeningVolume / TankClosingVolume** — for Dispensing and Transfer
  record types these are hardcoded `'0'`/`'N/A'` (no ATG tank link exists
  for those record types); only StockReceivedManual carries a real
  `TankID`/`Tank` value.
