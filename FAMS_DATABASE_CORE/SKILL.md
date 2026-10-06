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

Each kind of data has one source of truth; the other tables are backups or raw
input. Picking the wrong one silently produces wrong numbers, and calling a
backup or raw table the source of truth is a reporting error (owner-confirmed,
2026-10-06):

| Layer | Table | Role |
|---|---|---|
| **Source of truth** | `UsageDispensing` | All dispensing transactions. Every reported dispensing figure comes from here. |
| **Source of truth** | `UsageTransfer` | All transfer transactions (dispensing into a bowser or another tank). |
| **Source of truth** | `UsageReceiving` | All receiving / offloading transactions. |
| **Source of truth** | `Stock` | All tank levels. |
| Backup | `UsageDispensingAndroid` | Dispensing backup from the Android control unit (links the Android device with the fuel pump). Carries the meter readings (`Totalizer`/`TotalizerEnd`). |
| Backup | `UsageDispensingIOT` | Dispensing backup from the IOT device, decoded from `IOTData_FMS`. |
| Raw | `TempTableDataJson` | Raw Android dispensing payloads behind `UsageDispensing`; the main raw source for Android accounts. Keyed by `Macaddress` (→ `Store.Macaddress`), `errorid` flag. |
| Raw | `IOTData_FMS` | Raw IOT dispensing records. Decoded into `UsageDispensingIOT`, **and into `UsageDispensing` only when that transaction isn't already there**. |
| Raw | `IOTData_ATG` | Raw IOT tank levels (behind `Stock`). |
| Raw | `IOTData_Notification` | Raw IOT device alerts. |
| Raw | `IOTData_Error` | Raw IOT tank errors. |

**Android accounts** (`android_accounts` in the integrity agent's
`config.json`): all ShipTech except 365 TWK Agri Underberg and 397 PMB Storage,
plus RAM Couriers (390, 391, 415 Bloemfontein). Only these have
`TempTableDataJson` payloads and an Android backup; TWK, PMB Storage and PMC
Phalaborwa are IOT-only. New Android sites must be added to that list.

Dispensing flow:

```
Android device -> TempTableDataJson (raw) -> UsageDispensing (truth)
               -> UsageDispensingAndroid (backup)
IOT device     -> IOTData_FMS (raw) -> UsageDispensingIOT (backup)
                                    -> UsageDispensing (only if not already present)
```

What follows from this:

- Volumes, totals and reconciliation % are computed from `UsageDispensing`.
- A `UsageDispensing` row with no IOT or Android record still counts; what's
  missing is its backup evidence ("unexplained", check C06).
- An IOT or Android record with no `UsageDispensing` row is fuel missing from
  client reporting (C08). An `IOTData_FMS` dispensing record that never reached
  `UsageDispensingIOT` or `UsageDispensing` is a decode gap (C25), and a
  `TempTableDataJson` payload on an Android account with no `UsageDispensing`
  (or Transfer/Receiving) row is a processing gap (C26).
- When `UsageDispensing` and a backup disagree on volume, `UsageDispensing`
  stands in the report and the difference is a finding to explain (C07). Use
  the raw table (`TempTableDataJson` for Android accounts, `IOTData_FMS` for
  IOT) to settle a disputed transaction.
- The tables join on `(AccountID, TransactionID)`. Android volume can also be
  derived from the meter: `ABS(TotalizerEnd - Totalizer)`.
- Tank figures come from `Stock`, transfers from `UsageTransfer` and
  receiving/offloading from `UsageReceiving`; the IOT telemetry tables
  (`IOTData_ATG`, `IOTData_Notification`, `IOTData_Error`) are raw input and carry `RecordTypeId` and `TypeID` as decoded columns
  alongside `DeviceId`/`DeviceAlias` and a `TelementryData` JSON blob.

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

Agents query FAMS only through `fams_db.py` (repo `fams-integrity-agent/scripts/`,
installed at `/paperclip/fams-integrity-agent/scripts/`): a lexing read-only guard, an always-rolled-back
transaction, and `ApplicationIntent=ReadOnly`. The shared login has admin rights, so
this guard is the only thing stopping a write — never bypass it.

## Prohibited

Production SQL. Schema drops. Reading secrets. Modifying data to make a report
reconcile.
