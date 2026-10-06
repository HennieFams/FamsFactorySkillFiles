---
name: FAMS Integrity Check
slug: fams-integrity-check
description: >
  Use when running or scheduling the daily FAMS data-integrity check across
  ShipTech, RAM Couriers, and PMC Phalaborwa accounts. Covers the deterministic
  check engine (fams-integrity-agent code pack), the read-only database access rules,
  which AccountIDs belong to each client, each client's reporting window, and
  the branded PDF + workbook + email format. Don't use for API, frontend, or
  write/migration work — see FAMS Database Core for that.
metadata:
  owner: Hennie
  status: DRAFT
  lastValidated: null
---

# FAMS Integrity Check

Read [FAMS Database Core](../FAMS_DATABASE_CORE/SKILL.md) first — it covers table
roles, field semantics, and the reporting-boundary rule. This skill covers the
recurring integrity-check job specifically: how to run the check engine, which
accounts it covers, and what to report.

## How a run works (the short version)

All code lives outside this skill (Paperclip rejects skills that contain
scripts) in the **code pack**: repo folder `fams-integrity-agent/`, installed
on the VM at `H=/paperclip/fams-integrity-agent` with its own Python
(`PY=$H/.venv/bin/python`) by `fams-integrity-agent/deploy/install.sh`.

1. Install/update the pack is a human step on the VM (see its README). Don't
   pip-install anything yourself.
2. `$PY $H/scripts/run_checks.py --out $H/runs/$(date +%F)` — computes every client's window,
   pulls the data read-only, runs all checks, and writes
   `out/<Client>/findings.json` plus evidence CSVs. **Read its stderr and the
   JSON summary it prints.** A check that failed is listed in
   `checks_run`/`data_gaps` — report it as "unverifiable", never as clean.
3. Build each client's PDF and workbook **from `findings.json` only** (see
   Reporting). Do not recompute any number, do not re-query the database to
   "improve" a figure, and do not add findings the engine did not produce. If
   you think something is missing, say so in the issue comment.
4. Email the PDFs: `$PY $H/scripts/send_reports.py --run-dir $H/runs/$(date +%F) --pdf ShipTech=<pdf> --pdf RAM-Couriers=<pdf> --pdf PMC-Phalaborwa=<pdf>` (see Emailing the reports). Required on every daily run.
5. Update the client portal in Notion (see Publishing to the client portal):
   `$PY $H/scripts/publish_notion.py --run-dir $H/runs/$(date +%F) --pdf ShipTech=<pdf> --pdf RAM-Couriers=<pdf> --pdf PMC-Phalaborwa=<pdf>`.
   A publishing failure never blocks or undoes the email; report it.
6. Attach PDFs + workbooks to the issue and comment: windows, Investigate /
   Monitor counts, email results, and the `publish_notion.py` summary
   (pages created / updated / failed, warnings). Then close the issue.

The engine is deterministic and unit-tested
(`$PY -m pytest -q $H/tests`, which also covers the read-only guard).
Thresholds live in `config/config.json` of the pack, not in code and not in
this file's prose — change them there, in git.

## Going deeper: FAMS Integrity

[FAMS Integrity](../FAMS_INTEGRITY/SKILL.md) is the full investigation knowledge
base this daily check is a fixed, automated subset of. Every check the engine
runs traces back to a file there or in `fams-daily-report` (the
`check_registry` block in `findings.json` lists them):

