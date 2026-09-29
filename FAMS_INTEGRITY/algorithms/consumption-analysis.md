# Consumption Analysis

Aggregate `UsageDispensing.Volume` by day/week/equipment/store to build the
baseline that `outlier-detection.md`, `moving-average.md`, and
`variance-analysis.md` compare against. Always filter `Volume > 0` and
apply the same date-window discipline as the rest of this skill.
