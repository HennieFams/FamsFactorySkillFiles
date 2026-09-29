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

## Going deeper: FAMS Integrity

[FAMS Integrity](../FAMS_INTEGRITY/SKILL.md) is the full investigation knowledge
base this daily check is a fixed, automated subset of — algorithms, an anomaly
library, business rules, and per-domain investigation guides. You don't need to
read all of it every run; consult the specific file when a finding needs deeper
reasoning than the four automated checks below provide, or when something looks
like it might be one of the categories out of scope for this daily job (see
below). Each of this skill's checks traces back to a canonical file there:

| This check | FAMS Integrity source |
|---|---|
| Duplicate transactions | `algorithms/duplicate-detection.md` |
| Missing TransactionID, IOT/Android/Log reconciliation | `algorithms/atg-reconciliation.md`, `anomaly-library/transaction-integrity.md` |
| Suspicious gaps / data-gap handling | `anomaly-library/data-quality.md` |
| Tank-linked offload equipment, manual-entry candidates | `anomaly-library/equipment-integrity.md` |
| Tank opening/closing/capacity | `investigation/tank.md` |
| ATG fill/drop events, erratic-telemetry | `investigation/atg.md`, `algorithms/atg-reconciliation.md` |
| Communication health / near-empty-tank downgrade | `anomaly-library/device-integrity.md`, `investigation/devices.md` |

**Deliberately out of scope for this automated daily job** (this stays true
even though you now have the deeper skill available): fraud indicators,
employee-level behavioural analysis, equipment/nozzle/cost-centre validation,
seasonal and predictive anomaly detection, and SARS Schedule 6 reporting. If
something in this run's data looks like one of these, say so as a finding
(status Monitor or Investigate, per the categories below) and note that it
needs a human using FAMS Integrity directly — don't independently reach a
fraud or SARS-compliance conclusion inside this automated daily report.

## Scope: three clients, one shared database

All FAMS data for these clients lives in a single shared database. There is one
connection, and the check loops over `AccountID` grouped by client.

**ShipTech (PTY) LTD** — 18 accounts per the account master, but only 17 have
ever actually appeared in confirmed reporting data:
321, 328, 345, 346, 350, 353, 354, 360, 361, 365, 373, **377**, 378, 383, 389,
394, 397, 404

**⚠️ Unresolved discrepancy — do not silently resolve this either way.**
AccountID `377` ("Retail (Zimbabwe)" per the account master) does **not**
appear in the confirmed 17-account ShipTech map that `fams-daily-report` has
validated across multiple reporting windows. This could mean it's a
legitimate account with no activity in the windows checked so far, or there's
a real reason it doesn't belong in a SAST-anchored daily check (different
system, currency, or timezone for Zimbabwe operations). Include it in the
check, but if it genuinely has zero rows across the whole 48-hour window,
report that explicitly as "no data — unconfirmed account, needs owner
sign-off" rather than either silently treating it as clean or silently
dropping it from the report.

**RAM Couriers** — 2 accounts:
390, 391

**PMC Phalaborwa** — 1 account:
285

Treat each client's accounts as one group in the report. An anomaly in one
ShipTech depot does not need escalating the same way an anomaly affecting all
18 would.

## ShipTech-specific known patterns (confirmed, not hypothetical)

These are empirically confirmed across multiple real reporting windows —
treat them as a starting prior, but don't skip re-checking when the evidence
doesn't match:

- **Tank-linked offload equipment** (MAC-format `TransactionID`, non-standard
  `Recnumber`, otherwise looks like "unexplained dispensing"): confirmed at
  Cato Ridge (EquipmentID 26409), Piet Retief (30817); recurring but still
  pending account-owner sign-off at Nelspruit (31602), TWK Interlink (29307),
  Kokstad (29365), PMB (37571). Don't treat these as fresh anomalies each run,
  but don't add a new EquipmentID to this list without owner confirmation
  either.
- **Recnumber `4627x+` batch series** — a large-volume (600–40,000+ L)
  transfer/offload record with a MAC-prefixed `TransactionID` on one of the
  equipment IDs above is a known, confirmed pattern, not a manual-entry or
  fraud indicator, even though it falls outside the normal batch-recnumber
  format.
