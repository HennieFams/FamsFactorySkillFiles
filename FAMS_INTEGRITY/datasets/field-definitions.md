# Field Definitions

Data lineage (owner-confirmed 2026-10-06): sources of truth are `UsageDispensing`
(dispensing), `UsageTransfer` (transfers), `UsageReceiving` (receiving/offloading)
and `Stock` (tank levels). `UsageDispensingAndroid` and `UsageDispensingIOT` are
dispensing backups; `IOTData_ATG` / `_Notification` / `_Error` are raw IOT input;
`TempTableDataJson` is the raw table behind `UsageDispensing` (Android accounts
only); `IOTData_FMS` is the raw IOT table, decoded into `UsageDispensingIOT` and
into `UsageDispensing` when the transaction isn't already there. Full table in
FAMS Database Core → Table hierarchy.

## UsageDispensing (source of truth for dispensing)
- `ID` — row PK
- `AccountID`, `StoreID`, `EquipmentID` — scoping keys
- `Volume`, `OrigVolume` — reported volume / original-before-correction
- `Createdate` — transaction timestamp
- `TransactionID` — legacy transaction identifier field
- `UnqTrID` — reconciled unique transaction ID; `'N/A'` or NULL = unreconciled
- `InformationRec` — JSON blob. **Transaction ID key name is inconsistent
  across accounts**: seen as `$.transactionID`, `$.transactionId`, and
  `$.TransactionID`. Always detect the correct key per account before
  backfilling (query in `algorithms/duplicate-detection.md`).
- `Recnumber` — provenance: e.g. `'manualAdd'`, `'importFams'`
- `spare1` — scratch column, sometimes used to preserve a value before an
  UPDATE overwrites it (worth reusing as a defensive pattern)

## UsageDispensingIOT (backup, from the IOT device)
IOT data: decoded from `IOTData_FMS`. Verifies `UsageDispensing`, never
replaces it in reporting. Joins to `UsageDispensing` and
`UsageDispensingAndroid` on `(AccountID, TransactionID)`.

## UsageDispensingAndroid (backup, from the Android control unit)
From the Android control unit that links the Android device with the fuel pump. Includes `Totalizer`, `TotalizerEnd` — meter-derived
volume is `ABS(TotalizerEnd - Totalizer)`.

## TempTableDataJson (raw, behind UsageDispensing)
Raw inbound JSON payloads for `UsageDispensing`, **only for accounts that have
Android devices** — the main raw source for those (ShipTech except 365 TWK and
397 PMB Storage, plus RAM Couriers; list in `config.json → android_accounts`).
IOT-only accounts have nothing here. Keyed by `Macaddress` (→ `Store.Macaddress`),
with `errorid` flag. JSON paths in use: `$.transactionID`, `$.oldLitres`,
`$.DispensedVolume`, `$.Volume`.

## Account / Store / Equipment
- `Account.name` — searchable via `LIKE '%term%'`
- `Store.AccountID` — FK to Account
- `Equipment.AccountID`, `Equipment.[tag]` — FK + physical/RFID tag

---

## Additional tables discovered via get_ReportinglogbookRev6SARS

### Stock
ATG tank readings. `AccountID`, `TankID`, `CreateDate`, `Volume`. One row
per reading event; opening/closing per tank per day derived via MIN/MAX
CreateDate grouped by `CONVERT(varchar(50), CreateDate, 111)` (date-only).

### TANK
`ID`, `TankName`, `Capacity`, `AccountID` (via Store). Referenced as `TANK`
in the FROM clause but `Tank` elsewhere — case-insensitive in SQL Server,
same table.

### GetFueltransfers
A view/function (not a base table — called like a table but likely backed
by a view or inline function) returning fuel transfer events: `ID`,
`AccountID`, `Date`/`Year`/`Month`/`DateOnly`/`Time`, `Store`, `Product`,
`Registration`, `Volume`, `Totalizer`, `TotalizerEnd`.

