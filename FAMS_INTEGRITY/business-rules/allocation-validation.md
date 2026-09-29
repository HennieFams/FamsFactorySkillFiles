# Allocation Validation

Every `UsageDispensing` row carries two allocation links:
- `AllocationID` → `Allocation` (aliased `allc1`) = **Operation**
- `AllocationID2` → `Allocation` (aliased `allc2`) = **Location**

Each `Allocation` row can itself carry an `AllocationRebateID` → the
allocation is independently rebate-linked regardless of the equipment's own
`EquipmentRebateID`. This feeds directly into SARS eligibility — see
`business-rules/sars-schedule6.md`.

## Missing allocation description

`AID1DescOperation`/`AID2DescLocation` come straight off the `Allocation`
row itself (`allc1.Description`/`allc2.Description`) and are independent of
`PerEquipmentAssetAllocation`. If these are blank, the `Allocation` record
itself has no description — a data-setup gap, distinct from the
`PerEquipmentAssetAllocationDesc` gap described in
`business-rules/sars-schedule6.md`. Don't conflate the two when
investigating a "missing description" complaint — check which of the two
description sources the customer actually means.

## Validation query

```sql
SELECT u.ID, u.AllocationID, allc1.Description AS OperationDesc,
       u.AllocationID2, allc2.Description AS LocationDesc
FROM UsageDispensing u
LEFT JOIN Allocation allc1 ON u.AllocationID  = allc1.ID
LEFT JOIN Allocation allc2 ON u.AllocationID2 = allc2.ID
WHERE u.AccountID = {AccountID} AND u.Createdate >= '{StartDate}'
  AND (allc1.Description IS NULL OR allc2.Description IS NULL);
```