- **Confirmed duplicate-write bug (TWK Interlink, PMB)**: the same physical
  transfer/offload event gets written to `UsageDispensing` twice — once via
  the batch-transfer import, once via `importFams` — seconds apart, same
  `TransactionID`/`UnqTrID`/`Volume`/`EquipmentID`. If a duplicate-transaction
  finding matches this exact signature, cite the known bug rather than
  reporting it as a generic new duplicate.
- **Telemetry-outage false positive**: before reporting a low reconciliation
  percentage or a large "unexplained dispensing" total as a possible fraud or
  data-integrity issue, check whether the raw device tables
  (`UsageDispensingAndroid`/`UsageDispensingIOT`) simply stopped reporting for
  a stretch of hours while `UsageDispensing` kept logging normally through a
  different path. A real outage shows as a large gap in consecutive
  `Createdate` values, not an even trickle — cross-check against `Stock`/ATG
  readings for the same store to confirm a site-wide outage.
- **Cross-day matching**: a transaction can straddle the day boundary (e.g.
  23:48 on day N) and simply not exist in the file whose own window starts at
  the boundary on day N+1. When checking whether something is "missing,"
  search the full 48-hour window's data, not just the half of it closer to
  the event.

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

## Reporting: one branded management report per client, plus a technical workbook

Produce **three distinct PDF files**, one per client (ShipTech, RAM Couriers,
PMC Phalaborwa) — not one combined cross-client report. Each is a management
report covering that client's whole account portfolio, matching this
structure (this is the finalised, already-proven format used elsewhere at
Tecmo Automation for the same kind of daily check — follow it exactly rather
than reverting to a flat per-account list). Use the same full structure for
RAM Couriers (2 accounts) and PMC Phalaborwa (1 account) as for ShipTech — a
one- or two-row Portfolio Summary table is still a table; don't shrink the
report's structure just because there's less to put in it:

**Header** — client name and reporting window, e.g. "ShipTech (PTY) LTD —
Portfolio | 18 accounts" and "Reporting window: 2026-09-27 06:00 to
2026-09-29 06:00 SAST". Use a simple styled text header (bold client name,
an accent rule) rather than an external logo image — no image asset ships
with this skill, and inventing one is out of scope.

**01 Quick Stats** — six KPI cards, computed exactly as follows, never as raw
row counts:
- **Anomalies detected** — count of *grouped* findings with status
  Investigate or Monitor. A device with 600 repeated identical errors is
  ONE finding, not 600 — see grouping discipline below.
- **Total fuel dispensed** — sum of dispensing `Volume` in the window,
  across the whole client portfolio.
- **Reconciliation %** — `(total_litres - unexplained_litres -
  mismatch_litres) / total_litres`. State the numerator and denominator
  every time. Never fold an IOT-internal-only gap into this number.
- **Sites with possible fuel loss** — count of distinct accounts with an
  open possible-fuel-loss finding (status Investigate specifically).
- **Sites with communication failures** — count of distinct devices over
  the communication-error tolerance (10 per device per window; see
  Tolerances below) — not just devices with any errors at all.
