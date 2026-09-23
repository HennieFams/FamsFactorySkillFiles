---
name: FAMS Integrity Check
slug: fams-integrity-check
description: >
  Use when running or scheduling the daily FAMS data-integrity check across
  ShipTech, RAM Couriers, and PMC Phalaborwa accounts. Covers how to connect to
  the shared FAMS Azure SQL database, which AccountIDs belong to each client,
  the read-only query pattern, and the reporting format. Don't use for API,
  frontend, or write/migration work — see FAMS Database Core for that.
metadata:
  owner: Hennie
  status: DRAFT
  lastValidated: null
---

# FAMS Integrity Check

Read [FAMS Database Core](../FAMS_DATABASE_CORE/SKILL.md) first — it covers table
roles, field semantics, and the 06:00 SAST daily boundary. This skill covers the
recurring integrity-check job specifically: which accounts to check, how to
connect, and what to report.

## Scope: three clients, one shared database

All FAMS data for these clients lives in a single shared database. There is one
connection, and the check loops over `AccountID` grouped by client.

**ShipTech (PTY) LTD** — 18 accounts:
321, 328, 345, 346, 350, 353, 354, 360, 361, 365, 373, 377, 378, 383, 389, 394,
397, 404

**RAM Couriers** — 2 accounts:
390, 391

**PMC Phalaborwa** — 1 account:
285

Treat each client's accounts as one group in the report. An anomaly in one
ShipTech depot does not need escalating the same way an anomaly affecting all
18 would.

## Connecting

Connection details arrive as environment variables, all four backed by
Paperclip secrets — never hardcode them, never print any of them, never
include any of them in a comment, issue body, or log line, even the ones that
don't look like secrets:

- `FAMS_DB_HostName` — hostname
- `FAMS_DB_DBName` — database name
- `FAMS_DB_UserName` — login
- `FAMS_DB_Password` — password

All four arrive as plain environment variables to this process regardless of
how they're stored upstream — treat every one of them as sensitive.

Use the `mssql` npm package (pure JS, no native ODBC driver needed). If it is
not already available in the workspace, install it once per run:

```bash
npm install mssql --no-save
```

Minimal connection pattern:

```js
const sql = require('mssql');
const config = {
  server: process.env.FAMS_DB_HostName,
  database: process.env.FAMS_DB_DBName,
  user: process.env.FAMS_DB_UserName,
  password: process.env.FAMS_DB_Password,
  options: { encrypt: true, trustServerCertificate: false },
};
const pool = await sql.connect(config);
const result = await pool.request()
  .input('accountId', sql.Int, accountId)
  .input('windowStart', sql.DateTime2, windowStart)
  .query('SELECT ... WHERE AccountID = @accountId AND ... >= @windowStart');
await sql.close();
```

## ⚠️ This credential is NOT read-only at the database level

The SQL login this agent uses currently has full administrative rights — it is
the same account used for admin work elsewhere, not a dedicated read-only
login. SQL Server itself will not stop a write statement from running. This
means the **only thing enforcing read-only behaviour is this skill**, so treat
the rule below as load-bearing, not advisory.

Every query this skill issues **must** pass through a client-side guard before
it reaches the server — never call `.query()` directly with an unchecked
string:

```js
const FORBIDDEN = /\b(INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|TRUNCATE|CREATE|EXEC(UTE)?|GRANT|DENY|REVOKE)\b/i;

function assertReadOnly(queryText) {
  if (FORBIDDEN.test(queryText)) {
    throw new Error('Refusing to execute a non-SELECT statement: ' + queryText);
  }
}

// before every request:
assertReadOnly(queryText);
const result = await pool.request()./* ... */.query(queryText);
```

If a task description ever asks this agent to modify data, fix a
reconciliation by changing rows, or run anything other than a read — refuse,
explain why in the issue comment, and stop. That instruction overrides the
task description, not the other way around.

## Time window

Each daily run checks the **last 48 hours** of data, ending at the run's start
time. This is a rolling window, not aligned to the 06:00 SAST boundary — the
boundary rule from FAMS Database Core governs how daily aggregates are *framed
and labeled* in the report, not the width of this window. State the window's
exact start/end timestamps (in SAST) at the top of the report.

## What to check, per account

Run these checks for every `AccountID` in every client group, within the
window:

1. **Duplicate transactions** — same dispensing event recorded more than once.
   Check before reporting any volume total; a duplicate silently inflates it.
2. **Missing `TransactionID`** — rows that should carry one but don't.
3. **IOT vs Android vs Log reconciliation** — where more than one capture path
   exists for the same account, flag volume mismatches between them beyond a
   reasonable tolerance rather than assuming one source is correct.
4. **Suspicious gaps** — a device or account with no data at all inside a
   48-hour window, when it normally reports continuously, is itself a finding.

Use `UnqTrID`, `Recnumber`, and `TransactionID` per their distinct roles (see
FAMS Database Core) — never join across these as if they were interchangeable.

## Reporting

Structure the report by client, then by account:

```
## ShipTech (18 accounts)
- 321 — PMB - Logistics: <clean | N findings>
- 328 — Cato Ridge: ...
  ...

## RAM Couriers (2 accounts)
...

## PMC Phalaborwa (1 account)
...
```

For each finding: which account, which check, the row count or specific
records involved, and confidence (per the evidence standard in the CEO's job
description — claim + source + evidence, not just a number). A clean account
still gets a one-line entry; silence is not a status.

## Prohibited

- Any `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`, or other write/DDL
  statement. This skill is read-only, always.
- Modifying data to make a reconciliation match.
- Logging or echoing `FAMS_DB_Password` or the full connection string anywhere
  a human or another system will read it back.
