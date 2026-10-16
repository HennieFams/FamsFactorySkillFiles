---
name: factory-sql-shared
description: >
  NOT READY — do not assign to any agent yet. Placeholder for the SQL team (SQL Developer, SQL Tester) role skill in the
  new FAMS factory skill set. Will be written fresh from the code and Hennie's decisions.
---

# SQL team (SQL Developer, SQL Tester) — not written yet

Status: not started (see ../../REGISTRY.md). Agents must not load this skill.

## Sections planned
- Data lineage: UsageDispensing (source of truth), UsageDispensingIOT and UsageDispensingAndroid (backups), TempTableDataJson (raw for Android accounts), IOTData_FMS / _ATG / _Notification / _Error (raw IoT), Stock, UsageReceiving, UsageTransfer
- DEV database only; never production; masked extracts
- Naming and migration process (from the SQL audit, r5)

## Write it from
- Hennie's data-lineage statements (6 Oct)
- SQL audit r5 (pilot prep)
- FAMS_DATABASE_CORE (VALID 28 Sep) as a reference, not copied
