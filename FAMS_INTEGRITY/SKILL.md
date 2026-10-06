---
name: fams-integrity
description: Investigate FAMS (Fuel Automation Management Systems) fuel dispensing data in Azure SQL for data-integrity issues — duplicate transactions, missing TransactionIDs, IOT/Android/Log reconciliation mismatches, employee/equipment/tank integrity, and account-level anomaly or fraud review. Use whenever the user names a FAMS AccountID or customer, asks to find duplicate dispensing records, wants to reconcile IOT vs Android vs Log volumes, needs to backfill UnqTrID/TransactionID from InformationRec JSON, or wants an integrity/anomaly/risk report on fuel transaction data. Requires Azure SQL connectivity (Claude Code / Cowork; not available in the claude.ai browser sandbox).
---

# FAMS Integrity Agent

This file is the entry point. It doesn't try to contain everything — it
routes you to the right file(s) below depending on what the user is asking
for. Read only what you need for the task at hand.

## Prerequisites

Known connection details (non-secret — safe to keep here):
- Server: `db.fams.co.za`
- Database: `FAMS2018`

- Code lives outside this skill (skills can't carry scripts) in the **code pack**:
  repo folder `fams-integrity-agent/`, installed on the Paperclip VM at
  `/paperclip/fams-integrity-agent/` (python: `$H/.venv/bin/python`). Below,
  `<pack>` means whichever of those two you have.
- `pip install -r <pack>/scripts/requirements.txt` (`pymssql` needs no OS driver;
  `pyodbc` + ODBC Driver 18 is used instead when installed)
- Credentials in environment variables only — never entered into chat:
  local `FAMS_SQL_USER` / `FAMS_SQL_PASSWORD` (optionally `FAMS_SQL_SERVER`,
  `FAMS_SQL_DATABASE`, or a full `FAMS_SQL_CONN_STR`); the Paperclip agent's
  `FAMS_DB_HostName` / `FAMS_DB_DBName` / `FAMS_DB_UserName` /
  `FAMS_DB_Password` are accepted too
- Verify with `python <pack>/scripts/db_connect.py --test` before querying

**Read-only, always.** The shared login has admin rights and a read-only login
could not be created, so `<pack>/scripts/fams_db.py` is the only path to the
database: a lexing guard that accepts a single `SELECT`/`WITH` statement (or
an allowlisted report proc), a transaction that is always rolled back, and
`ApplicationIntent=ReadOnly`. `run_query.py` cannot run `UPDATE`/`DELETE`.
When an investigation ends in a data fix, write the exact SQL (preview
`SELECT`, explicit ID list, the write) for the human to run in SSMS.

If no driver is installed, the test fails, or there's no network path
to `db.fams.co.za` (e.g. running in claude.ai chat) — **switch to Manual /
Paste Mode** below instead of retrying or asking for a password.

## Manual / Paste Mode (no DB connection available)

Use whenever `db_connect.py --test` fails or this environment has no
network access to `db.fams.co.za` (this is always the case in claude.ai
chat; may or may not be the case in Claude Code depending on the machine).

1. State plainly: **"No DB connection available — here's the SQL to run yourself."**
2. Route to the right query as normal (`algorithms/`, `business-rules/`,
   `<pack>/sql/`), fill in the placeholders
   (`{AccountID}`, `{StartDate}`, etc.) with the values the user gave, and
   hand back the finished, ready-to-paste SQL.
3. Ask the user to run it in SSMS / Azure Data Studio / their tool of
   choice and paste the results back into the chat.
4. Analyze pasted results exactly as if they came from `run_query.py` —
   every reference file (dedup rules, SARS eligibility logic,
   reconciliation tolerances) applies the same either way.
5. Never ask the user for their password in chat. Credentials only ever go
   into their own local environment (shell env vars / `.env`).

## Routing

| User is asking about... | Go to |
|---|---|
| What this org/methodology is, general principles | `knowledge/00-company.md`, `knowledge/01-core-principles.md` |
| How to run an integrity review end-to-end | `knowledge/02-integrity-methodology.md`, `knowledge/06-investigation-process.md` |
| What counts as an anomaly, anomaly taxonomy | `knowledge/03-anomaly-detection.md`, `anomaly-library/` |
| How to score/prioritize risk | `knowledge/04-risk-scoring.md`, `algorithms/integrity-score.md`, `algorithms/confidence-scoring.md` |
| Why something looks wrong (root cause) | `knowledge/05-root-cause-analysis.md` |
| Output format for findings | `knowledge/07-report-format.md`, `reports/` |
| Unfamiliar term | `knowledge/glossary.md` |
| Duplicate transactions, TransactionID collisions | `algorithms/duplicate-detection.md`, `prompts/review-transactions.md` |
| Totaliser jumps / skipped volume / "meter says more than FAMS" | `algorithms/totaliser-continuity.md`, `business-rules/nozzle-validation.md` |
| ProductID / ProdID = 0, missing EquipmentID, truncated InformationRec | `anomaly-library/data-quality.md` |
| Missing/bad TransactionID | `business-rules/` (validation rules), `algorithms/duplicate-detection.md` § backfill |
| IOT vs Android vs Log mismatch, tank/ATG checks | `algorithms/atg-reconciliation.md`, `investigation/atg.md`, `investigation/devices.md`, `prompts/review-atg.md` |
| Statistical outliers / trend checks | `algorithms/outlier-detection.md`, `algorithms/z-score.md`, `algorithms/moving-average.md`, `algorithms/seasonal-analysis.md`, `algorithms/variance-analysis.md`, `algorithms/consumption-analysis.md` |
| Employee-level review | `business-rules/employee-validation.md`, `investigation/employee.md`, `anomaly-library/employee-integrity.md`, `prompts/analyse-employees.md` |
| Equipment-level review | `business-rules/equipment-validation.md`, `investigation/equipment.md`, `anomaly-library/equipment-integrity.md`, `prompts/analyse-equipment.md` |
| Tank-level review | `investigation/tank.md`, `anomaly-library/tank-integrity.md`, `business-rules/tank-validation.md` |
| "Client says a delivery/receipt is missing from FAMS" | `investigation/tank.md` § "FAMS did not record this delivery" claims, `fams-reconciliation` skill for the full client-facing investigation |
| Reconciliation % looks unexpectedly bad for one site/window | `investigation/networking.md` § telemetry outage — check for a device/connectivity gap before treating it as fraud or data loss |
| Device/networking faults | `investigation/devices.md`, `investigation/networking.md`, `anomaly-library/device-integrity.md` |
| BT/Bluetooth link-loss errors ("BT errors") | `anomaly-library/device-integrity.md` § BTLinkLost, `datasets/calculations.md` § Actual volume, `business-rules/nozzle-validation.md` |
| Maintenance-related anomalies | `investigation/maintenance.md` |
| Suspected fraud | `investigation/fraud.md`, `anomaly-library/fraud-indicators.md` |
| Allocation / cost-centre rules | `business-rules/allocation-validation.md`, `business-rules/cost-centre-validation.md` |
| Operating hours / volume limits | `business-rules/operating-hours.md`, `business-rules/volume-limits.md` |
| Nozzle rules, override policy, SARS Schedule 6 | `business-rules/nozzle-validation.md`, `business-rules/override-policy.md`, `business-rules/sars-schedule6.md` |
| Generate the SARS/logbook report itself | `prompts/generate-sars-report.md`, `<pack>/sql/get_ReportinglogbookRev6SARS.sql`, `business-rules/sars-schedule6.md` |
| Table/column meaning | `datasets/field-definitions.md`, `datasets/expected-columns.md` |
| Validation rules, unit conversions, calculations | `datasets/validation-rules.md`, `datasets/unit-conversions.md`, `datasets/calculations.md` |
| Industry-specific pattern (mining, logistics, etc.) | `examples/<industry>/` |
| "Prep a review for me on X" style requests | `prompts/` (matching prompt file) |

## Core workflow (always applies regardless of investigation type)

1. **Resolve the account** — `SELECT * FROM Account WHERE [name] LIKE '%<term>%'`. Confirm AccountID with the user if ambiguous.
2. **Confirm the date window** with the user rather than assuming full history.
3. **Load only the routing-table files relevant to the request.**
4. **Run read-only queries first**, always, for every check.
5. **Never execute UPDATE/DELETE yourself** — the tooling refuses them. Hand the user the preview `SELECT`, the explicit ID list and the write statement to run in SSMS after they've reviewed it.
6. **Report using `knowledge/07-report-format.md` / `reports/`.**

## Scripts (code pack)

All in the code pack (`fams-integrity-agent/` in the repo; `/paperclip/fams-integrity-agent/` on the VM):

- `scripts/fams_db.py` — the only DB access layer: credentials from env, read-only guard, always-rollback
- `scripts/db_connect.py` — `--test` the connection
- `scripts/run_query.py` — run one read-only statement (`--sql`/`--sql-file`, `--param Name=VALUE` bound as parameters, `--csv`, `--proc` for the allowlisted SARS proc)
- `sql/get_ReportinglogbookRev6SARS.sql` — production SARS proc, verbatim, as ground truth
- `tests/` — guard + engine tests (`python -m pytest -q <pack>/tests`)
- `scripts/integrity_checks.py` / `run_checks.py` — the daily automated subset of this skill (checks C01–C25); reuse on exported data with `run_checks.py --source dir --data-dir <exports>`
