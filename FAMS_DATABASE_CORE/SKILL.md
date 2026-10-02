---
name: FAMS Database Core
slug: fams-database-core
description: >
  Use when writing or reviewing any FAMS SQL — queries, stored procedures, views,
  schema changes or migrations — and when interpreting FAMS transaction data. Covers
  the table hierarchy, the field semantics that are commonly misread, and the
  migration rule. Don't use for API or frontend work.
metadata:
  owner: Hennie
  status: VALID
  lastValidated: 2026-09-28
---

# FAMS Database Core

SQL Server (Azure SQL). Read this before writing a single query against FAMS data.

## Table hierarchy

FAMS tables fall into three roles, and picking the wrong one silently produces wrong
numbers:

- **Canonical** — `UsageDispensing`. The agreed source for a dispensing transaction:
  `ID` (PK), `AccountID`/`StoreID`/`EquipmentID` (scoping), `Volume`/`OrigVolume`,
  `Createdate`, `TransactionID`, `UnqTrID`, `InformationRec` (JSON), `Recnumber`,
  `AllocationID`/`AllocationID2`, `EquipmentCostCentreID`, `ProductID`, `Hour`/`KM`.
- **Decoded** — `UsageDispensingIOT` (IOT-device-reported version; joins to
  `UsageDispensing` and `UsageDispensingAndroid` on `(AccountID, TransactionID)`),
  `UsageDispensingAndroid` (Android-handheld log; volume via
  `ABS(TotalizerEnd - Totalizer)`), and the raw telemetry tables `IOTData_FMS` /
  `IOTData_ATG` / `IOTData_Notification` / `IOTData_Error`, which carry `RecordTypeId`
  and `TypeID` as decoded columns (not just inside the JSON blob) alongside
  `DeviceId`/`DeviceAlias` and a `TelementryData` JSON blob.
- **Raw fallback** — `TempTableDataJson`. Raw inbound JSON payloads keyed by
  `Macaddress` (→ `Store.Macaddress`), with an `errorid` flag. Used only when the
  canonical and decoded rows are absent; not consumed by the automated daily check,
  useful for manual investigation of a specific disputed transaction.

Supporting tables: `Account`/`Store`/`Equipment` (Account.name searchable via LIKE;
Store.AccountID and Equipment.AccountID are FKs; Equipment.[tag] is the physical/RFID
tag), `Stock` (ATG tank readings), `TANK` (case-insensitive with `Tank`).

## Field semantics that are routinely misread

- **`EquipmentID`** is a reusable dispensing-point tag. It is **not** a device
  identifier. Two physically different devices can carry the same `EquipmentID` over
  time. Never use it to identify hardware.
- **Device identity** is established by `StoreID` + MAC address. Use that pair when
  the question is "which device".
