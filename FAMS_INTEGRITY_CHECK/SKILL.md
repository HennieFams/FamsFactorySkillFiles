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

Each daily run checks **48 hours** of data, but the window's anchor point
differs by client — get this wrong and you silently shift or duplicate a
day's data:

- **ShipTech** — anchored to the most recently completed **06:00 SAST**
  boundary (per FAMS Database Core's daily-boundary rule). The window is
  `[anchor − 48h, anchor)`, where `anchor` is the most recent 06:00 SAST at or
  before the run's start time.
- **RAM Couriers and PMC Phalaborwa** — anchored to the most recently completed
  **midnight SAST**. The window is `[anchor − 48h, anchor)`, where `anchor` is
  the most recent midnight SAST at or before the run's start time.

**The container's system clock is UTC, not SAST.** South Africa does not
observe daylight saving, so SAST is always UTC+2 — but you must convert
explicitly rather than trust local system time to already be SAST. Compute
each anchor in SAST, then convert to UTC before querying (the database's
timestamps' own timezone should be confirmed against FAMS Database Core rather
than assumed).

State each client's exact window start/end, in both SAST and UTC, at the top
of that client's report — this is a common source of silent off-by-one-day
errors and should be auditable at a glance.

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

## Reporting: three separate PDFs, one per client

Produce **three distinct PDF files**, not one combined report — ShipTech's PDF
covers only ShipTech's 18 accounts, and so on. Each PDF is structured by
account:

```
FAMS Integrity Report — ShipTech
Window: 2026-09-22 06:00 SAST → 2026-09-24 06:00 SAST (04:00 → 04:00 UTC)

321 — PMB - Logistics: <clean | N findings>
328 — Cato Ridge: ...
...
```

For each finding: which account, which check, the row count or specific
records involved, and confidence (per the evidence standard in the CEO's job
description — claim + source + evidence, not just a number). A clean account
still gets a one-line entry; silence is not a status.

Generate the PDFs with the `pdfkit` npm package (pure JS, no native
dependencies) — install once per run if not already present:

```bash
npm install pdfkit --no-save
```

Name each file `FAMS-Integrity-<Client>-<YYYY-MM-DD>.pdf`, e.g.
`FAMS-Integrity-ShipTech-2026-09-24.pdf`, using the date the window ends.

## Emailing the reports

After generating all three PDFs, email each one separately using the internal
FAMS endpoint — this call needs no API key or auth header (it is
network-trust only), just a plain HTTPS POST:

```js
const https = require('https');

function sendReportEmail({ toAddress, subject, bodyHtml, pdfBuffer, reportName }) {
  const payload = JSON.stringify({
    email: toAddress,
    subject,
    body: bodyHtml,
    fileName: `${reportName}.pdf`,
    fileContentBase64: pdfBuffer.toString('base64'),
  });
  return new Promise((resolve, reject) => {
    const req = https.request(
      'https://api24.fams.co.za/api/SendGrid/SendMessageEmailWithAttachment',
      { method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } },
      (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.statusCode);
        else reject(new Error(`Send failed: HTTP ${res.statusCode}`));
      },
    );
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}
```

The endpoint accepts **one recipient per call** — there is no comma-separated
or list form. Send each of the three client PDFs to each of the four
recipients separately (12 calls total per run):

```
hennie@fams.co.za
franco@fams.co.za
schalk@fams.co.za
werner@fams.co.za
```

Subject line: `FAMS Integrity Report — <Client> — <YYYY-MM-DD>`. Keep the HTML
body short — a one-line summary (e.g. "3 findings across 18 accounts, see
attached") is enough; the PDF carries the detail.

If any of the 12 sends fails, report the failure in the issue comment (which
recipient, which client, the HTTP status) rather than silently retrying more
than once. Do not treat a partial send (some recipients succeeded, others
didn't) as a reason to re-send to everyone — retry only the failed ones, once.

## Prohibited

- Any `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`, or other write/DDL
  statement. This skill is read-only, always.
- Modifying data to make a reconciliation match.
- Logging or echoing `FAMS_DB_Password` or the full connection string anywhere
  a human or another system will read it back.
