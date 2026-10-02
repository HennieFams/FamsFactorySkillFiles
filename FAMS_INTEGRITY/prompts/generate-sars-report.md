# Prompt: Generate SARS Report

Trigger phrasing: "run the SARS report for X", "SARS schedule 6 for
account X", "generate the logbook for X".

Steps:
1. Resolve account + confirm `@from`/`@to` window with the user.
2. Call the production proc (source kept verbatim in
   `fams-integrity-agent/sql/get_ReportinglogbookRev6SARS.sql`) through the
   read-only runner — it is the one allowlisted proc:
   ```bash
   python <pack>/scripts/run_query.py --proc --csv sars.csv \
     --sql "EXEC get_ReportinglogbookRev6SARS @account = {AccountID}, @from = {StartDate}, @to = {EndDate}" \
     --param AccountID=278 --param StartDate=2025-10-01 --param EndDate=2025-11-01
   ```
3. If the user asks *why* something is Eligible/Non-Eligible, or why an
   Asset Allocation Desc is blank/repeated, don't re-derive it from
   scratch — explain via `business-rules/sars-schedule6.md`, which
   documents the exact rule and its history.
4. This report is read-only by nature (a stored proc call) — no
   confirm-before-write step needed unless the user separately asks to
   modify underlying data based on what the report surfaces.
