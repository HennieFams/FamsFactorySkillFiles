# Equipment Investigation

1. Pull equipment record: `SELECT * FROM Equipment WHERE AccountID = {AccountID} AND [tag] = '{tag}'` (or by EquipmentID)
2. Pull its transaction history in the review window.
3. Run `algorithms/duplicate-detection.md` and `algorithms/atg-reconciliation.md` scoped to this EquipmentID.
4. Compare its manual-entry (`Recnumber = 'manualAdd'`) rate against peer equipment at the same store.