### GetFuelReceivingManual
Same pattern as `GetFueltransfers`, for manually-captured stock receipts:
`ID`, `AccountID`, `Date`/`Year`/`Month`/`DateOnly`/`Time`, `TankID`,
`TankName`, `InvoiceNr`, `DeliveryNote`, `FuelSupplier`, `Description`,
`Volume`, `Store`, `Product`.

### PerEquipmentAssetAllocation (PEA)
`ID`, `EquipmentAssetID`, `Allocation1ID`, `Allocation2ID`, `Description`.
Maps an equipment asset to an Operation (Allocation1) / Location
(Allocation2) pair with a description. Can have multiple rows per
`(EquipmentAssetID, Allocation1ID, Allocation2ID)` — dedup by `ID ASC` when
querying. May have Allocation1-only rows with no matching Allocation2 row
for the same asset (see `business-rules/sars-schedule6.md` for the
fallback-match logic this requires).

### EquipmentAsset
`ID`, `AssetID`, `EquipmentRebateID`, `Name`, `Description`. Joined from
`Equipment.EquipmentAssetID`.

### EquipmentRebate
`ID`, `Name`. Joined from `Equipment.EquipmentRebateID`. Presence of a
row (`ID > 0`) is one of the three ways a transaction can qualify
Eligible for SARS purposes (see `business-rules/sars-schedule6.md`).

### AllocationRebate
`ID`, `Name`. Joined from `Allocation.AllocationRebateID` — i.e. an
Allocation (Operation or Location) can itself carry a rebate link,
independent of the Equipment's own rebate.

### Allocation
`ID`, `Name`, `Description`, `AllocationRebateID`. Generic allocation
table used twice per transaction: once via `UsageDispensing.AllocationID`
(Operation, aliased `allc1`) and once via `AllocationID2` (Location,
aliased `allc2`).

### PerEquipmentStore
`EquipmentID`, `StoreID`, `Maxlitres1`. Per-equipment-per-store maximum
litres capacity, used as the equipment "tank" ceiling for
Eqp_OpeningBalance/Eqp_ClosingBalance calculations.

### EquipmentCostCentre
`ID`, `Name`, `Description`. Joined from
`UsageDispensing.EquipmentCostCentreID`.

### PerEquipmentMasterGroup / EquipmentMasterGroup
`PerEquipmentMasterGroup.EquipmentID` → `EquipmentMasterGroupID` →
`EquipmentMasterGroup.ID/Name`. Groups equipment into a master
classification independent of cost centre or allocation.

### EquipmentMeasurement
`ID`, `Name`. Lookup for `Equipment.EquipmentMeasurementID`: `1` = volume
only (no reading), `2` = Hour-based (uses `UsageDispensing.Hour`), `3` =
KM-based (uses `UsageDispensing.KM`). Drives which reading/consumption
formula applies (see `datasets/calculations.md`).

## Additional UsageDispensing columns discovered

- `Hour`, `KM` — meter readings, used per `EquipmentMeasurementID` (see
  `EquipmentMeasurement` above)
- `AllocationID`, `AllocationID2` — Operation / Location links
- `AuthorizationID`, `OperatorID`, `DriverID` — all FK to `Operator`
- `EquipmentCostCentreID` — FK to `EquipmentCostCentre`
- `JobNumber`, `FuelPrice`, `Description` (free text)
- `ProductID` — FK to `Product`

---

## IOTData_* raw telemetry tables (FMS, ATG, Notification, Error) and the
## RecordTypeId / TypeID scheme

These four tables are the raw IOT device stream. `IOTData_FMS` dispensing
records are decoded into `UsageDispensingIOT` (backup) and into
`UsageDispensing` when the transaction isn't already there (and the newer transfer/receiving cross-check work in
`fams-daily-report`). Every row carries **two distinct codes** — conflating
them was a real bug caught 2026-08-21 (see below), so keep them separate:

- **`RecordTypeId`** — which envelope/table this row belongs to (constant
  per table). `1`=FMS, `2`=ATG, `99`=Notification, `123`=FMC.
