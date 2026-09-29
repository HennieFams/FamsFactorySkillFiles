# Core Principles

1. **Never assume — verify against the database.** Every claim about
   duplicates, mismatches, or missing data must be backed by an actual query
   result, not inferred from a partial view.
2. **Read before write.** Every UPDATE/DELETE is preceded by a SELECT
   preview shown to the user, with an explicit confirmation step.
3. **Scope every write narrowly.** AccountID + date range at minimum;
   prefer an explicit ID list over a broad condition.
4. **Distinguish confirmed defects from unexplained discrepancies.** Not
   every mismatch is fraud — see `knowledge/05-root-cause-analysis.md`.
5. **Preserve provenance.** Don't discard `Recnumber`/original values
   without recording what was overwritten (see `spare1` pattern in
   `datasets/field-definitions.md`).
