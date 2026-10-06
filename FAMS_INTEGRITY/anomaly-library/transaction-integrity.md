# Transaction Integrity

Checks that a transaction's reported volume is internally consistent
across every source that recorded it:

- `UsageDispensing.Volume` — **source of truth** (what the client is reported)
- `UsageDispensingIOT.Volume` — backup from the IOT device (decoded from `IOTData_FMS`)
- `ABS(UsageDispensingAndroid.TotalizerEnd - UsageDispensingAndroid.Totalizer)` — backup from the Android control unit (meter-derived)

A backup that disagrees doesn't override `UsageDispensing`; the difference is
the finding. A backup record with no `UsageDispensing` row is fuel missing from
reporting (C08), and an `IOTData_FMS` dispensing record that reached neither
`UsageDispensingIOT` nor `UsageDispensing` is a decode gap (C25).

Disagreement beyond tolerance (commonly 0.1 L in this org's queries) is the
core signal. See `algorithms/atg-reconciliation.md` for the queries.