- **`TypeID`** carries different meanings in `IOTData_FMS` and in `IOTData_ATG`. Never
  carry an interpretation across the two tables. Every row also carries a separate
  **`RecordTypeId`** (which table/envelope this row belongs to — constant per table:
  `1`=FMS, `2`=ATG, `99`=Notification, `123`=FMC) — conflating `RecordTypeId` with
  `TypeID` was a real, confirmed bug (see below). Full mapping:

  | RecordTypeId | Table | TypeID | Meaning |
  |---|---|---|---|
  | 1 | FMS | 1 | Dispensing |
  | 1 | FMS | 2 | Transfer |
  | 1 | FMS | 3 | Offloading |
  | 1 | FMS | 4 | Complete (transaction-complete marker, not itself a movement) |
  | 2 | ATG | 1 | Level (routine tank reading) |
  | 2 | ATG | 2 | Received (fill complete) |
  | 2 | ATG | 3 | RapidDrop (drop complete) |
  | 2 | ATG | 4 | ReceivingStart (fill start) |
  | 2 | ATG | 5 | RapidDropStart (drop start) |
  | 2 | ATG | 99 | ATGError (sensor-fault flag) |
  | 99 | Notification | 1 | Startup |
  | 99 | Notification | 2 | NotifyTag |
  | 99 | Notification | 3 | NoFlow |
  | 99 | Notification | 9 | DispenseDuringFill |
  | 99 | Notification | 10 | Recovery alert |
  | 99 | Notification | 124 | DispTransactionComplete — event-end marker |
  | 99 | Notification | 125 | DispStartNow — event-start marker |
  | 99 | Notification | 132 | BTLinkLost |
  | 99 | Notification | 205 | ATGOverfill |
  | 123 | FMC | 1 | Power |
  | 123 | FMC | 2 | Override |

  (Full list including minor notification codes: `datasets/IOTRecordType.csv` in the
  `fams-integrity` skill.) **Open question, not yet resolved**: `RecordTypeId=123`
  (FMC) doesn't correspond to any documented base table — if a raw `IOTData_FMC`
  table exists, confirm its structure before relying on it.

  **Corrected 2026-08-21**: FMS TypeID 2/3 had previously been documented and coded
  backwards (as Offloading/Receiving). The correct mapping is 2=Transfer,
  3=Offloading, confirmed by the account owner's own `IOTRecordType.csv`. TypeID 4
  ("Complete") wasn't recognized at all and was being silently flagged as an
  unexpected/unknown TypeID. Treat any report generated before this date as suspect
  on this point.

- **`UnqTrID`**, **`Recnumber`** and **`TransactionID`** are three distinct fields with
  three distinct roles. They are not interchangeable keys, and joining on the wrong one
  produces duplicates or silent row loss:
  - **`TransactionID`** — the legacy transaction identifier field on
    `UsageDispensing`, used to join across `UsageDispensing`, `UsageDispensingIOT`,
    and `UsageDispensingAndroid` on `(AccountID, TransactionID)`. Also present inside
    `InformationRec`'s JSON blob, but **the key name is inconsistent across
    accounts** — seen as `$.transactionID`, `$.transactionId`, and `$.TransactionID`.
    Always detect the correct key per account before backfilling from JSON.
  - **`UnqTrID`** — the reconciled unique transaction ID. `'N/A'` or `NULL` means the
    transaction is unreconciled — this is the field that actually tells you whether
    reconciliation succeeded, not `TransactionID`.
  - **`Recnumber`** — provenance/import-batch marker, e.g. `'manualAdd'`,
    `'importFams'`, or a dated/numeric batch code. A value outside the known batch
    codes is a candidate (not automatic proof) for a manual entry — confirm known
    batch values with the account owner before flagging based on this alone.

## Daily boundary

06:00 SAST, not midnight. Every daily window, aggregate and reconciliation uses it,
except for the human-approved per-client exceptions listed in FAMS Core (§ Reporting
convention) — currently RAM Couriers and PMC Phalaborwa at 00:00 SAST.

## Migration rule (§27)

Up + recovery/down + validation + dependency check + rollback. A migration without a
tested rollback is not finished. Migrations require human approval before they are
applied anywhere beyond DEV.

## Dependency awareness (§11.3)

A schema change propagates: schema → stored procedure → repository → service → API →
Vue → report. Before proposing a change, state which of those it touches. A change
that breaks an SSRS report is not a successful change.

## Known failure patterns

Duplicate transactions and missing `TransactionID` values are recurring FAMS data
integrity problems. If a query result looks too high, check for duplicates before
reporting the number.

## Read-only access from agents

Agents query FAMS only through `fams_db.py` (in `FAMS_INTEGRITY/scripts/` and
`FAMS_INTEGRITY_CHECK/scripts/`): a lexing read-only guard, an always-rolled-back
transaction, and `ApplicationIntent=ReadOnly`. The shared login has admin rights, so
this guard is the only thing stopping a write — never bypass it.

## Prohibited

Production SQL. Schema drops. Reading secrets. Modifying data to make a report
reconcile.
