# Data Quality Anomalies

- **Unreconciled UnqTrID** — `UnqTrID = 'N/A'` or `NULL` on `UsageDispensing`.
  Backfill logic: `algorithms/duplicate-detection.md` § related note, and
  the JSON key inconsistency warning in `datasets/field-definitions.md`.
- **Malformed/empty InformationRec JSON** — `JSON_VALUE` returns NULL for
  all known key variants.
- **Missing EquipmentID** — `EquipmentID = 0` or NULL on a dispensing row.
- **Exact duplicate rows** — see `algorithms/duplicate-detection.md`.

Detection queries live in `algorithms/duplicate-detection.md` rather than
here — this file is the "what/why", that one is the "how".
