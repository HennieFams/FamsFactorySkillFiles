# Cost Centre Validation

`UsageDispensing.EquipmentCostCentreID` → `EquipmentCostCentre` (`ID`,
`Name`, `Description`). Straightforward FK — a dispensing row with a
non-null `EquipmentCostCentreID` that doesn't resolve to a
`EquipmentCostCentre` row is a referential integrity problem worth
flagging.

```sql
SELECT u.ID, u.EquipmentCostCentreID
FROM UsageDispensing u
LEFT JOIN EquipmentCostCentre cst ON u.EquipmentCostCentreID = cst.ID
WHERE u.AccountID = {AccountID} AND u.Createdate >= '{StartDate}'
  AND u.EquipmentCostCentreID IS NOT NULL AND cst.ID IS NULL;
```

<!-- Populate further with any org-specific cost-centre rules (e.g.
     required cost centre per equipment type, valid cost-centre/allocation
     combinations) once defined. -->
