# Calculations

- **Meter-derived volume:** `ABS(TotalizerEnd - Totalizer)`
- **Cross-source delta:** `ABS(IOT.Volume - Android/Log.Volume)`,
  flagged when `> 0.1` (see `datasets/validation-rules.md`)
- **Z-score:** `(x - mean) / stdev` — see `algorithms/z-score.md`
- **Actual volume (for validating a specific transaction's recorded
  `Volume` against the raw meter) — use self-check FIRST, next-transaction
  diff only as a fallback:**

  1. **Primary: same-row self-check.**
     `ActualVolume(txn_i) = TotalizerEnd(txn_i) - Totalizer(txn_i)`, using
     that transaction's own `Totalizer`/`TotalizerEnd` pair in
     `UsageDispensingAndroid`, when both are valid (see "invalid values"
     below). This is usually close to circular — `Volume` is typically
     derived from this same pair at capture time — so it mostly confirms
     internal consistency rather than independence, but it's still the
     right first check and it's the *reliable* one.
  2. **Fallback: next-transaction diff, only when the row's own pair is
     unavailable.**
     `ActualVolume(txn_i) = Totalizer(txn_{i+1}) - Totalizer(txn_i)`,
     where `txn_{i+1}` is the next real (`Volume > 0`) row for the same
     nozzle — see `business-rules/nozzle-validation.md` for the nozzle key
     (`StoreID, ProductID, TrailerMac, InformationMac` — **not**
     `EquipmentID`).
     **Do not use this as the default/primary method** — confirmed
     false-positive source: it can span a real operational gap (no other
     transaction logged for hours) or, rarely, a totaliser reset/rollback
     between transactions, producing an enormous nonsense delta (hundreds
     to hundreds-of-thousands of litres) that has nothing to do with the
     transaction being checked. Always try the self-check first; only
     fall back to this when the self-check pair is invalid, and still
     treat a negative or wildly large fallback result as "unverifiable
     via this method" (see below), not as a finding.

  **Invalid values (apply to both methods) — don't compute, mark
  unavailable instead:**
  - `Totalizer`/`TotalizerEnd` == `0.0` (not-captured placeholder), or
  - the overflow sentinel `4294967.0`/`4294968.0`, or
  - the source row is itself a zero-`Volume` row (exclude entirely from
    the nozzle's sequence, don't just skip it as `txn_i`), or
  - (fallback only) the resulting diff is negative (totaliser regression
    — device reset/fault, not usable).

  **Totalizer availability is a per-nozzle hardware trait, not a
  per-transaction fluke** — checked empirically, a nozzle's zero-rate on
  `Totalizer` is bimodal (~100% or ~0%, never in between). A nozzle that
  never reports a usable totalizer can't be verified by *either* method —
  report it as "unverifiable" plainly, don't count it as clean just
  because nothing was flagged.

  Compare the result to `UsageDispensing.Volume` for that TransactionID;
  flag `|delta| > 2 L` as worth a look (deltas under ~2L are typically
  rounding at the totalizer's whole-litre resolution, not a real
  discrepancy — confirmed threshold from real portfolio data, Sept 2026).
