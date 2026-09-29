# Tank Investigation

Real logic, extracted from `get_ReportinglogbookRev6SARS.sql` STEP 3 (ATG
tank stock reconciliation) — reusable for tank checks outside the SARS
report context too.

## Daily opening/closing readings per tank

Opening = earliest `Stock` reading that day per tank; closing = latest.
Both derived via MIN/MAX `CreateDate` grouped by tank + date-only:

```sql
SELECT TankID, MIN(CreateDate) AS OpeningTime, CONVERT(varchar(50), CreateDate,111) AS [Date]
FROM Stock
WHERE AccountID = {AccountID} AND CreateDate BETWEEN '{StartDate} 00:00:00' AND '{EndDate} 23:59:59'
GROUP BY TankID, CONVERT(varchar(50), CreateDate,111);
-- (closing = same shape with MAX instead of MIN)
```

## Delivery detection heuristic

A **volume jump greater than 3500 litres** between consecutive readings on
the same tank is treated as a delivery event, not consumption or a data
glitch. This threshold is hardcoded in the stored procedure — if your
tanks are meaningfully smaller than this, the threshold will under-detect;
flag with the user if a customer's tank capacity is well under ~3500L.

```sql
-- Simplified shape of the logic (see stored proc for the full LAG-based version)
CASE
    WHEN ABS(CurrentReading.Volume - PreviousReading.Volume) > 3500
    THEN 'Likely delivery'
    ELSE 'Normal fluctuation'
END
```

## Consumption calculation

Once delivery is separated out, consumption for the day is derived as:

```
opening_volume + delivery_volume - closing_volume
```

(clamped to 0 if the arithmetic goes negative — see STEP 3f's `IIF` guard
in the stored proc). This is the tank-level analogue to
`algorithms/atg-reconciliation.md`'s cross-source dispensing checks —
tank-level consumption should roughly track the sum of dispensing volume
for equipment fed by that tank over the same window. A persistent gap
between the two is a strong integrity signal (unaccounted loss, unlogged
manual dispensing, or a tank/dispensing mapping error) — see
`anomaly-library/tank-integrity.md`.

## Ullage

`Capacity - ClosingVolume` (0 if closing volume exceeds capacity, which
itself would be worth flagging as a data or sensor issue).

## "FAMS did not record this delivery" claims — check before agreeing

**Confirmed root cause at least once (Richards Bay, Delivery Note
135367, Sept 12):** a client-reported "missing" delivery was actually
captured correctly by FAMS, as `UsageReceiving` row(s) with
`RecordTypeID=3` ("Offloading") — it just had `DeliveryNote`/`InvoiceNr`
left blank, so a delivery-note-based search couldn't find it. Before
agreeing a delivery is genuinely missing:
1. Search `UsageReceiving` by StoreID + EquipmentID (not by
   `DeliveryNote`, which may be blank) across the full available window.
2. Check whether the volume splits across two or more consecutive,
   totaliser-continuous records rather than one record — confirmed
   pattern, not a duplicate.
3. Cross-check the tank-level delivery-detection heuristic above (a
   >3500L jump) for independent corroboration, but note a same-window
   telemetry gap (see `investigation/networking.md`) can prevent the
   tank-level rise from fully confirming the quantity even when the
   FAMS-side flow record is solid.
4. Only conclude "not recorded" once step 1 comes back empty across the
   full window — not just the `DeliveryNote` field.

For the full client-facing investigation methodology and report format
for exactly this scenario (document ↔ flow ↔ control ↔ tank ↔ digital
reconstruction, 19-section report), use the separate `fams-reconciliation`
skill rather than reinventing the structure here.
