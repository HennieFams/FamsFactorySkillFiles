# Device Integrity

- IOT device volume disagreeing with Android/meter-derived volume beyond
  tolerance — see `algorithms/atg-reconciliation.md`.
- Payload errors in `TempTableDataJson.errorid != 0` for a device's
  Macaddress — trace via `datasets/field-definitions.md`.
- **BTLinkLost (Bluetooth link lost)** — `IOTData_Notification` rows with
  `RecordTypeID=99, TypeID=132`. Each row's `TelementryData` JSON carries a
  `TrId` and a `msg` string in the form
  `"BT Link lost on Prod:<n>, on TrId:<TrId> with <volume>L "`.
  1. Parse `TrId` and the volume out of `msg`
     (regex `with\s+([\d.]+)\s*L`).
  2. Join `(AccountID, TrId = UsageDispensing.TransactionID)` to get the
     matching `UsageDispensing.ID` / recorded `Volume`. **Search the full
     available dataset for this, not just the single export whose window
     is closest to the event** — a transaction can straddle a midnight
     boundary and land outside the file whose own date range starts the
     next morning. Confirmed false-"missing" case: TrId `YdNmUoNr1XNQ`
     (Cato Ridge) had `CreateDate` 23:48:23 on day N, and briefly looked
     unrecorded because it was only searched for in the day-N+1 export
     (whose data starts at 00:01 on day N+1). It was correctly present in
     the day-N export the whole time.
  3. Cross-check the recorded volume against the true meter reading using
     the totalizer-diff method in `datasets/calculations.md` § Actual
     volume, sourced from `UsageDispensingAndroid` (backup 2, which carries the meter readings)
     — **not** `UsageDispensing`'s own Totalizer columns, and **not**
     grouped by `EquipmentID` (see `business-rules/nozzle-validation.md`
     for why).
  4. A device/site that repeatedly dominates the portfolio's BTLinkLost
     count across multiple reporting windows (not just a one-off day) is
     the strongest signal — escalate that specific device for a hardware
     check rather than treating isolated counts as noise. Missing-
     EquipmentID dispensing rows co-occurring within ±5 min of a
     BTLinkLost event on the same account is a plausible causal link
     worth checking (device drops link mid-transaction → fails to tag
     EquipmentID).
  No confirmed tolerance threshold exists yet for BTLinkLost *event
  volume* (events/day per device) — until one is set, judge by portfolio
  distribution (which device/account is the outlier) rather than a fixed
  number.
- See `investigation/devices.md` and `investigation/networking.md` for
  fault tracing once a device is implicated.
