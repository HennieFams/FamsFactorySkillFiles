---
name: factory-database-core
description: >
  NOT READY — do not assign to any agent yet. FAMS_DATABASE_CORE (Blueprint Rev 2 §79): database knowledge for the SQL Developer, and for
  Research / Architecture and the Unit Tester (SQL tests on DEV only). Will be written fresh from the code and Hennie's decisions.
---

# FAMS database core (FAMS_DATABASE_CORE) — not written yet

Status: not started (see ../../REGISTRY.md). Agents must not load this skill.

## Sections planned
- Data lineage: UsageDispensing (source of truth), UsageDispensingIOT and UsageDispensingAndroid (backups), TempTableDataJson (raw for Android accounts), IOTData_FMS / _ATG / _Notification / _Error (raw IoT), Stock, UsageReceiving, UsageTransfer
- DEV database only; never production; masked extracts
- Naming and migration process (from the SQL audit, r5)

## Write it from
- Hennie's data-lineage statements (6 Oct)
- SQL audit r5 (pilot prep)
- FAMS_DATABASE_CORE (VALID 28 Sep) as a reference, not copied
