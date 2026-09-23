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
  status: DRAFT
  lastValidated: null
---

# FAMS Database Core

SQL Server (Azure SQL). Read this before writing a single query against FAMS data.

## Table hierarchy

FAMS tables fall into three roles, and picking the wrong one silently produces wrong
numbers:

- **Canonical** — the agreed source for a fact.
- **Decoded** — parsed or normalised from raw payloads.
- **Raw fallback** — used only when the canonical and decoded rows are absent.

> TO CONFIRM (Hennie): list the actual table names under each role before this skill
> moves from DRAFT to VALID. An agent must not guess which table is canonical for a
> given fact.

## Field semantics that are routinely misread

- **`EquipmentID`** is a reusable dispensing-point tag. It is **not** a device
  identifier. Two physically different devices can carry the same `EquipmentID` over
  time. Never use it to identify hardware.
- **Device identity** is established by `StoreID` + MAC address. Use that pair when
  the question is "which device".
- **`TypeID`** carries different meanings in `IOTData_FMS` and in `IOTData_ATG`. Never
  carry an interpretation across the two tables.
- **`UnqTrID`**, **`Recnumber`** and **`TransactionID`** are three distinct fields with
  three distinct roles. They are not interchangeable keys, and joining on the wrong one
  produces duplicates or silent row loss.

> TO CONFIRM (Hennie): write out the exact role of each of the three fields, and the
> `TypeID` value meanings per table. These are the facts agents most need and most
> easily invent.

## Daily boundary

06:00 SAST, not midnight. Every daily window, aggregate and reconciliation uses it.

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

## Prohibited

Production SQL. Schema drops. Reading secrets. Modifying data to make a report
reconcile.
