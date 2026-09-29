# Prompt: Review Transactions

Trigger phrasing: "review transactions for X", "check for duplicate
dispensing on account X".

Steps: resolve account → confirm window → run all 3 checks in
`algorithms/duplicate-detection.md` → run TransactionID backfill check →
report per `reports/anomaly-report.md`.
