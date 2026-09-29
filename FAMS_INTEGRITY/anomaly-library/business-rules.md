# Business-Rule Anomalies (index)

Pointer file — the actual rules live under `business-rules/`:
employee-validation, equipment-validation, allocation-validation,
cost-centre-validation, operating-hours, volume-limits, tank-validation,
nozzle-validation, override-policy, sars-schedule6.

A "business-rule anomaly" here means a transaction that is internally
consistent (no cross-source mismatch) but still violates a configured
policy — e.g. dispensed outside allowed hours, or over a configured volume
limit.