- **`TypeID`** — the specific sub-event within that envelope (varies row to
  row). Full authoritative mapping in `datasets/IOTRecordType.csv` (source:
  account owner), reproduced here:

| RecordTypeId | Table | TypeID | Meaning |
|---|---|---|---|
| 1 | FMS | 1 | Dispensing |
| 1 | FMS | 2 | Transfer |
| 1 | FMS | 3 | Offloading |
| 1 | FMS | 4 | Complete (transaction-complete marker, not itself a movement) |
| 2 | ATG | 1 | Level (routine tank reading) |
| 2 | ATG | 2 | Received (fill complete) |
| 2 | ATG | 3 | RapidDrop (drop complete) |
| 2 | ATG | 4 | ReceivingStart (fill start) |
| 2 | ATG | 5 | RapidDropStart (drop start) |
| 2 | ATG | 99 | ATGError (sensor-fault flag) |
| 99 | Notification | 1 | Startup |
| 99 | Notification | 2 | NotifyTag |
| 99 | Notification | 3 | NoFlow |
| 99 | Notification | 4-8, 126-131 | Entry/selection fields (account, cash, job order, employee account, nozzle, driver, attendant, auth, misc, km/hrs, allocation) |
| 99 | Notification | 9 | DispenseDuringFill |
| 99 | Notification | 10 | Recovery alert |
| 99 | Notification | 12 | Device Info |
| 99 | Notification | 105 | DispenseMaxLitres |
| 99 | Notification | 114 / 116 | Verify1Fail / Verify2Fail |
| 99 | Notification | 117 | WrongTagType |
| 99 | Notification | 118 | GetInfoFail |
| 99 | Notification | 123 | PauseComplete |
| 99 | Notification | 124 | DispTransactionComplete — event-end marker |
| 99 | Notification | 125 | DispStartNow — event-start marker |
| 99 | Notification | 132 | BTLinkLost |
| 99 | Notification | 133 | ProtTokheimStatus |
| 99 | Notification | 134 | ProdTotals |
| 99 | Notification | 205 | ATGOverfill |
| 99 | Notification | 402 | StartWithTag |
| 123 | FMC | 1 | Power |
| 123 | FMC | 2 | Override |

**Open question, not yet mapped to a known base table**: `RecordTypeId=123`
(FMC — Power/Override) doesn't correspond to any table currently
documented in this skill or in `fams-daily-report`'s schema. If a raw
`IOTData_FMC` (or similarly-named) table exists, confirm its structure with
the account owner rather than guessing.

**Row-level columns, per real exports**: `IOTData_FMS`/`IOTData_ATG` carry
`RecordTypeID` and `TypeID` as separate decoded columns (not just inside
the JSON blob), alongside `DeviceId`/`DeviceAlias` (also decoded, matching
the blob's `deviceId`/`deviceAlias` exactly) and a `TelementryData` JSON
blob holding one or more per-tank/per-event entries — a single message can
mix entry types (e.g. a routine multi-tank snapshot alongside one sensor
fault), so match on the presence of event-specific keys (`strtVol`/`endVol`
for a fill/drop event) rather than trusting the outer TypeID alone when an
entry-level distinction matters.

**Corrected 2026-08-21**: FMS TypeID 2/3 had been documented and coded
(in `fams-daily-report`) as Offloading/Receiving respectively — backwards.
The correct mapping is 2=Transfer, 3=Offloading (confirmed by the account
owner's own `IOTRecordType.csv`), and TypeID 4 ("Complete") wasn't
recognized at all, so it was being silently flagged as an unexpected/
unknown TypeID on every account whose export had one. Note this lines up
with `business-rules/sars-schedule6.md`'s own (differently-scoped, stored-
proc-local) `RecordTypeID` 1/2/3 = Dispensing/Transfer/StockReceivedManual
ordering — that's a separate, proc-internal synthetic tag, not the same
column as this table's `RecordTypeId`/`TypeID`, but the two happen to agree
on ordering, which is a useful cross-check, not a coincidence to rely on
blindly.
