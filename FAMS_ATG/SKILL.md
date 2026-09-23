---
name: FAMS ATG
slug: fams-atg
description: >
  Use when working with automatic tank gauging data — tank level readings, ATG
  telemetry, ATG device behaviour, or reconciliation between ATG movements and
  dispensing records. Covers the vendors in the FAMS estate and the failure modes that
  produce plausible-looking wrong numbers. Don't use for dispenser or flowmeter
  transaction logic.
metadata:
  owner: Hennie
  status: DRAFT
  lastValidated: null
---

# FAMS ATG

Automatic Tank Gauging supplies tank level readings into FAMS.

## Estate

Veeder-Root, Gilbarco, TCS/EMR, Piusi, Teltonika, Siemens IOT2050, PLCs, flowmeters,
Android devices, Azure IoT. Vendor behaviour differs — a protocol assumption that holds
for one does not automatically hold for another.

> TO CONFIRM (Hennie): which ATG vendors are actually deployed at which client sites,
> and where the per-vendor quirks are documented.

## `TypeID` warning

`TypeID` in `IOTData_ATG` does not mean what `TypeID` means in `IOTData_FMS`. Never
carry an interpretation between the two tables. See FAMS_DATABASE_CORE.

## Failure modes that produce plausible wrong answers

- **Stale readings.** The last reading persists in the table. Nothing in the row says
  "this is old" — you must compare its timestamp against now.
- **Offline / retry behaviour.** Devices buffer and replay. A batch of readings can
  arrive late, out of order, or duplicated. Ordering by insert time rather than reading
  time gives the wrong picture.
- **Delivery vs dispensing.** A rising level is normally a delivery; a falling level is
  normally dispensing. Normally. Temperature, water ingress, dipping and manual
  transfers all move a level without a matching transaction.

## Reconciliation

When ATG movement and dispensing records disagree, the disagreement is the finding —
do not "fix" either side to make them match. Report the delta, the window, the tank,
the site and the confidence, and let a human decide.

The daily boundary for any ATG reconciliation window is 06:00 SAST.
