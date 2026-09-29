# Risk Scoring

Use `algorithms/integrity-score.md` and `algorithms/confidence-scoring.md`
for the actual scoring mechanics. At the framing level, classify every
finding as one of:

- **Confirmed data defect** — provable from the data alone (e.g. exact
  duplicate row). Safe to recommend a fix once previewed.
- **Unexplained discrepancy** — cross-source mismatch with no clear cause.
  Needs field/human investigation, not an automated fix.
- **Possible integrity risk** — pattern inconsistent with peers (e.g.
  abnormal manual-entry rate). Flag for ops/customer, don't assert fraud
  without further evidence.
