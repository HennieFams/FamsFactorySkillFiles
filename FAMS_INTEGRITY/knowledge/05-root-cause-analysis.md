# Root Cause Analysis

When a discrepancy is found, don't stop at "these two numbers disagree" —
trace toward a cause before reporting:

1. Check device/network health around the time of the anomaly
   (`investigation/devices.md`, `investigation/networking.md`).
2. Check for a maintenance event on the equipment/tank in that window
   (`investigation/maintenance.md`).
3. Trace back to the raw inbound payload (`TempTableDataJson`) to see if
   the discrepancy originates upstream of FAMS's own processing — see
   `datasets/field-definitions.md` for the relevant JSON paths.
4. Only after ruling out device/process causes, consider behavioural or
   fraud explanations (`investigation/fraud.md`).