- **Tanks at risk of running dry** — a forward 24h/48h/72h forecast needs
  multi-day consumption history. This is a single 48-hour check, so report
  **0 with an explicit caveat** ("insufficient history for a run-dry
  forecast") rather than inventing a projection from one window.

No financial values or fuel prices appear anywhere in this report.

**02 Executive Summary** — one prose paragraph covering the window, the
overall reconciliation picture, and calling out (by name) anything that
needs attention this run, plus which sites had no findings.

**03 Portfolio Summary** — a table, one row per account: Account name
(client-name prefix auto-stripped — compute this from the actual account
names each run, e.g. "ShipTech (PTY) LTD - Cato Ridge" → "Cato Ridge", not
hardcoded to one client's naming convention), Dispensed (L), Recon %,
Anomalies, Comm. Fail. Use `n/a` for Recon % on an account with zero
dispensing volume in the window rather than a divide-by-zero or a fabricated
percentage.

**04 Items for Management (Investigate)** — a table for every finding
classified `Investigate` only: Account, Category, Affected (the litres or
count involved), Note (what happened, possible cause using the language
discipline below, and a recommended next step). Omit this whole section if
there are none this run — don't render an empty table.

**05 Monitoring Items** — findings classified `Monitor`, grouped by kind
(e.g. "ATG telemetry noise" as a table of Account/Tank/Window; "Communication
errors explained by near-empty tanks" as a table of Account/Device/Errors/
Note). Add a one-line caveat under each sub-table explaining why these don't
need action (e.g. "most coincide with normal daytime dispensing activity...
no action required unless a specific tank is also flagged under possible fuel
loss").

**06 No Action Required** — a short bullet list: which accounts had zero
findings this period, the count of sites/tanks with a confirmed
possible-fuel-loss finding (should match Quick Stats), and a line confirming
no financial values/individuals/due dates are assigned per reporting policy.

**07 Data Quality & Methodology Note** — state plainly which optional data
sources this run actually had (e.g. `UsageDispensingAndroid`,
`UsageTransfer`/`UsageReceiving`, `IOTData_ATG`), and for anything missing,
say so explicitly rather than treating an unavailable source as "clean" — the
correct posture for a missing source is "unverifiable with current data," not
silence or a false all-clear.

**08 Technical Appendix** — a short pointer to the companion Excel workbook
(see below) and what's in it.

### Status vocabulary — exactly these three, nothing else

- **Investigate** — real discrepancy, possible fuel loss, device over
  tolerance, tank variance over tolerance, unexplained transaction, duplicate
  affecting totals, possible manual entry, run-dry risk, or missing data that
  blocks reconciliation.
- **Monitor** — minor/incomplete evidence, within tolerance but unusual, a
  repeated pattern that might matter later, or a data-confidence warning
  (e.g. erratic telemetry) that isn't itself a confirmed event.
- **No action required** — fully reconciled, within tolerance, a rapid-drop
  event fully explained, a delayed record that arrived within grace period,
  a device at or under the error tolerance, or purely informational.

Never state a due date, assigned individual, or responsible team against a
finding — only what happened, why it matters, possible cause(s), evidence,
and a recommended next step.

### Tolerances

- Volume/tank variance: 1% or less is acceptable (`volume_tolerance_pct`).
- Communication errors: up to 10 per device per window is acceptable
  (`comm_error_tolerance`). If the erroring device's tank volume is flat and
  near-zero throughout (≤10 L, `near_empty_tank_litres`), that's a
  near-empty-tank explanation (Monitor), not a device fault.
- A missing Operator alone is never an anomaly.
- Zero-volume dispensing rows with no raw match are informational, not
  anomalies — don't count their litres in the unexplained total.
- An "unexplained" dispensing transaction on a confirmed tank-linked offload
  `EquipmentID` (see FAMS Integrity Check's ShipTech-specific known patterns
  above) is confirmed offloading, not a dispensing gap.
- A `Recnumber` outside the known batch-import values is a candidate for a
  possible manual entry, not automatic proof — this business has historically
  had no manual dispensing entries, so treat an out-of-set value as worth
  flagging, not silently accepting.

### Language discipline

Always say "possible cause" unless proven. Never assert theft, fraud, or
confirmed loss from tank/telemetry data alone — only "possible unexplained
fuel loss," paired with an explicit statement that the finding is unconfirmed
and needs field verification (a physical dip-stick check, invoice
reconciliation, etc.).

### Grouping discipline

Group findings by shared site/device/tank/category/root-cause/time-window.
Preserve every underlying record as evidence (in the technical workbook, not
the PDF), but never surface hundreds of identical repeated errors as hundreds
of separate management findings — that buries the one that actually matters.

Generate the PDF with the `pdfkit` npm package (pure JS, no native
dependencies) — install once per run if not already present:

```bash
npm install pdfkit --no-save
```

Name each file `FAMS-Integrity-<Client>-<YYYY-MM-DD>.pdf`, e.g.
`FAMS-Integrity-ShipTech-2026-09-24.pdf`, using the date the window ends.

### PDF styling — this is load-bearing, not cosmetic

A management report with words split mid-character or a KPI card that reads
as a bare wrapped text block isn't a finished deliverable. **Every** call to
`doc.text()` inside a table cell or KPI card **must** pass an explicit
`width` option — this is what makes `pdfkit` wrap at word boundaries instead
of an uncontrolled overflow that can visually break mid-word. Never place
text at a fixed `x`/`y` with no `width` inside anything resembling a column
or a box.

**Page setup**: A4, `size: 'A4'`, margins of `50` on all sides, `Helvetica`
family (built into `pdfkit`, no extra install) for body text, `Helvetica-Bold`
for headings/KPI numbers.

**Colors** (reuse this exact palette — it's the house style already in use
elsewhere at Tecmo Automation for this same kind of report): orange `#E8720C`
for section numbers/accents, navy `#1F2A44` for headings, dark `#2B2B2B` for
table header fills, light `#F4F1EC` for KPI-card backgrounds and table
zebra-striping.

**Table columns**: compute each column's width from the actual content that
will go in it (measure with `doc.widthOfString()` against a sample of the
real values for that run, plus padding), not equal division of the page
width — a "Note" column needs far more room than an "Account" column. If the
computed widths don't fit the content width, reduce font size before you
start shrinking a column below a safe minimum (~60pt), and never let a column
get narrow enough that a word inside it can't fit on one wrapped line by
itself.

**Worked pattern** — a header-styled, word-wrapped table row (adapt column
count/widths per section; row height must be computed from the tallest
cell's actual wrapped line count, not a fixed guess):

```js
function drawTableRow(doc, x, y, cells, colWidths, opts = {}) {
  const { isHeader = false, fillColor = null, font = 'Helvetica', fontSize = 9, padding = 6 } = opts;
  doc.font(isHeader ? 'Helvetica-Bold' : font).fontSize(fontSize);

  // Row height = tallest wrapped cell, computed BEFORE drawing anything
  let rowHeight = 0;
  cells.forEach((cell, i) => {
    const h = doc.heightOfString(String(cell), { width: colWidths[i] - padding * 2 });
    rowHeight = Math.max(rowHeight, h + padding * 2);
  });

  if (fillColor) {
    doc.rect(x, y, colWidths.reduce((a, b) => a + b, 0), rowHeight).fill(fillColor);
  }
  doc.fillColor(isHeader ? '#FFFFFF' : '#2B2B2B');

  let cx = x;
  cells.forEach((cell, i) => {
    doc.text(String(cell), cx + padding, y + padding, {
      width: colWidths[i] - padding * 2,   // <- the width option is what prevents mid-word splitting
      align: 'left',
    });
    cx += colWidths[i];
  });

  return rowHeight; // caller advances y by this before the next row
}
```

**KPI cards**: fixed-size boxes (e.g. ~150×70pt), arranged in a 3×2 grid, each
with a filled `#F4F1EC` rounded rect (`doc.roundedRect(x, y, w, h,
6).fill(...)`), the number in large bold (`fontSize(24)`) centered, and the
label below it in smaller regular text (`fontSize(9)`) — always with a
`width` matching the card's inner width so a longer label (e.g. "Sites with
communication failures") wraps onto two lines within the card rather than
overflowing it.

**Before finalizing**: after generating each PDF, do a final sanity pass —
re-extract its text (e.g. a quick `pdf-parse` read, or re-reading your own
layout computation) and check for any word that got split mid-character. If
you find one, that column was too narrow for its content; widen it or reduce
font size and regenerate, rather than shipping a report with broken text.

### Companion technical workbook

Alongside each client's PDF, produce one Excel workbook with five sheets,
using the `exceljs` npm package (install once per run if not already
present: `npm install exceljs --no-save`):

- **Portfolio Summary** — same rows/columns as the PDF's Portfolio Summary
  table.
- **All Findings** — every Investigate/Monitor finding, one row each, tagged
  by account, with the full evidence (not summarized) that backs it.
- **Dispensing Detail** — every dispensing transaction across every account
  in the client's portfolio, with its classification (per the TypeID table
  in FAMS Database Core) and which check (if any) flagged it.
- **Tank Reconciliation** — opening/closing/capacity detail per tank, every
  account.
- **Data Gaps & Audit** — every assumption, estimate, and missing data
  source used this run, per account — this is where "unverifiable with
  current data" gets recorded in full rather than just mentioned in prose.

Name it `FAMS-Integrity-<Client>-Technical-<YYYY-MM-DD>.xlsx`. Don't email
this workbook to the four recipients (see below) — attach it to the issue as
a work product instead, and reference it by name in the PDF's Technical
Appendix section, so it's available for deeper investigation without adding
four more email sends per client every day.

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
