# Investigation Process

Step-by-step for going deep on a single flagged item (not a full account
sweep — see `knowledge/02-integrity-methodology.md` for that):

1. Pull every table's version of the transaction (`UsageDispensing`,
   `UsageDispensingIOT`, `UsageDispensingAndroid`) by TransactionID.
2. Pull the raw JSON payload if available.
3. Check equipment/tank/device health at that timestamp.
4. Check for related transactions on the same equipment same day
   (pattern, not isolated incident?).
5. Classify per `knowledge/04-risk-scoring.md`.
6. Write up per `knowledge/07-report-format.md`.
