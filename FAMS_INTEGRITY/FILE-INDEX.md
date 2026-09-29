# FAMS-Integrity-AI — File Index

77 files total. Legend: ✅ = real, populated content · 📝 = stub/placeholder (needs team input) · 🔧 = script/code

## Root

| File | Purpose |
|---|---|
| ✅ `SKILL.md` | The actual skill definition Claude loads to trigger and operate this agent. Contains the routing table (which file to open for which request) and the core workflow/safety rules. **Start here.** |
| ✅ `CLAUDE.md` | Claude Code's project-memory file (auto-loaded every session in this repo). Points to `SKILL.md` and states standing rules (never write without confirmation, never hardcode credentials). |

## knowledge/ — general principles & process

| File | Purpose |
|---|---|
| ✅ `00-company.md` | Domain/company context — what FAMS is, what this skill audits. |
| ✅ `01-core-principles.md` | Five non-negotiable operating principles (verify against DB, read before write, scope writes narrowly, etc). |
| ✅ `02-integrity-methodology.md` | The 7-step end-to-end approach for auditing an account. |
| ✅ `03-anomaly-detection.md` | Index/taxonomy of anomaly types, pointing into `anomaly-library/`. |
| ✅ `04-risk-scoring.md` | How to classify a finding: confirmed defect vs. unexplained discrepancy vs. possible risk. |
| ✅ `05-root-cause-analysis.md` | How to trace a discrepancy to a cause before reporting it. |
| ✅ `06-investigation-process.md` | Step-by-step for deep-diving a single flagged item. |
| ✅ `07-report-format.md` | Pointer to `reports/` templates — which to use for which audience. |
| ✅ `glossary.md` | Domain term definitions (ATG, IOT, UnqTrID, Totalizer, etc). |

## anomaly-library/ — anomaly taxonomy (what to look for)

| File | Purpose |
|---|---|
| ✅ `data-quality.md` | Unreconciled IDs, malformed JSON, missing EquipmentID, duplicates. |
| ✅ `transaction-integrity.md` | Cross-source volume disagreement (IOT vs Android vs UsageDispensing). |
| 📝 `employee-integrity.md` | Employee-level anomaly signals — needs your team's input. |
| ✅ `equipment-integrity.md` | Equipment-level anomaly signals (bad EquipmentID, manual-entry rate). |
| 📝 `tank-integrity.md` | Tank-level anomaly signals — needs your team's input. |
| 📝 `atg-integrity.md` | ATG-specific fault patterns — needs your team's input. |
| ✅ `device-integrity.md` | IOT/device fault signals, payload errors, BTLinkLost (Bluetooth link-loss) volume cross-check. |
| ✅ `business-rules.md` | Index pointing into `business-rules/` for policy-violation anomalies. |
| 📝 `behavioural-analysis.md` | Pattern-shift-over-time checks — needs your team's input. |
| 📝 `fraud-indicators.md` | Fraud pattern indicators — needs your team's validated patterns. |
| 📝 `predictive-anomalies.md` | Forward-looking checks — future extension, not yet built. |

## business-rules/ — actual policy rules (what's allowed/not allowed)

| File | Purpose |
|---|---|
| ✅ `sars-schedule6.md` | **Real, load-bearing.** The SARS rebate Eligible/Non-Eligible logic, its bug history, and the PEA description-resolution rules — extracted from the actual stored procedure. |
| ✅ `allocation-validation.md` | Operation/Location (Allocation1/2) FK validation query and rebate-link explanation. |
| ✅ `cost-centre-validation.md` | Cost centre FK validation query. |
| 📝 `employee-validation.md` | Needs your team's actual employee rules. |
| 📝 `equipment-validation.md` | Needs your team's actual equipment rules. |
| 📝 `operating-hours.md` | Needs your team's allowed dispensing hours policy. |
| 📝 `volume-limits.md` | Needs your team's configured volume limits. |
| 📝 `tank-validation.md` | Needs your team's tank-level rules. |
| ✅ `nozzle-validation.md` | Confirmed nozzle identity key (StoreID+ProductID+TrailerMac+InformationMac, not EquipmentID) and per-nozzle totalizer-availability trait. |
| 📝 `override-policy.md` | Needs your team's manual-override policy. |

## algorithms/ — the actual detection queries/methods

| File | Purpose |
|---|---|
| ✅ `duplicate-detection.md` | The 3 dedup SQL checks + the UnqTrID/TransactionID backfill queries (from your original pasted SQL). |
| ✅ `atg-reconciliation.md` | IOT vs Android vs UsageDispensing three-way volume comparison queries, raw-payload trace, plus the Transfer/Receiving vs. ATG telemetry cross-check (device/time-anchored via IOTData_Notification, not fillTrId). |
| ✅ `outlier-detection.md` | Z-score-based per-equipment volume outlier query. |
| ✅ `z-score.md` | When to use z-score vs. IQR for skewed volume distributions. |
| 📝 `moving-average.md` | Trailing-average drift detection — concept only, needs refinement. |
| 📝 `seasonal-analysis.md` | Needs your team's known seasonal patterns per industry. |
| 📝 `variance-analysis.md` | Concept only. |
| 📝 `consumption-analysis.md` | Concept only — the aggregation baseline other algorithms build on. |
| 📝 `integrity-score.md` | Scoring formula not yet defined — needs your team's weighting. |
| 📝 `confidence-scoring.md` | Confidence-vs-severity distinction — concept only. |

