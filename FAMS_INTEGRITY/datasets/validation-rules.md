# Validation Rules (data-level)

- `Volume > 0` required for meaningful dedup/reconciliation checks (many
  queries in this org filter this explicitly).
- `UnqTrID` should never remain `'N/A'`/NULL beyond the reconciliation
  window — treat persistent unreconciled rows as a data-quality finding.
- Cross-source volume tolerance: 0.1 (unit: whatever `Volume` is stored in
  — confirm per account) is the tolerance used historically in this org's
  reconciliation queries.

<!-- Add further validation rules as they're confirmed. -->
