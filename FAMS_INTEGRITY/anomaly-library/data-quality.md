# Data Quality Anomalies

- **Unreconciled UnqTrID** — `UnqTrID = 'N/A'` or `NULL` on `UsageDispensing`.
  Backfill logic: `algorithms/duplicate-detection.md` § related note, and
  the JSON key inconsistency warning in `datasets/field-definitions.md`.
- **Missing TransactionID** — no usable `TransactionID` (NULL/''/'N/A'/'0')
  on a non-zero dispensing row: the row can't be reconciled to IOT/Android
  at all. `InformationRec` often still holds it (backfill candidate).
- **TransactionID collision** — one `TransactionID` on rows with different
  volumes (Richards Bay canonical-override case). See
  `algorithms/duplicate-detection.md` rule 4.
- **Malformed/empty/truncated InformationRec** — `JSON_VALUE` returns NULL for
  all known key variants, or the payload reads "Over Character Limit".
  Seen at high rates on some accounts (321: 85.7%, 346: 76.9%, Sept 2026);
  the daily job flags an account above 25%.
- **Missing EquipmentID** — `EquipmentID = 0` or NULL on a dispensing row.
  Recurring per specific StoreIDs (321/2403, 383/2407, 350/2235+2241,
  345/2360+2361); check for a BTLinkLost within ±5 min.
- **ProductID / ProdID = 0** — product not identified on a `Usage*` row or
  inside `IOTData_FMS.TelementryData` (`prodId`). Breaks per-product
  reporting, the nozzle key (`business-rules/nozzle-validation.md`) and the
  totaliser chain. Usually a device/nozzle product-mapping gap. Daily check
  C11, status Investigate.
- **Exact duplicate rows** — see `algorithms/duplicate-detection.md`.

Detection queries live in `algorithms/` rather than here — this file is the
"what/why"; the daily job implements all of the above in
`fams-integrity-agent/scripts/integrity_checks.py`.
