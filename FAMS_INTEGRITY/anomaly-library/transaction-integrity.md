# Transaction Integrity

Checks that a transaction's reported volume is internally consistent
across every source that recorded it:

- `UsageDispensing.Volume` (as reported/possibly reconciled)
- `UsageDispensingIOT.Volume` (device-reported)
- `ABS(UsageDispensingAndroid.TotalizerEnd - UsageDispensingAndroid.Totalizer)` (meter-derived)

Disagreement beyond tolerance (commonly 0.1 L in this org's queries) is the
core signal. See `algorithms/atg-reconciliation.md` for the queries.
