# Nozzle Validation

## Nozzle identity — do NOT use EquipmentID

`EquipmentID` is not a reliable nozzle identifier: it's sometimes 0/NULL on
otherwise-real dispensing rows (see `anomaly-library/data-quality.md`), and
a single `EquipmentID` can appear across rows that don't actually share a
physical meter.

The confirmed reliable key for "same physical nozzle" is, from
`UsageDispensingAndroid` (backup 2, which carries the meter readings):

```
(StoreID, ProductID, TrailerMac, InformationMac)
```

- `InformationMac` — the FMS controller device's own MAC.
- `TrailerMac` — distinguishes multiple physical nozzles/hoses wired to the
  same controller at the same store+product.
- Treat NULL `TrailerMac`/`InformationMac` as their own explicit group
  value (don't drop those rows from the grouping).

Plain `(StoreID, ProductID)` alone is **not** sufficient — confirmed cases
in this org's data where two distinct nozzles share a Store+Product.

## Totalizer availability is a per-nozzle hardware trait, not per-transaction

Checked empirically: `Totalizer` zero-rate per
`(StoreID, ProductID, TrailerMac)` group is bimodal — each nozzle reports a
real totalizer on **either ~100% or ~0%** of its transactions, never a mix.
So a `Totalizer` reading of 0 on a transaction from a nozzle that normally
*does* report a totalizer is a genuine capture-failure signal; the same 0
on a nozzle that *never* reports one is just that hardware's normal
behaviour and not itself an anomaly. Don't flag every zero as an error —
check the nozzle's baseline rate first.

Two sentinel values must be excluded before treating `Totalizer` as a real
reading (see `datasets/calculations.md` for the full rule):
- `0.0` — not-captured placeholder
- `4294967.0` / `4294968.0` — 32-bit-unsigned overflow/error sentinel
  (`2^32/1000 ≈ 4294967.296`)

Also exclude zero-`Volume` rows from the nozzle's totalizer sequence
entirely — their totalizer snapshot is stale/unrelated to real dispensing
and will corrupt a next-transaction lookup if left in.

## Totaliser continuity

Readings on a nozzle must chain: each transaction's start = the previous
transaction's end (±2 L). A jump is a skipped/unrecorded volume or a reset.
Full rule, IOT `TotaliserFromComms` caveat and SQL:
`algorithms/totaliser-continuity.md`.
