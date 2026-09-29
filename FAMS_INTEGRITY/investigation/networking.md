# Networking Investigation

## Detecting a telemetry outage (device/connectivity gap)

**Confirmed pattern, twice (Estcourt Sept 12, ~32hr gap; Richards Bay
Store 2225 Sept 12, ~2h21m gap):** a site's raw device tables
(`UsageDispensingAndroid`, `UsageDispensingIOT`, `Stock`) can simply stop
reporting for hours while `UsageDispensing` keeps logging transactions
normally via a different path. This produces a large, alarming-looking
"unexplained dispensing" or low-reconciliation-% result that is actually
a device/connectivity outage, not lost fuel, fraud, or data corruption.

**Diagnostic method:**
1. Pull the raw device table's own row timestamps for the account/store
   in question across the *full* available window (not just inside the
   reporting cutoff).
2. Look for a gap between consecutive `Createdate`/`CreateDate` values
   that's many multiples of the normal polling cadence (typically
   ~30s-1min for these devices) — that's the outage window.
3. Cross-check `Stock`/ATG readings for the same store over the same
   window — if those also show a matching gap, that confirms a
   site-wide telemetry outage (not just one app/table failing to sync).
4. Report the outage explicitly (start/end time, duration, which tables
   affected) rather than just reporting the resulting reconciliation %
   or unexplained-litres number on its own — the raw percentage without
   this context reads as far more alarming than the situation actually
   is, and conversely shouldn't be waved away without checking it's a
   real device gap and not something else.

This is a general diagnostic technique, not limited to BTLinkLost
investigations — apply it whenever a reconciliation check produces a
surprisingly bad number for one site/window relative to its own history.
