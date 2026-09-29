# Integrity Methodology

The end-to-end approach for auditing an account's data integrity:

1. Resolve account + scope (stores, equipment, date window).
2. Structural checks — `anomaly-library/data-quality.md`,
   `algorithms/duplicate-detection.md`.
3. Cross-source reconciliation — `algorithms/atg-reconciliation.md`,
   `investigation/atg.md`, `investigation/devices.md`.
4. Statistical checks — `algorithms/outlier-detection.md`,
   `algorithms/z-score.md`, `algorithms/variance-analysis.md`.
5. Business-rule checks — everything in `business-rules/`.
6. Score and prioritize findings — `knowledge/04-risk-scoring.md`.
7. Report — `knowledge/07-report-format.md`.

See `knowledge/06-investigation-process.md` for how to go deeper on any
single flagged item.
