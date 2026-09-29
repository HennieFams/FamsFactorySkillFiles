# Equipment Integrity

- Equipment with `EquipmentID = 0` on dispensing rows (data quality, but
  also potentially a mis-provisioned nozzle).
- Equipment with abnormal manual-entry (`Recnumber = 'manualAdd'`) rate
  relative to peers at the same store — see
  `business-rules/equipment-validation.md`.
- Equipment flagged repeatedly in cross-source mismatches — see
  `investigation/equipment.md`.