| Check | What it finds | Source |
|---|---|---|
| C01 | Duplicate transactions — 5 rules (UnqTrID+Volume+Equipment, UnqTrID+Equipment+Time, Store+Volume+Time, same TransactionID+same volume, same Equipment+Volume within 120 s), merged into one group per event, lowest ID kept as original, known dual-pipeline bug tagged | `algorithms/duplicate-detection.md` |
| C02 | TransactionID collision — same ID, different volumes | `algorithms/duplicate-detection.md` |
| C03 | Missing TransactionID (with backfill candidate from InformationRec) | `anomaly-library/data-quality.md` |
| C04 | Unreconciled UnqTrID ('N/A'/NULL) | `datasets/validation-rules.md` |
| C05 | InformationRec truncated ("Over Character Limit") / blank above 25% | `anomaly-library/data-quality.md` |
| C06 | Unexplained dispensing: a UsageDispensing row with no backup record (no IOT **and** no Android); split out if inside a backup-feed outage; owner-confirmed offload equipment excluded; pending offload equipment and MAC-prefixed IDs annotated | `algorithms/atg-reconciliation.md`, `investigation/networking.md` |
| C07 | Volume mismatch UsageDispensing vs backup (IOT, else Android) > 1% | `algorithms/atg-reconciliation.md` |
| C08 | Backup (IOT/Android) record that never reached UsageDispensing/Transfer/Receiving (searched across the whole fetched range) | `anomaly-library/transaction-integrity.md` |
| C09 | IOTData_FMS TypeID outside 1–4 | `datasets/field-definitions.md` |
| C10 | Recnumber: manual-entry candidates; 4627x batch series (known pattern on known/pending offload equipment, Investigate elsewhere); blank Recnumber | `anomaly-library/equipment-integrity.md` |
| C11 | ProductID / ProdID = 0 (or blank) in UsageDispensing, IOT, Android, Transfer, Receiving and IOTData_FMS TelementryData | `anomaly-library/data-quality.md` |
| C12 | Totaliser flow continuity per nozzle — next start must equal previous end within 2 L | `algorithms/totaliser-continuity.md` |
| C13 | Totaliser overflow sentinel (4294967.x) and capture failures on nozzles that normally report a totaliser | `datasets/calculations.md` |
| C14 | BTLinkLost: recorded vs meter volume, TrId missing from canonical, per-device concentration with idle-timeout signature | `anomaly-library/device-integrity.md` |
| C15 | Missing EquipmentID (0/NULL), with BTLinkLost ±5 min co-occurrence | `anomaly-library/data-quality.md` |
| C16 | NoFlow stop with no DispTransactionComplete for the same TrId | `anomaly-library/device-integrity.md` |
| C17 | Telemetry gaps > 60 min (Stock, ATG), units that stopped reporting, accounts with no data at all | `investigation/networking.md` |
| C18 | Store-level tank variance: tank decline (deliveries > 3500 L excluded) vs dispensed + transferred; possible unexplained fuel loss | `investigation/tank.md` |
| C19 | ATG telemetry noise (rolling stdev), reading above capacity | `investigation/atg.md` |
| C20 | Communication errors over 10/device, near-empty-tank downgrade | `anomaly-library/device-integrity.md` |
| C21 | Transfer/Receiving volume vs ATG fill/drop (anchored via Notification TrId, not fillTrId) | `algorithms/atg-reconciliation.md` |
| C22 | Raw payload errors (TempTableDataJson.errorid ≠ 0) | `investigation/devices.md` |
| C23 | Volume outliers per equipment (Q3 + 3×IQR on the unit's own history); Bridgeport 36941 known benign | `algorithms/outlier-detection.md` |
| C24 | Allocation / cost-centre references that don't resolve or have no description | `business-rules/allocation-validation.md`, `cost-centre-validation.md` |
| C25 | IOTData_FMS dispensing record (TypeID 1) not decoded: missing from UsageDispensingIOT **and** UsageDispensing → Investigate; in UsageDispensing but not UsageDispensingIOT → Monitor (records in the last `decode_grace_minutes` of the window skipped) | FAMS Database Core → Table hierarchy |

**Still out of scope for this automated daily job**: fraud indicators,
employee-level behavioural analysis, seasonal and predictive anomaly
detection, and SARS Schedule 6 reporting. If something in this run's data
looks like one of these, say so as a finding (Monitor or Investigate) and note
that it needs a human using FAMS Integrity directly — don't reach a fraud or
SARS-compliance conclusion inside this automated report.

## Scope: three clients, one shared database

All three clients live in one shared database; the engine loops over
`AccountID` grouped by client. The account lists are in the pack's `config/config.json`
— that file, not this prose, is what the engine uses.

**ShipTech (PTY) LTD** — 17 accounts:
321, 328, 345, 346, 350, 353, 354, 360, 361, 365, 373, 378, 383, 389, 394,
397, 404. (AccountID 377 "Retail (Zimbabwe)" was removed 2026-10-02 — site
discontinued. Don't add it back.)

**RAM Couriers** — 2 accounts: 390, 391

**PMC Phalaborwa** — 1 account: 285

Treat each client's accounts as one group in the report. An anomaly in one
ShipTech depot does not need escalating the same way as one affecting all 17.
If a new AccountID shows up in a client's data that isn't in config, say so in
the issue comment — don't add it yourself.

## ShipTech-specific known patterns (confirmed, not hypothetical)

These are encoded in `config.json` and the checks. Treat them as a starting
prior, but don't skip re-checking when the evidence doesn't match:

- **Tank-linked offload equipment** (MAC-format `TransactionID`, non-standard
  `Recnumber`): confirmed at Cato Ridge (EquipmentID 26409) and Piet Retief
  (30817) → `known_offload_equipment_ids`, excluded from C06. Recurring but
  pending owner sign-off at Nelspruit (31602), TWK Interlink (29307), Kokstad
  (29365), PMB (37571) → `pending_offload_equipment_ids`, still counted but
  annotated. Move an ID from pending to known only after the owner confirms.
- **Recnumber `4627x+` batch series** — large transfer/offload records on the
  equipment above. C10 reports these as Monitor (known pattern) and as
  Investigate only on unexpected equipment.
- **Confirmed duplicate-write bug (TWK Interlink, PMB)** — same event written
  by the batch-transfer import and by `importFams` seconds apart. C01 tags
  these "known dual-pipeline bug" so the report cites the known bug.
- **Telemetry-outage false positive** — C06 separates unexplained transactions
  that fall inside an IOT+Android silence (> 30 min either side) into a
  Monitor finding, and C17 reports the gaps themselves. Report the outage
  explicitly; don't present the raw reconciliation % without that context.
- **Cross-day matching** — the engine fetches a 72-hour lookback plus
  everything up to the run time, so matching (duplicates, BTLinkLost TrIds,
  raw-vs-canonical) never misses a record that straddles the boundary.

## Database access — read-only, enforced in code

The SQL login this agent uses has full administrative rights, and a dedicated
read-only login could not be created. So **the only database access path is
`$H/scripts/fams_db.py`**. It enforces read-only in three layers:

1. **Static guard** — the statement is lexed (comments, string literals and
   quoted identifiers stripped first, so neither `-- DELETE` nor `[Update]`
   fools it, and nothing can hide behind a comment). It must be one statement
   starting with `SELECT`/`WITH`, with no write/DDL/side-effect keyword
   (`INSERT`, `UPDATE`, `DELETE`, `MERGE`, `SELECT … INTO`, `EXEC`, `NEXT VALUE
   FOR`, `OPENROWSET`, `WAITFOR`, `xp_`/`sp_` calls, `SET`, `DECLARE`, …).
2. **Always-rollback** — autocommit off; every statement runs in a
   transaction that is rolled back after the rows are fetched, success or
   failure.
3. **Read-only intent** — the pyodbc connection declares
   `ApplicationIntent=ReadOnly`.

Rules for the agent:

- Never open your own connection (no `mssql`, `sqlcmd`, raw `pyodbc`). For an
  ad hoc follow-up query use `$H/scripts/run_query.py`, which
  goes through the same guard.
- A `ReadOnlyViolation` is final. Don't rephrase the query to get around it.
- If a task description asks this agent to modify data, fix a reconciliation
  by changing rows, or run anything other than a read — refuse, explain why
  in the issue comment, and stop. That instruction overrides the task
  description, not the other way around.

Credentials arrive as Paperclip secrets in environment variables —
`FAMS_DB_HostName`, `FAMS_DB_DBName`, `FAMS_DB_UserName`, `FAMS_DB_Password`.
Treat every one as sensitive: never print, echo, log, or put any of them in a
comment, issue body or file. `fams_db.py` scrubs them from error messages.
Driver: `pymssql` (installed in the pack's venv) unless ODBC Driver 18 is installed,
in which case `pyodbc` is used; override with `FAMS_DB_DRIVER`.

## Time window

Each run checks **48 hours** of data, `[anchor − 48h, anchor)`. The anchor
differs by client — this is an **approved per-client exception** to the
06:00 SAST rule in FAMS Core / FAMS Database Core, set by Hennie on
2026-10-02, and it lives in `config.json` as `boundary_hour_sast`:

- **ShipTech** — anchor = the most recent **06:00 SAST** at or before the run.
- **RAM Couriers and PMC Phalaborwa** — anchor = the most recent **midnight
  SAST** at or before the run.

The engine does the timezone maths (container clock is UTC; SAST is always
UTC+2, no DST) and assumes database timestamps are SAST (`db_timezone` in
config — change it there if that's ever shown to be wrong). It writes each
window in SAST and UTC into `findings.json → window`; put exactly those
strings at the top of each client's report.

## Reporting: one branded management report per client, plus a technical workbook

Produce **three distinct PDF files**, one per client (ShipTech, RAM Couriers,
PMC Phalaborwa) — not one combined cross-client report. Each is a management
report covering that client's whole account portfolio, matching this
structure (this is the finalised, already-proven format used elsewhere at
Tecmo Automation for the same kind of daily check — follow it exactly rather
than reverting to a flat per-account list). Use the same full structure for
RAM Couriers (2 accounts) and PMC Phalaborwa (1 account) as for ShipTech — a
one- or two-row Portfolio Summary table is still a table; don't shrink the
report's structure just because there's less to put in it.

Every number and finding comes from that client's `findings.json`:

| Report element | `findings.json` source |
|---|---|
| Window line | `window.start_sast`, `window.end_sast` (+ `_utc`) |
| Quick Stats | `kpis` |
| Portfolio Summary | `portfolio` |
| Investigate / Monitor / No action | `findings[]` filtered by `status` (already grouped and sorted) |
| Accounts with no findings | `accounts_without_findings` |
| Data Quality & Methodology | `data_sources`, `data_gaps`, `checks_run` |
| Totaliser flow table | evidence CSV of every `C12` Investigate finding |

**Header** — the real Tecmo Automation / FAMS banner, plus client name and
reporting window. The banner image ships alongside this skill at
`assets/fams_header_banner.jpg` (1246×232px) — embed it at the top of every
page (not just the first), scaled to the page's content width with its
aspect ratio preserved:

```js
const bannerPath = path.join(skillDir, 'assets', 'fams_header_banner.jpg');
const bannerWidth = doc.page.width - doc.page.margins.left - doc.page.margins.right;
const bannerHeight = bannerWidth * (232 / 1246); // preserve the real aspect ratio
doc.image(bannerPath, doc.page.margins.left, doc.page.margins.top, { width: bannerWidth });
// then move the cursor below the banner before drawing anything else, e.g.:
let y = doc.page.margins.top + bannerHeight + 20;
```

Below the banner: client name and account count, then the reporting window,
in the same style as before (bold client name, `#1F2A44` navy, an accent
rule underneath).

**Use the real image file, not a substitute.** Verify
`assets/fams_header_banner.jpg` actually exists and `doc.image()` loads it
without throwing before you generate anything — if it fails, that's a bug to
fix (wrong path, skill not materialized correctly), not a reason to draw your
own text-only banner that merely resembles it. A drawn rectangle with
"TECMO AUTOMATION" typed into it is not the same deliverable as the real
logo, even if it looks superficially similar.

**Text encoding**: `pdfkit`'s built-in `Helvetica` font only supports
WinAnsi/Latin-1 encoding — it silently renders unsupported characters as
garbage rather than erroring. Never use an arrow character (`→`, `➜`, `▶`,
etc.) or any other character outside that range anywhere in PDF text
(window ranges, notes, anywhere) — use the word "to" instead (e.g.
"2026-09-27 06:00 SAST to 2026-09-29 06:00 SAST"), which is what every
correct report so far has used. A plain hyphen `-` or true em-dash `—` is
fine; a Unicode arrow is not.

**01 Quick Stats** — six KPI cards, straight from `kpis`:
- **Anomalies detected** — `anomalies_detected` (grouped findings with status
  Investigate or Monitor; a device with 600 repeated errors is ONE finding).
- **Total fuel dispensed** — `total_fuel_dispensed_L`. This is already net of
  duplicate rows; if `duplicate_excess_L` > 0, say underneath "after removing
  X L of duplicate rows".
- **Reconciliation %** — `reconciliation_pct`. State
  `reconciliation_numerator_L` / `reconciliation_denominator_L` every time. If
  `of_which_during_raw_feed_outage_L` > 0, say how much of the unexplained
  volume falls inside a backup-feed outage (IOT and Android both silent).
- **Sites with possible fuel loss** — `sites_with_possible_fuel_loss`.
- **Sites with communication failures** — `sites_with_communication_failures`
  (devices over the 10-per-window tolerance).
- **Tanks at risk of running dry** — `tanks_at_risk_of_running_dry` (always 0)
  with the `run_dry_caveat` text.

No financial values or fuel prices appear anywhere in this report.

**02 Executive Summary** — one prose paragraph covering the window, the
overall reconciliation picture, and calling out (by name) anything that
needs attention this run, plus which sites had no findings.

**03 Portfolio Summary** — a table from `portfolio`: Account, Dispensed (L),
Recon %, Anomalies, Comm. Fail. `Recon_pct` is already `n/a` for an account
with zero dispensing volume.

**04 Items for Management (Investigate)** — a table for every finding with
status `Investigate`: Account, Category, Affected, Note. Omit the whole
section if there are none — don't render an empty table.

Directly under it, if any `C12` Investigate finding exists, a sub-table
**Totaliser flow breaks** with one row per break from the finding's evidence
CSV, columns exactly: **Account, Macaddress, ID, TransactionID, Volume (L),
Missing volume (L)** (`MissingVolume_L`; show "backwards" when blank). If
there are more than 40 rows, show the 40 largest missing volumes and say
"N more in the technical workbook".

**05 Monitoring Items** — findings with status `Monitor`, grouped by
`category` (e.g. "ATG telemetry noise" as a table of Account/Tank/Window;
"Communication errors explained by near-empty tanks" as Account/Device/
Errors/Note). Add a one-line caveat under each sub-table explaining why these
don't need action (e.g. "most coincide with normal daytime dispensing
activity... no action required unless a specific tank is also flagged under
possible fuel loss").

**06 No Action Required** — a short bullet list: `accounts_without_findings`,
any `No action required` findings (known offload equipment, known benign
outliers), the count of sites with a possible-fuel-loss finding (must match
Quick Stats), and a line confirming no financial values/individuals/due dates
are assigned per reporting policy.

**07 Data Quality & Methodology Note** — start with the data lineage from
`source_hierarchy`, printed as-is (layer, table, note): `UsageDispensing` is the
source of truth for every dispensing figure, `UsageDispensingIOT` and
`UsageDispensingAndroid` are backups, `TempTableDataJson` and `IOTData_FMS` are
raw. Never describe any other table as the source of truth, primary source or
main source. Then, from `data_sources`, `data_gaps` and `checks_run`: which sources this run had and how many rows, and for anything
missing or any check that failed, say so explicitly — the correct posture is
"unverifiable with current data", never silence or a false all-clear. Also
state the window boundary used for this client.

**08 Technical Appendix** — a short pointer to the companion Excel workbook
(see below) and what's in it.

### Status vocabulary — exactly these three, nothing else

- **Investigate** — real discrepancy, possible fuel loss, device over
  tolerance, tank variance over tolerance, unexplained transaction, duplicate
  affecting totals, possible manual entry, totaliser flow break, ProductID 0,
  run-dry risk, or missing data that blocks reconciliation.
- **Monitor** — minor/incomplete evidence, within tolerance but unusual, a
  repeated pattern that might matter later, or a data-confidence warning
  (e.g. erratic telemetry) that isn't itself a confirmed event.
- **No action required** — fully reconciled, within tolerance, a rapid-drop
  event fully explained, a delayed record that arrived within grace period,
  a device at or under the error tolerance, or purely informational.

The engine assigns these; don't change a finding's status in the report. If
you disagree with one, keep it and explain why in the issue comment.

Never state a due date, assigned individual, or responsible team against a
finding — only what happened, why it matters, possible cause(s), evidence,
and a recommended next step.

### Tolerances (all in `config.json → tolerances`)

- Volume/tank variance: 1% (`volume_tolerance_pct`); a store variance must
  also exceed the materiality floor (`material_loss_litres` 500 L or 5% of
  capacity, whichever is smaller) before it is a possible loss.
- Communication errors: up to 10 per device per window (`comm_error_tolerance`);
  median tank volume ≤ 10 L during the errors (`near_empty_tank_litres`) is a
  near-empty-tank explanation (Monitor), not a device fault.
- Totaliser continuity: a jump of more than 2 L between a transaction's end
  reading and the next transaction's start on the same nozzle
  (`totaliser_continuity_litres`).
- A missing Operator alone is never an anomaly.
- Zero-volume dispensing rows with no raw match are informational, not
  anomalies — not counted in the unexplained total.
- A `Recnumber` outside `recnumber_known_patterns` is a candidate for a
  possible manual entry, not automatic proof — this business has historically
  had no manual dispensing entries. If a legitimate new batch format appears,
  add its pattern to config (with the owner's confirmation).

### Language discipline

`UsageDispensing` is the source of truth for dispensing; IOT and Android are
backups (FAMS Database Core → Table hierarchy). Never call `UsageDispensingIOT`
or any other table the source of truth, primary or main source, and never call
IOT/Android records "raw": the raw tables are `TempTableDataJson` and
`IOTData_FMS`.

Always say "possible cause" unless proven. Never assert theft, fraud, or
confirmed loss from tank/telemetry data alone — only "possible unexplained
fuel loss," paired with an explicit statement that the finding is unconfirmed
and needs field verification (a physical dip-stick check, invoice
reconciliation, etc.).

### Grouping discipline

The engine already groups findings by account + category (or device / store /
tank). Every underlying record is in the finding's evidence CSV, which goes
into the workbook, not the PDF. Never split a grouped finding back into
per-row findings in the PDF.

Generate the PDF with the `pdfkit` npm package (pure JS, no native
dependencies) — install once per run if not already present:

```bash
npm install pdfkit --no-save
```

Name each file `FAMS-Integrity-<Client>-<YYYY-MM-DD>.pdf` (date = `window.report_date`), e.g.
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
zebra-striping. **The orange specifically must appear on every section
number** ("01", "02", "03", etc. — not the section title text itself, just
the leading number, e.g. `doc.fillColor('#E8720C').text('01', ...)` then
switch back to navy for the word "Quick Stats" that follows it) — a report
using navy/gray throughout with no orange anywhere is missing this rule, not
a valid interpretation of "reuse the palette."

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

Alongside each client's PDF, produce one Excel workbook with these sheets,
using the `exceljs` npm package (install once per run if not already
present: `npm install exceljs --no-save`). All content comes from the
engine's output files — copy, don't recompute:

- **Portfolio Summary** — `findings.json → portfolio` (same as the PDF table).
- **All Findings** — one row per entry in `findings[]`: finding_id, Account,
  Check, Status, Category, Affected, Litres, Count, Note, Evidence file.
- **Evidence** — every finding's evidence CSV, stacked, with a leading
  `finding_id` column (or one sheet per check if a single sheet would be
  unreadable). This is the full record behind every finding.
- **Totaliser Flow** — all `C12` evidence rows: Account, Macaddress, ID,
  UsageDispensingID, TransactionID, Volume, MissingVolume_L, BreakType,
  CreateDate, TotaliserEnd, NextID, NextTransactionID, NextTotaliserStart,
  Gap_L, Source, NozzleKey, Explanation.
- **Dispensing Detail** — `dispensing_detail.csv` (every window dispensing
  row, its Classification, and `FlaggedBy`).
- **Tank Reconciliation** — `tank_reconciliation.csv` and
  `store_reconciliation.csv` (two tables on one sheet, or two sheets).
- **Data Gaps & Audit** — `data_gaps.csv`, `findings.json → data_sources`,
  `checks_run`, the window strings, and the tolerances from `config.json`.

Name it `FAMS-Integrity-<Client>-Technical-<YYYY-MM-DD>.xlsx`, using
`window.report_date`. Don't email this workbook to the four recipients (see
below) — attach it to the issue as a work product instead, and reference it by
name in the PDF's Technical Appendix section, so it's available for deeper
investigation without adding four more email sends per client every day.

## Publishing to the client portal (Notion)

Every run also writes the results into the clients' Notion portal. This
replaces the old nightly job that created these pages (switched off when the
agent went live) — the agent is now the only writer.

| Client | Where the pages go |
|---|---|
| ShipTech | FAMS Client Portal > Shiptech (pty) ltd Portal > Sites > *one page per site* > **Data Integrity Reports** |
| RAM Couriers, PMC Phalaborwa | FAMS Client Portal > FAMS Clients > Sites > *site page* > **Data Integrity Reports** |

AccountID → site → database is fixed in the pack's `config/config.json`
(`notion.sites`, 20 sites). `publish_notion.py` does all of it from
`findings.json`; don't hand-edit pages or use the Notion MCP tools to write
these pages.

- **One page per site per operational day.** A 48-hour run covers two days,
  so it upserts two pages per site, named "DD Mon YYYY" with the `Date`
  property set. The next day's run rewrites the older of the two with fresher
  data. A page is found by its `Date`; the script updates it in place and
  never creates a second page for the same date.
- **Properties:** Status (`Clean` when the site-day has no Investigate or
  Monitor findings, otherwise `Issues Found`), Usage % (that day's
  reconciliation %), Transfer % / Receiving % (logged volume not contradicted
  by ATG telemetry), ATG % (tank decline vs dispensed + transferred), each
  blank when not applicable.
- **Body**, same layout as before: KPI table, last-7-days trend (read from the
  previous pages), Investigate table, **Totaliser flow breaks** (Macaddress,
  ID, TransactionID, Volume, Missing volume), Monitor table, tanks,
  reconciliation line, one "⚠️" section per Investigate finding with its
  evidence rows for that day, No action required, data-quality note, and the
  PDF link.
- **PDF:** the client's PDF is uploaded to Azure Blob
  (`reconciliation-reports/paperclip/<Client>/…`, secret
  `FAMS_BLOB_CONNECTION_STRING`) and linked with a read-only link valid for
  `pdf_upload.link_days` (365). If the secret is missing or the upload fails,
  pages are still published, without the link, and the run says so.
- **Client-facing.** These portals are read by the client: the page carries
  the same language discipline as the PDF (possible cause, unconfirmed until
  field-verified, no prices, no names, no due dates).
- **Safety:** the script writes only into the 20 configured databases, never
  deletes or moves a page, and on an update only replaces that page's own
  content. If two pages exist for one date it updates the oldest and warns —
  leave the extra page for a human to archive.
- Check before go-live with `--dry-run` (writes the page JSON to
  `<Client>/notion_preview/`, no network). `publish_log.json` in each client
  folder lists every page created / updated / failed with its URL.

## Emailing the reports

Send the PDFs with the installed script. Never write your own HTTP code for
this:

    $PY $H/scripts/send_reports.py --run-dir $H/runs/$(date +%F) \
        --pdf ShipTech=<pdf> --pdf RAM-Couriers=<pdf> --pdf PMC-Phalaborwa=<pdf>

- Recipients, endpoint and subject come from `config.json → email`: the four
  FAMS addresses, one POST per recipient (the endpoint takes a single address),
  so 12 sends per run. The endpoint needs no auth (network-trust only).
- Subject: `FAMS Integrity Report — <Client> — <YYYY-MM-DD>`. The body is a
  one-line summary built from that client's `findings.json`.
- PDFs only. The workbooks are attached to the issue, never emailed.
- The script retries a failed send once, records every send in
  `<run-dir>/email_log.json`, prints a JSON summary and exits 2 if anything
  still failed. Re-running it only sends what hasn't been sent yet, so it never
  emails anyone twice. Don't pass `--resend` unless a human asks.
- Report the summary in the issue comment (sent / failed, with recipient,
  client and HTTP status for any failure). Don't send by any other means.
- A test or an issue that says "no email" means: skip this step entirely.
  `--to <address>` limits a send to one recipient when a human asks for a test.

## Prohibited

- Any database access that doesn't go through `$H/scripts/fams_db.py`.
- Any `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`, or other write/DDL
  statement, or any attempt to get a statement past the read-only guard.
- Modifying data to make a reconciliation match.
- Changing a finding's numbers or status in the report or on Notion.
- Writing to Notion other than through `publish_notion.py`, deleting or
  moving any Notion page, or writing outside the configured databases.
- Logging or echoing any `FAMS_DB_*` value or a connection string anywhere a
  human or another system will read it back.