## investigation/ — step-by-step workflows once something is flagged

| File | Purpose |
|---|---|
| 📝 `employee.md` | Needs your team's actual process. |
| ✅ `equipment.md` | Equipment investigation workflow (pull record → history → dedup/reconciliation → peer comparison). |
| ✅ `tank.md` | **Real.** Daily reading detection, the >3500L delivery heuristic, consumption formula — from the SARS stored proc. |
| ✅ `atg.md` | ATG mismatch investigation workflow, links to devices/maintenance. |
| ✅ `devices.md` | Device fault-tracing via TempTableDataJson errorid. |
| ✅ `networking.md` | Confirmed telemetry-outage diagnostic method (gap detection across raw device tables). |
| 📝 `maintenance.md` | Needs a maintenance log table if one exists. |
| 📝 `fraud.md` | Needs your team's escalation process. |

## examples/ — industry-specific patterns (6 empty folders)

| File | Purpose |
|---|---|
| 📝 `mining/README.md` | Placeholder — populate with mining-account patterns once you have cases. |
| 📝 `logistics/README.md` | Placeholder. |
| 📝 `agriculture/README.md` | Placeholder. |
| 📝 `municipalities/README.md` | Placeholder. |
| 📝 `fuel-suppliers/README.md` | Placeholder. |
| 📝 `manufacturing/README.md` | Placeholder. |

## reports/ — output templates by audience

| File | Purpose |
|---|---|
| ✅ `executive-summary.md` | Few-line, no-SQL template for execs. |
| ✅ `anomaly-report.md` | Itemized findings table, one section per anomaly type. |
| ✅ `integrity-report.md` | Full account review template (summary + all detail sections). |
| ✅ `management-report.md` | Operational/actionable template (owner-focused). |
| ✅ `technical-report.md` | Full detail incl. raw SQL and complete result sets. |

## prompts/ — trigger phrasing → workflow mapping

| File | Purpose |
|---|---|
| ✅ `review-transactions.md` | "Review transactions for X" → dedup + backfill checks. |
| ✅ `review-atg.md` | "Reconcile IOT vs android for X" → reconciliation queries. |
| 📝 `investigate-losses.md` | "Why are we seeing losses" — needs fraud-indicator content to be fully useful. |
| ✅ `analyse-equipment.md` | "Check equipment X" → equipment investigation workflow. |
| 📝 `analyse-employees.md` | Needs employee-validation content to be fully useful. |
| 📝 `review-business-rules.md` | Needs business-rules/ content to be fully useful. |
| ✅ `executive-review.md` | "Executive summary for X" → forces exec-only output format. |
| ✅ `generate-sars-report.md` | "Run the SARS report for X" → calls the stored procedure directly. |

## datasets/ — schema reference

| File | Purpose |
|---|---|
| ✅ `field-definitions.md` | **Real, the most-used reference file.** Every table/column discovered so far: UsageDispensing, IOT, Android, TempTableDataJson, plus everything from the SARS proc (Stock, TANK, PerEquipmentAssetAllocation, EquipmentRebate, AllocationRebate, Allocation, PerEquipmentStore, EquipmentCostCentre, EquipmentMasterGroup, EquipmentMeasurement, GetFueltransfers, GetFuelReceivingManual), plus the IOTData_FMS/ATG/Notification/Error RecordTypeId/TypeID scheme. |
| ✅ `IOTRecordType.csv` | Account owner's own RecordTypeId/TypeID reference export - source of truth for the table in `field-definitions.md`. |
| 📝 `expected-columns.md` | Placeholder for full column/type list per table (typo-catching). |
| ✅ `validation-rules.md` | Data-level rules (Volume > 0, UnqTrID shouldn't stay unreconciled, 0.1 tolerance). |
| 📝 `unit-conversions.md` | Needs confirmation of what unit Volume is stored in. |
| ✅ `calculations.md` | Core formulas: meter-derived volume, cross-source delta, z-score, actual-volume totalizer-diff (BTLinkLost cross-check). |

## scripts/ — executable code

| File | Purpose |
|---|---|
| 🔧 `db_connect.py` | Azure SQL connection helper. Reads credentials from env vars only — never hardcoded. |
| 🔧 `run_query.py` | CLI to run a SQL file or inline query against the DB, with `{PARAM}` substitution and CSV export. |
| 🔧 `stored-procedures/get_ReportinglogbookRev6SARS.sql` | The actual production SARS/logbook stored procedure, kept verbatim as ground truth for `business-rules/sars-schedule6.md`. |

---

## Quick stats
- **77 files** total
- **~40 real/populated**, **~30 placeholders** needing your team's domain input, **3 scripts**
- Placeholders are concentrated in `business-rules/` (org policy specifics: SARS aside, none of your operating-hours/volume-limit/override rules are documented anywhere yet) and `examples/` (no cases logged yet)
