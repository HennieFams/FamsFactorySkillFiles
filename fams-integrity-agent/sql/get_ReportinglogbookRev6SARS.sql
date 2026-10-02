/****** Object:  StoredProcedure [dbo].[get_ReportinglogbookRev6SARS]    Script Date: 2026/07/07 14:49:15 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:      FAMS
-- Create date: 2026-02-25
-- Description: SARS format report
-- =============================================
-- Rev 1 : Report created - Dispensing only
-- Rev 2 : This report combines the dispensing with the manual stock received entries
-- Rev 3 : Combine the transfer with the existing report
-- Rev 4 : ATG tank balancing added
-- Rev 5 : Eqp_OpeningBalance, Eqp_Ltthatcanbeused, Eqp_ClosingBalance calculated
--         using Equipment.MaxLitres and LAG/LEAD window functions on dispensing records.
-- Rev 6 : Four client-reported fixes applied to Rev5 base:
--         FIX 1 - TankOpeningVolume / TankClosingVolume explicitly passed through.
--         FIX 2 - Eqp_Usage column added (LEAD of next fill volume).
--         FIX 3 - Eligible_NonEligible column added (ERID / AR1ID / AR2ID check).
--         FIX 4 - Operations / Location sourced directly from allc1/allc2.
-- Rev 7 : Three additional client-reported fixes applied to Rev6 base:
--         FIX 5 - Eligible_NonEligible logic corrected:
--                 Rev6 compared rebate ID = 1 (matched only record with PK=1).
--                 Rev7 first checks whether PerEquipmentAssetAllocationDesc
--                 contains 'Not qualified' → forces 'Non-Eligible' regardless
--                 of any rebate ID. Only then checks ERID/AR1ID/AR2ID > 0
--                 for 'Eligible'. This correctly marks WingerdBestuur vehicles
--                 (and any other operation whose PEA desc says "Not qualified")
--                 as Non-Eligible even when a rebate record exists.
--         FIX 6 - Asset Allocation Desc blank for some Operation/Location
--                 combinations (e.g. CDW947NC under PekanVervoer, Tiller,
--                 DruiweVervoer, Dis):
--                 PEA join now uses a ranked subquery that de-duplicates on
--                 (EquipmentAssetID, Allocation1ID, Allocation2ID) and also
--                 falls back to an Allocation1ID-only match when no exact
--                 Allocation1+Allocation2 row exists. This ensures the desc
--                 pulls through whenever at least the Operation (Allocation1)
--                 has a PEA record, even if the specific Location (Allocation2)
--                 is not yet mapped.
--         FIX 7 - AA. / SS. Asset Allocation Desc appearing to duplicate in
--                 the Excel Per Equipment sheet:
--                 Confirmed via data analysis that no duplicate Fill IDs exist
--                 in the result set. The visual repetition is caused by the
--                 same description applying to multiple fills of the same
--                 vehicle across the period. No stored procedure change needed;
--                 the Excel template should suppress repeated desc values in
--                 the INDIVIDUAL sheet. This comment documents the finding.
-- =============================================

ALTER PROCEDURE [dbo].[get_ReportinglogbookRev6SARS]
    -- Test: get_ReportinglogbookRev7SARS 278, '2025-10-01', '2025-11-01'
    @account int,
    @from    datetime,
    @to      datetime

AS
BEGIN

    -- =========================================================================
    -- CLEANUP: drop all temp tables if they exist from a previous run
    -- =========================================================================
    IF OBJECT_ID('tempdb.dbo.#TempKPISARS_FTP',         'U') IS NOT NULL DROP TABLE #TempKPISARS_FTP;
    IF OBJECT_ID('tempdb.dbo.#TempData_FTP',             'U') IS NOT NULL DROP TABLE #TempData_FTP;

    DROP TABLE IF EXISTS #TempOpening_FTP;
    DROP TABLE IF EXISTS #TempStockDataRaw_FTP;
    DROP TABLE IF EXISTS #TempMinMaxReadingRaw_FTP;
    DROP TABLE IF EXISTS #TempMinMaxReading_FTP;
    DROP TABLE IF EXISTS #Delivery_FTP;
    DROP TABLE IF EXISTS #TempData_Final_FTP;
    DROP TABLE IF EXISTS #FAMSSARS_FTP;
    DROP TABLE IF EXISTS #ATGBalancing_FTP;
    DROP TABLE IF EXISTS #EqpBalances_FTP;


    -- =========================================================================
    -- STEP 1: Build dispensing dataset
    --   Part A: Last fill BEFORE the report period (provides opening reading)
    --   Part B: All fills WITHIN the report period
    -- =========================================================================
    SELECT * INTO #TempKPISARS_FTP
    FROM
    (
        -- Last fill before the period (opening balance carrier)
        SELECT * FROM (
            SELECT  u.EquipmentID 'Eqp1', MAX(CreateDate) 'MaxDate'
            FROM    UsageDispensing u
            WHERE   u.accountID = @account AND u.Volume > 0
            AND     u.createdate < @from   -- strict less-than: no overlap with Part B
            GROUP BY u.EquipmentID
        ) x
        INNER JOIN UsageDispensing u ON u.CreateDate = x.MaxDate AND u.EquipmentID = x.Eqp1

        UNION

        -- All fills within the period
        SELECT * FROM (
            SELECT  u.EquipmentID 'Eqp2', CreateDate 'MaxDate'
            FROM    UsageDispensing u
            WHERE   u.accountID = @account AND u.Volume > 0
            AND     u.createdate BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'
            GROUP BY u.EquipmentID, CreateDate
        ) x
        INNER JOIN UsageDispensing u ON u.CreateDate = x.MaxDate AND u.EquipmentID = x.Eqp2
    ) AS tmp;


    -- =========================================================================
    -- STEP 2: Enrich dispensing records with equipment, operator,
    --         allocation, asset, and reading data → #TempData_FTP
    --
    -- FIX 4 (Rev6): allc1/allc2 joined directly on AllocationID/AllocationID2.
    --               PEA still LEFT JOINed but only drives AssetAllocationDesc.
    --
    -- FIX 6 (Rev7): PEA join replaced with a ranked CTE subquery that:
    --               (a) de-duplicates multiple PEA rows for the same
    --                   EquipmentAssetID + Allocation1ID + Allocation2ID, and
    --               (b) falls back to an Allocation1ID-only match when no
    --                   exact Allocation1+Allocation2 row exists, so that
    --                   Asset Allocation Desc still pulls through for
    --                   Operation/Location combos not fully mapped in PEA.
    --               Priority: exact match (rank 1) preferred over fallback.
    -- =========================================================================
    SELECT
        u.id,
        e.id                            [Equipment_ID],
        e.Name                          [Name],
        e.Registration                  [Registration],
        pes.Maxlitres1                   [EqpMax],
        LAG(u.id) OVER (ORDER BY u.equipmentid)                            [UsageOpeningReadingID],
        CASE
            WHEN e.EquipmentMeasurementID = 2 THEN ISNULL(LAG(ROUND(u.Hour,2)) OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC),0)
            WHEN e.EquipmentMeasurementID = 3 THEN ISNULL(LAG(ROUND(u.KM,2))   OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC),0)
            WHEN e.EquipmentMeasurementID = 1 THEN 0
        END                                                                [OpeningReading],
        ISNULL(LAG(u.createdate) OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC), NULL) [OpeningReadingDate],
        ISNULL(LAG(u.Volume)     OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC), 0)    [OpeningVolume],
        u.id                                                               [UsageClosingReadingID],
        CASE
            WHEN e.EquipmentMeasurementID = 2 THEN ISNULL(ROUND(u.Hour,2),0)
            WHEN e.EquipmentMeasurementID = 3 THEN ISNULL(ROUND(u.KM,2),0)
            WHEN e.EquipmentMeasurementID = 1 THEN 0
        END                                                                [ClosingReading],
        u.createdate                                                       [ClosingReadingDate],
        CASE
            WHEN e.EquipmentMeasurementID = 2 THEN ROUND(ISNULL(CONVERT(real,ISNULL(ROUND(u.Hour,2),0)) - CONVERT(real,ISNULL(LAG(ROUND(u.Hour,2)) OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC),0)),0),2)
            WHEN e.EquipmentMeasurementID = 3 THEN ROUND(ISNULL(CONVERT(real,ISNULL(ROUND(u.KM,2),0))   - CONVERT(real,ISNULL(LAG(ROUND(u.KM,2))   OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC),0)),0),2)
            WHEN e.EquipmentMeasurementID = 1 THEN 0
        END                                                                [TotalReading],
        CASE
            WHEN u.Volume > 0 AND e.EquipmentMeasurementID = 3
            THEN ROUND((ISNULL(CONVERT(real,ISNULL(ROUND(u.KM,2),0)) - CONVERT(real,ISNULL(LAG(ROUND(u.KM,2)) OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC),0)),0)) / u.Volume, 2)
            ELSE 0
        END                                                                [KMPerLitre],
        CASE
            WHEN e.EquipmentMeasurementID = 2
             AND ISNULL(CONVERT(real,ISNULL(ROUND(u.Hour,2),0)) - CONVERT(real,ISNULL(LAG(ROUND(u.Hour,2)) OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC),0)),0) > 0
            THEN ROUND(u.Volume / ISNULL(CONVERT(real,ISNULL(ROUND(u.Hour,2),0)) - CONVERT(real,ISNULL(LAG(ROUND(u.Hour,2)) OVER (PARTITION BY u.equipmentid ORDER BY u.createdate ASC),0)),0), 2)
            ELSE 0
        END                                                                [LitrePerHour],
        p.Name                          [Product],
        ROUND(u.Volume,2)               [Volume],
        EMSS.Name                       [Measurement_Name],
        e.EquipmentMeasurementID        [Measurement_ID],
        A.Name                          [Account],
        YEAR(u.CreateDate)              [Year],
        MONTH(u.CreateDate)             [Month],
        DAY(u.CreateDate)               [Day],
        u.storeid                       [Store_ID],
        s.Name                          [Store],
        u.ID                            [Usage_ID],
        u.createdate                    [Date],
        CONVERT(varchar(50), u.CreateDate, 108)  AS [Time],
        CONVERT(varchar(50), u.CreateDate, 111)  AS [DateOnly],
        ISNULL(u.AuthorizationID,0)     [AuthorizationID],
        ISNULL(Auth.Name,   'N/A')      [Authorization],
        ISNULL(u.OperatorID,0)          [OperatorID],
        ISNULL(Oper.Name,   'N/A')      [Operator],
        ISNULL(u.DriverID,  0)          [DriverID],
        ISNULL(Drv.Name,    'N/A')      [Driver],
        ISNULL(CST.id,      0)          [CID],
        ISNULL(CST.name,    'N/A')      [Costcentre],
        ISNULL(CST.Description,'N/A')   [CostcentreDesc],
        ISNULL(ME.ID,       0)          [MID],
        ISNULL(ME.Name,     'N/A')      [MasterEquipment],
        ISNULL(allc1.ID,    0)          [AID1],
        ISNULL(allc1.Name,  'N/A')      [Allocation1],
        ISNULL(allc1.Description,'N/A') [AID1DescOperation],
        ISNULL(allc2.ID,    0)          [AID2],
        ISNULL(allc2.Name,  'N/A')      [Allocation2],
        ISNULL(allc2.Description,'N/A') [AID2DescLocation],
        e.Consumption,
        u.[Description],
        u.FuelPrice,
        ER.ID                           [ERID],
        ER.[Name]                       [Rebate],
        u.JobNumber,
        e.tag                           [Eqptag],
        u.spare1,
        u.InformationRec,
        u.Recnumber,
        u.Totalizer                     [Totalizer],
        AR1.[ID]                        [AR1ID],
        AR1.[Name]                      [AR1Name],
        AR2.[ID]                        [AR2ID],
        AR2.[Name]                      [AR2Name],
        ISNULL(EA.[ID],0)               [EquipmentAID],
        ISNULL(EA.[AssetID],    'N/A')  [EquipmentAssetID],
        ISNULL(EA.[EquipmentRebateID],0)[EquipmentAssetRebateID],
        ISNULL(EA.[Name],       'N/A')  [EquipmentAssetName],
        ISNULL(EA.[Description],'N/A')  [EquipmentAssetDesc],
        ISNULL(PEA.[ID],0)              [PerEquipmentAssetAllocationID],
        -- FIX 6: PEA desc now comes from ranked/fallback subquery (see join below)
        ISNULL(PEA.[Description],'N/A') [PerEquipmentAssetAllocationDesc],
        ISNULL(PEA.[Allocation1ID],0)   [PerEquipmentAssetAllocationAllocation1ID],
        ISNULL(PEA.[Allocation2ID],0)   [PerEquipmentAssetAllocationAllocation2ID],
        ISNULL(u.[TotalizerEnd],0)      [TotalizerEnd],
        ISNULL(u.[UnqTrID],0)           [UnqTrID]

    INTO [#TempData_FTP]

    FROM  #TempKPISARS_FTP u
    INNER JOIN Account          A       ON  u.accountID         = A.ID
    INNER JOIN Store            s       ON  u.Storeid           = s.ID
    LEFT  JOIN Product          p       ON  u.ProductID         = P.ID
    LEFT  JOIN Equipment        e       ON  u.EquipmentID       = e.ID
    LEFT JOIN PerEquipmentStore pes     on e.ID = pes.EquipmentID AND s.ID = pes.StoreID
    LEFT  JOIN EquipmentMeasurement EMSS ON e.EquipmentMeasurementID = EMSS.ID
    LEFT  JOIN Operator         Auth    ON  u.AuthorizationID   = Auth.ID
    LEFT  JOIN Operator         Oper    ON  u.OperatorID        = Oper.ID
    LEFT  JOIN Operator         Drv     ON  u.DriverID          = Drv.ID
    LEFT  JOIN dbo.EquipmentCostCentre         CST  ON CST.ID  = U.[EquipmentCostCentreID]
    LEFT  JOIN dbo.PerEquipmentMasterGroup     PEG  ON PEG.EquipmentID = u.EquipmentID
    LEFT  JOIN dbo.EquipmentMasterGroup        ME   ON ME.ID   = PEG.EquipmentMasterGroupID
    -- FIX 4 (Rev6): allc1/allc2 joined directly — independent of PEA
    LEFT  JOIN dbo.Allocation                  allc1 ON u.AllocationID  = allc1.ID
    LEFT  JOIN dbo.Allocation                  allc2 ON u.AllocationID2 = allc2.ID
    LEFT  JOIN [dbo].[EquipmentRebate]         ER   ON e.EquipmentRebateID = ER.ID
    LEFT  JOIN [dbo].[AllocationRebate]        AR1  ON AR1.ID = allc1.AllocationRebateID
    LEFT  JOIN [dbo].[AllocationRebate]        AR2  ON AR2.ID = allc2.AllocationRebateID
    LEFT  JOIN [dbo].[EquipmentAsset]          EA   ON EA.ID  = e.EquipmentAssetID

    -- -------------------------------------------------------------------------
    -- FIX 6 (Rev7): Ranked PEA subquery
    --
    -- Logic:
    --   MatchType 1 = exact match on both Allocation1ID AND Allocation2ID
    --   MatchType 2 = fallback: matches only on Allocation1ID
    --                (used when the specific Location/Allocation2 combo has
    --                 no PEA record but the Operation/Allocation1 does)
    --
    -- ROW_NUMBER orders by MatchType ASC so exact match always wins.
    -- Only rn = 1 is joined, ensuring one PEA row per usage record.
    -- -------------------------------------------------------------------------
    LEFT  JOIN (
        SELECT
            p2.*,
            ROW_NUMBER() OVER (
                PARTITION BY p2.EquipmentAssetID,
                             p2.Allocation1ID,
                             p2.Allocation2ID
                ORDER BY p2.ID ASC
            ) AS dedup_rn,
            1 AS MatchType   -- exact match rows
        FROM [dbo].[PerEquipmentAssetAllocation] p2
        UNION ALL
        SELECT
            p3.*,
            ROW_NUMBER() OVER (
                PARTITION BY p3.EquipmentAssetID,
                             p3.Allocation1ID,
                             p3.Allocation2ID
                ORDER BY p3.ID ASC
            ) AS dedup_rn,
            2 AS MatchType   -- fallback rows (Allocation1 only)
        FROM [dbo].[PerEquipmentAssetAllocation] p3
    ) PEA_RANKED
        ON  PEA_RANKED.EquipmentAssetID = EA.ID
        AND PEA_RANKED.Allocation1ID    = U.AllocationID
        AND (
                -- Exact match: both Allocation1 and Allocation2 match
                (PEA_RANKED.MatchType = 1 AND PEA_RANKED.Allocation2ID = U.AllocationID2)
             OR
                -- Fallback: only Allocation1 matches; Allocation2 either
                -- not mapped in PEA or not captured on the usage record
                (PEA_RANKED.MatchType = 2
                 AND PEA_RANKED.dedup_rn = 1
                 AND NOT EXISTS (
                     SELECT 1
                     FROM [dbo].[PerEquipmentAssetAllocation] px
                     WHERE px.EquipmentAssetID = EA.ID
                       AND px.Allocation1ID    = U.AllocationID
                       AND px.Allocation2ID    = U.AllocationID2
                 ))
            )
        AND PEA_RANKED.dedup_rn = 1
    -- Alias back to PEA for consistency with the rest of the query
    LEFT  JOIN [dbo].[PerEquipmentAssetAllocation] PEA
               ON PEA.ID = PEA_RANKED.ID

    WHERE u.accountID = @account AND U.Volume > 0
    GROUP BY
        e.ID, e.Registration, e.Name, u.ID, u.AccountID, A.Name, u.RecordTypeID,
        u.StoreID, S.Name, u.EquipmentID, e.Tag, u.ProductID, P.Name,
        u.OperatorID, u.DriverID, u.AuthorizationID, u.AllocationID,
        allc1.ID, allc1.Name, allc1.Description,
        u.AllocationID2, allc2.ID, allc2.Name, allc2.Description,
        u.KM, u.Hour, u.Volume, u.EquipmentTagfromField,
        u.InformationReg, u.InformationOpr, u.InformationDrv,
        u.InformationAth, u.InformationAllocation, u.InformationMac,
        u.Createdate, CST.ID, CST.Name, CST.Description,
        ME.ID, ME.Name, Oper.Name, Drv.Name, EMSS.Name,
        e.Consumption, Auth.Name, S.StoreTypeID,
        u.Description, u.FuelPrice, ER.ID, ER.Name,pes.Maxlitres1,
        e.EquipmentMeasurementID, u.JobNumber, e.tag, u.spare1,
        u.InformationRec, u.Recnumber,
        AR1.[ID], AR1.[Name], AR2.[ID], AR2.[Name],
        u.Totalizer, allc1.Description, allc2.Description,
        EA.[ID], EA.[AssetID], EA.[EquipmentRebateID], EA.[Name], EA.[Description],
        PEA.[ID], PEA.[Description], PEA.[Allocation1ID], PEA.[Allocation2ID],
        u.[TotalizerEnd], u.[UnqTrID]

    ORDER BY e.registration ASC, u.ID ASC;


    -- =========================================================================
    -- STEP 2b: Calculate per-asset equipment tank balances
    --
    -- FIX 2 (Rev6): [Usage] (LEAD of next fill volume) carried through all
    --               CTEs and stored in #EqpBalances_FTP as [Eqp_Usage].
    -- =========================================================================
    ;WITH cte_EqpBalanceRaw AS
    (
        SELECT
            [Usage_ID],
            [Equipment_ID],
            [ClosingReadingDate],
            [Volume],
            ISNULL([EqpMax], 0)                                             AS [EqpMax],
            ISNULL([EqpMax], 0)                                             AS [Eqp_Ltthatcanbeused],
            LEAD(ROUND([Volume],2))
                OVER (PARTITION BY [Equipment_ID] ORDER BY [ClosingReadingDate] ASC)
                                                                            AS [Usage],
            ROW_NUMBER()
                OVER (PARTITION BY [Equipment_ID] ORDER BY [ClosingReadingDate] ASC)
                                                                            AS [RowNum]
        FROM  #TempData_FTP
    ),
    cte_EqpBalanceCalc AS
    (
        SELECT
            [Usage_ID],
            [Equipment_ID],
            [ClosingReadingDate],
            [Volume],
            [EqpMax],
            [Eqp_Ltthatcanbeused],
            [Usage],
            [RowNum],
            CASE
                WHEN [Usage] IS NOT NULL
                THEN ROUND([EqpMax] - [Usage], 2)
                ELSE NULL
            END                                                             AS [Eqp_ClosingBalance]
        FROM  cte_EqpBalanceRaw
    ),
    cte_EqpWithOpening AS
    (
        SELECT
            c.[Usage_ID],
            c.[Equipment_ID],
            c.[ClosingReadingDate],
            c.[EqpMax],
            c.[Eqp_Ltthatcanbeused],
            c.[Usage],
            c.[Eqp_ClosingBalance],
            CASE
                WHEN c.[RowNum] = 1
                THEN ROUND(c.[EqpMax] - c.[Volume], 2)
                ELSE LAG(c.[Eqp_ClosingBalance])
                         OVER (PARTITION BY c.[Equipment_ID] ORDER BY c.[ClosingReadingDate] ASC)
            END                                                             AS [Eqp_OpeningBalance]
        FROM  cte_EqpBalanceCalc c
    )
    SELECT
        [Usage_ID],
        [Eqp_OpeningBalance],
        [Eqp_Ltthatcanbeused],
        ISNULL([Usage], 0)                                                  AS [Eqp_Usage],
        [Eqp_ClosingBalance]
    INTO  #EqpBalances_FTP
    FROM  cte_EqpWithOpening;


    -- =========================================================================
    -- STEP 3: ATG Tank stock reconciliation (unchanged from Rev 6)
    -- =========================================================================

    -- STEP 3a: Opening and closing ATG readings per tank per day
    SELECT * INTO #TempOpening_FTP
    FROM
    (
        SELECT * FROM (
            SELECT  s.TankID 'Tank1', MIN(CreateDate) 'MaxDate', CONVERT(varchar(50), CreateDate,111) 'Date'
            FROM    Stock s
            WHERE   s.accountID = @account
            AND     s.createdate BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'
            GROUP BY s.TankID, CONVERT(varchar(50), CreateDate,111)
        ) x
        INNER JOIN Stock s ON s.CreateDate = x.MaxDate AND s.TankID = x.Tank1
        UNION
        SELECT * FROM (
            SELECT  s.TankID 'Tank2', MAX(CreateDate) 'MaxDate', CONVERT(varchar(50), CreateDate,111) 'Date'
            FROM    Stock s
            WHERE   s.accountID = @account
            AND     s.createdate BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'
            GROUP BY s.TankID, CONVERT(varchar(50), CreateDate,111)
        ) x
        INNER JOIN Stock s ON s.CreateDate = x.MaxDate AND s.TankID = x.Tank2
    ) AS tmp;

    -- STEP 3b: Pair each reading with the previous reading (LAG)
    SELECT
        t.ID                                                                [TID],
        t.TankName,
        t.Capacity,
        LAG(u.id) OVER (ORDER BY u.tankID)                                 [OpeningReadingID],
        ISNULL(LAG(u.createdate) OVER (PARTITION BY u.tankID ORDER BY u.createdate ASC), u.createdate)          [OpeningVolumeReadingDate],
        ISNULL(LAG(ROUND(u.Volume,2)) OVER (PARTITION BY u.tankID ORDER BY u.createdate ASC), ROUND(u.Volume,2))[OpeningVolumeReading],
        u.id                                                               [CurrentReadingID],
        u.createdate                                                       [CurrentReadingDate],
        ROUND(u.Volume,2)                                                  [CurrentVolume]
    INTO [#TempStockDataRaw_FTP]
    FROM  #TempOpening_FTP  u
    INNER JOIN Account  A ON u.accountID = A.ID
    INNER JOIN Store    s ON u.Storeid   = s.ID
    INNER JOIN TANK     T ON u.TankID    = T.ID
    WHERE u.accountID = @account
    AND   u.createdate BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'
    ORDER BY u.createdate ASC, t.ID ASC, u.ID ASC;

    -- STEP 3c: Detect deliveries via volume jump > 3500 litres
    SELECT
        x.TankID,
        ss.ID  'ssID',  x.StockOpeningReadingID,  ss.Volume  'ssVolume',  ss.CreateDate 'ssCreatedate',
        sss.ID 'sssID', x.StockCurrentReadingID,  sss.Volume 'sssVolume', sss.CreateDate 'sssCreatedate',
        IIF((ss.Volume - sss.Volume) > 3500, ss.Volume,
            IIF((ss.Volume - sss.Volume) < 0, ss.Volume, sss.Volume))     AS Saleable,
        CONVERT(varchar(50), ss.CreateDate, 111)                           [Date]
    INTO [#TempMinMaxReadingRaw_FTP]
    FROM
    (
        SELECT
            s.TankID,
            ISNULL(LAG(s.id)         OVER (PARTITION BY s.tankID ORDER BY s.createdate ASC), s.ID)         [StockOpeningReadingID],
            ISNULL(LAG(s.createdate) OVER (PARTITION BY s.tankID ORDER BY s.createdate ASC), s.createdate) [StockOpeningReadingDate],
            s.ID          [StockCurrentReadingID],
            s.createdate  [StockCurrentReadingDate]
        FROM  Stock s
        WHERE s.accountID = @account
        AND   s.createdate BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'
        AND   s.TankID != 0
    ) x
    INNER JOIN stock ss  ON ss.ID  = x.[StockOpeningReadingID]
    INNER JOIN stock sss ON sss.ID = x.[StockCurrentReadingID]
    ORDER BY x.StockCurrentReadingDate ASC, x.TankID ASC;

    -- STEP 3d: Min/max saleable volume per tank per day
    SELECT [Date], TankID, MIN(Saleable) 'minVolume', MAX(Saleable) 'maxVolume'
    INTO [#TempMinMaxReading_FTP]
    FROM  [#TempMinMaxReadingRaw_FTP]
    GROUP BY [Date], TankID
    ORDER BY [Date] ASC;

    -- STEP 3e: Delivery detection
    SELECT
        xx.[Date],  xx.TID,  xx.TankName 'Tank',
        uumin.CreateDate 'O/S Date', uumin.Volume 'O/S',
        uumax.CreateDate 'C/S Date', uumax.Volume 'C/S',
        CASE WHEN (ISNULL(ABS(uumin.Volume - TTT.maxVolume),0) > 3500)
             THEN ISNULL(ROUND(TTT.maxVolume - TTT.minVolume,2),0) ELSE 0 END  'Delivery1',
        CASE WHEN ISNULL(uumax.Volume - uumin.Volume,0) > 0
             THEN CASE WHEN (ISNULL(ABS(uumax.Volume - uumin.Volume),0) > 3500)
                       THEN uumax.Volume - uumin.Volume ELSE 0 END
             ELSE 0 END  'Delivery2'
    INTO [#Delivery_FTP]
    FROM
    (
        SELECT CONVERT(varchar(50), TSDR.CurrentReadingDate,111) 'Date',
               TID, TankName, MIN(TSDR.OpeningReadingID) 'minID', MAX(TSDR.CurrentReadingID) 'maxID',
               TSDR.Capacity
        FROM   [#TempStockDataRaw_FTP] TSDR
        WHERE  TSDR.[CurrentReadingDate] BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'
        GROUP BY CONVERT(varchar(50), TSDR.CurrentReadingDate,111), TSDR.TID, TSDR.TankName, TSDR.Capacity
    ) xx
    INNER JOIN stock uumin ON uumin.ID = xx.minID
    INNER JOIN stock uumax ON uumax.ID = xx.maxID
    INNER JOIN #TempMinMaxReading_FTP TTT ON xx.[Date] = TTT.[Date] AND TTT.TankID = xx.TID
    ORDER BY xx.[Date] ASC, xx.TID ASC;

    -- STEP 3f: Final daily ATG balances
    SELECT
        @account 'AccountID',
        xx.[Date], xx.TID, xx.TankName 'Tank',
        uumin.CreateDate  'O/S Date', uumin.Volume 'O/S',
        CASE
            WHEN uumin.Volume = uumax.Volume THEN 0
            WHEN uumax.Volume < uumin.Volume THEN ISNULL(uumin.Volume - uumax.Volume, 0)
            WHEN (uumax.Volume - uumin.Volume) > 3500
            THEN IIF(((uumin.Volume + ISNULL(ROUND(TTT.maxVolume - TTT.minVolume,2),0)) - uumax.Volume) < 0,
                     0,
                     ((uumin.Volume + ISNULL(ROUND(TTT.maxVolume - TTT.minVolume,2),0)) - uumax.Volume))
            ELSE 0
        END 'Consumption',
        CASE
            WHEN DEL.Delivery1 > DEL.Delivery2 THEN DEL.Delivery1
            WHEN DEL.Delivery1 < DEL.Delivery2 THEN DEL.Delivery2
            ELSE 0
        END 'Delivery',
        uumax.CreateDate 'C/S Date', uumax.Volume 'C/S',
        CASE
            WHEN uumax.Volume > xx.Capacity THEN xx.Capacity
            WHEN uumax.Volume < xx.Capacity THEN ISNULL(xx.Capacity - uumax.Volume, 0)
        END 'Ullage',
        CASE WHEN (ISNULL(ABS(uumin.Volume - TTT.maxVolume),0) > 3500)
             THEN ISNULL(TTT.minVolume, 0) ELSE 0 END 'BeforeDelivery',
        CASE WHEN (ISNULL(ABS(uumin.Volume - TTT.maxVolume),0) > 3500)
             THEN ISNULL(TTT.maxVolume, 0) ELSE 0 END 'AfterDelivery',
        xx.Capacity
    INTO [#TempData_Final_FTP]
    FROM
    (
        SELECT CONVERT(varchar(50), TSDR.CurrentReadingDate,111) 'Date',
               TID, TankName, MIN(TSDR.OpeningReadingID) 'minID', MAX(TSDR.CurrentReadingID) 'maxID',
               TSDR.Capacity
        FROM   [#TempStockDataRaw_FTP] TSDR
        WHERE  TSDR.[CurrentReadingDate] BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'
        GROUP BY CONVERT(varchar(50), TSDR.CurrentReadingDate,111), TSDR.TID, TSDR.TankName, TSDR.Capacity
    ) xx
    INNER JOIN stock uumin ON uumin.ID = xx.minID
    INNER JOIN stock uumax ON uumax.ID = xx.maxID
    INNER JOIN #TempMinMaxReading_FTP TTT ON xx.[Date] = TTT.[Date] AND TTT.TankID = xx.TID
    INNER JOIN [#Delivery_FTP] DEL ON xx.[Date] = DEL.[Date] AND DEL.TID = xx.TID
    ORDER BY xx.[Date] ASC, xx.TID ASC;

    SELECT
        f.AccountID, f.[Date], f.TID 'TankID', f.Tank,
        f.[O/S Date], CONVERT(varchar(50), f.[O/S Date], 111) 'OS_DateOnly', f.[O/S],
        f.Consumption, f.Delivery,
        f.[C/S Date], CONVERT(varchar(50), f.[C/S Date], 111) 'CS_DateOnly', f.[C/S],
        f.Ullage, f.BeforeDelivery, f.AfterDelivery, f.Capacity
    INTO [#ATGBalancing_FTP]
    FROM  [#TempData_Final_FTP] f;


    -- =========================================================================
    -- STEP 4: Build combined SARS output table (#FAMSSARS_FTP)
    --
    -- FIX 1 (Rev6): TankOpeningVolume/TankClosingVolume explicitly '0'/'N/A'
    --               for Dispensing. Date columns added.
    -- FIX 2 (Rev6): Eqp_Usage added from #EqpBalances_FTP.
    -- FIX 3 (Rev6): Eligible_NonEligible column added.
    -- FIX 4 (Rev6): Operation and Location from allc1/allc2 directly.
    -- FIX 5 (Rev7): Eligible_NonEligible logic corrected — 'Not qualified'
    --               in PerEquipmentAssetAllocationDesc forces 'Non-Eligible'
    --               BEFORE any rebate ID check. Rebate IDs now compared > 0
    --               (not = 1) to correctly detect any linked rebate record.
    -- =========================================================================

    -- ── RecordType 1: Dispensing ─────────────────────────────────────────────
    SELECT
        @account                                                            'AccountID',
        '1'                                                                 'RecordTypeID',
        'Dispensing'                                                        'RecordType',
        d.ID                                                                'FillID',
        CONVERT(varchar(50),[Year]) + '-' + CONVERT(varchar(50),[Month])   'Period',
        [DateOnly],
        [Time],
        [Date],

        -- FIX 1 (Rev6): Dispensing has no ATG tank link
        '0'                                                                 'TankOpeningVolume',
        'N/A'                                                               'TankOpeningVolumeDate',
        '0'                                                                 'TankID',
        'N/A'                                                               'Tank',
        '0'                                                                 'StockRecDate',
        '0'                                                                 'StockRecInvoiceNr',
        '0'                                                                 'StockRecDeliveryNote',
        '0'                                                                 'StockRecFuelSupplier',
        '0'                                                                 'StockRecDescription',
        '0'                                                                 'StockRecVolume',
        '0'                                                                 'StockRecVolumeCalc',
        '0'                                                                 'TankClosingVolume',
        'N/A'                                                               'TankClosingVolumeDate',

        CONVERT(varchar(100), Totalizer)                                    'MeterPreDisp',
        CONVERT(varchar(100), TotalizerEnd)                                 'MeterPostDisp',
        [Store]                                                             'Source',
        [Product],
        [Registration],
        [Volume],
        EquipmentAssetName                                                  'AssetGroup',
        [EquipmentAssetID]                                                  'AssetID',
        EquipmentAssetDesc                                                  'AssetDescription',
        [OpeningReading]                                                    'OpenReading',
        [ClosingReading]                                                    'ClosingReading',
        [TotalReading]                                                      'Worked',
        [Measurement_Name]                                                  'Measurement',
        [KMPerLitre],
        [LitrePerHour],
        -- FIX 4 (Rev6): Operation/Location sourced from allc1/allc2 directly
        [Allocation1]                                                       'Operation',
        [AID1DescOperation]                                                 'Operation_Desc',
        [Allocation2]                                                       'Location',
        [AID2DescLocation]                                                  'Location_Desc',
        PerEquipmentAssetAllocationDesc                                     'AssetAllocationDesc',
        [Driver],
        [Operator]                                                          'FuelAttendant',
        [Costcentre],
        ISNULL(NULLIF(CONVERT(varchar(50), eb.Eqp_OpeningBalance),  ''), '0')  'Eqp_OpeningBalance',
        ISNULL(NULLIF(CONVERT(varchar(50), eb.Eqp_Ltthatcanbeused), ''), '0')  'Eqp_Ltthatcanbeused',
        -- FIX 2 (Rev6): Eqp_Usage — litres consumed between this fill and next
        ISNULL(NULLIF(CONVERT(varchar(50), eb.Eqp_Usage),           ''), '0')  'Eqp_Usage',
        ISNULL(NULLIF(CONVERT(varchar(50), eb.Eqp_ClosingBalance),  ''), '0')  'Eqp_ClosingBalance',

        -- ─────────────────────────────────────────────────────────────────────
        -- FIX 5 (Rev7): Corrected Eligible_NonEligible logic
        --
        -- Rule priority (evaluated top to bottom):
        --   1. If PEA description contains 'Not qualified' → Non-Eligible
        --      regardless of any rebate ID. This correctly handles vehicles
        --      like CDW947NC (WingerdBestuur) where a rebate record exists
        --      but the activity is explicitly disqualified.
        --   2. If EquipmentRebate ID > 0 → Eligible
        --   3. If AllocationRebate 1 ID > 0 → Eligible
        --   4. If AllocationRebate 2 ID > 0 → Eligible
        --   5. Otherwise → Non-Eligible
        --
        -- Changed from Rev6: 
        --   - 'Not qualified' guard added as highest priority
        --   - Comparison changed from = 1 to > 0 (catches any rebate ID,
        --     not just the record that happens to have primary key = 1)
        -- ─────────────────────────────────────────────────────────────────────
        CASE
            WHEN ISNULL(d.PerEquipmentAssetAllocationDesc, '')
                 LIKE '%Not qualified%'                        THEN 'Non-Eligible'
            WHEN ISNULL(d.[ERID],  0) > 0                     THEN 'Eligible'
            WHEN ISNULL(d.[AR1ID], 0) > 0                     THEN 'Eligible'
            WHEN ISNULL(d.[AR2ID], 0) > 0                     THEN 'Eligible'
            ELSE 'Non-Eligible'
        END                                                                 'Eligible_NonEligible'

    INTO [#FAMSSARS_FTP]

    FROM  #TempData_FTP d
    LEFT JOIN #EqpBalances_FTP eb ON eb.Usage_ID = d.Usage_ID
    WHERE d.[ClosingReadingDate] >= @from + ' 00:00:00'

    UNION

    -- ── RecordType 2: Transfers ──────────────────────────────────────────────
    SELECT
        @account                                                            'AccountID',
        '2'                                                                 'RecordTypeID',
        'Transfer'                                                          'RecordType',
        gut.[ID]                                                            'FillID',
        CONVERT(varchar(50),gut.[year]) + '-' + CONVERT(varchar(50),gut.[Month]) 'Period',
        gut.[DateOnly], gut.[Time], gut.[Date],
        '0'    'TankOpeningVolume',
        'N/A'  'TankOpeningVolumeDate',
        '0'    'TankID',
        'N/A'  'Tank',
        CONVERT(varchar(50),'0') 'StockRecDate',
        '0' 'StockRecInvoiceNr', '0' 'StockRecDeliveryNote',
        '0' 'StockRecFuelSupplier', '0' 'StockRecDescription',
        '0' 'StockRecVolume', '0' 'StockRecVolumeCalc',
        '0'    'TankClosingVolume',
        'N/A'  'TankClosingVolumeDate',
        CONVERT(varchar(100), Totalizer)    'MeterPreDisp',
        CONVERT(varchar(100), TotalizerEnd) 'MeterPostDisp',
        gut.[Store] 'Source', gut.[Product], gut.[Registration], gut.[Volume],
        'N/A' 'AssetGroup', '0' 'AssetID', 'N/A' 'AssetDescription',
        '0' 'OpenReading', '0' 'ClosingReading', '0' 'Worked',
        'N/A' 'Measurement', '0' 'KMPerLitre', '0' 'LitrePerHour',
        'N/A' 'Operation', 'N/A' 'Operation_Desc',
        'N/A' 'Location', 'N/A' 'Location_Desc', 'N/A' 'AssetAllocationDesc',
        'N/A' 'Driver', 'N/A' 'FuelAttendant', 'N/A' 'Costcentre',
        'N/A' 'Eqp_OpeningBalance',
        'N/A' 'Eqp_Ltthatcanbeused',
        '0'   'Eqp_Usage',
        'N/A' 'Eqp_ClosingBalance',
        'N/A' 'Eligible_NonEligible'
    FROM  [dbo].[GetFueltransfers] gut
    WHERE accountid = @account
    AND   [Date] BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59'

    UNION

    -- ── RecordType 3: Stock Received (Manual) ────────────────────────────────
    SELECT
        @account                                                            'AccountID',
        '3'                                                                 'RecordTypeID',
        'StockReceivedManual'                                               'RecordType',
        gurm.[ID]                                                           'FillID',
        CONVERT(varchar(50),gurm.[year]) + '-' + CONVERT(varchar(50),gurm.[Month]) 'Period',
        gurm.[DateOnly], gurm.[Time], gurm.[Date],
        '0'    'TankOpeningVolume',
        'N/A'  'TankOpeningVolumeDate',
        gurm.TankID 'TankID',
        gurm.TankName 'Tank',
        CONVERT(varchar(50),gurm.[Date],111) 'StockRecDate',
        gurm.[InvoiceNr]   'StockRecInvoiceNr',
        gurm.[DeliveryNote]'StockRecDeliveryNote',
        gurm.[FuelSupplier]'StockRecFuelSupplier',
        gurm.[Description] 'StockRecDescription',
        gurm.[Volume]      'StockRecVolume',
        '0'    'StockRecVolumeCalc',
        '0'    'TankClosingVolume',
        'N/A'  'TankClosingVolumeDate',
        '0' 'MeterPreDisp', '0' 'MeterPostDisp',
        gurm.[Store] 'Source', gurm.[Product],
        'N/A' [Registration], '0' 'Volume',
        'N/A' 'AssetGroup', '0' 'AssetID', 'N/A' 'AssetDescription',
        '0' 'OpenReading', '0' 'ClosingReading', '0' 'Worked',
        'N/A' 'Measurement', '0' 'KMPerLitre', '0' 'LitrePerHour',
        'N/A' 'Operation', 'N/A' 'Operation_Desc',
        'N/A' 'Location', 'N/A' 'Location_Desc', 'N/A' 'AssetAllocationDesc',
        'N/A' 'Driver', 'N/A' 'FuelAttendant', 'N/A' 'Costcentre',
        'N/A' 'Eqp_OpeningBalance',
        'N/A' 'Eqp_Ltthatcanbeused',
        '0'   'Eqp_Usage',
        'N/A' 'Eqp_ClosingBalance',
        'N/A' 'Eligible_NonEligible'
    FROM  [dbo].[GetFuelReceivingManual] gurm
    WHERE accountid = @account
    AND   [Date] BETWEEN @from + ' 00:00:00' AND @to + ' 23:59:59';


    -- =========================================================================
    -- STEP 5: Deduplicate and return final result set
    -- =========================================================================
    WITH cte_DuplicateDispensing AS
    (
        SELECT
            ROW_NUMBER() OVER (PARTITION BY SAR.FillID, SAR.AccountID ORDER BY SAR.[Date]) rnk,
            SAR.FillID,
            SAR.AccountID,
            SAR.RecordTypeID,
            SAR.RecordType,
            SAR.[Period],
            SAR.[DateOnly],
            SAR.[Time],
            SAR.[Date],
            SAR.TankOpeningVolume,
            SAR.TankOpeningVolumeDate,
            SAR.TankID,
            SAR.Tank,
            SAR.StockRecDate,
            SAR.StockRecInvoiceNr,
            SAR.StockRecDeliveryNote,
            SAR.StockRecFuelSupplier,
            SAR.StockRecDescription,
            SAR.StockRecVolume,
            SAR.StockRecVolumeCalc,
            SAR.TankClosingVolume,
            SAR.TankClosingVolumeDate,
            ROUND(SAR.MeterPreDisp,  2) 'MeterPreDisp',
            ROUND(SAR.MeterPostDisp, 2) 'MeterPostDisp',
            SAR.[Source],
            SAR.[Product],
            SAR.[Registration],
            SAR.[Volume],
            SAR.AssetGroup,
            SAR.AssetID,
            SAR.AssetDescription,
            SAR.OpenReading,
            SAR.ClosingReading,
            SAR.Worked,
            SAR.Measurement,
            SAR.KMPerLitre,
            SAR.LitrePerHour,
            SAR.Operation,
            SAR.Operation_Desc,
            SAR.[Location],
            SAR.Location_Desc,
            SAR.AssetAllocationDesc,
            SAR.Driver,
            SAR.FuelAttendant,
            SAR.Costcentre,
            ISNULL(NULLIF(SAR.Eqp_OpeningBalance,  ''), '0')   Eqp_OpeningBalance,
            ISNULL(NULLIF(SAR.Eqp_Ltthatcanbeused, ''), '0')   Eqp_Ltthatcanbeused,
            ISNULL(NULLIF(SAR.Eqp_Usage,           ''), '0')   Eqp_Usage,
            ISNULL(NULLIF(SAR.Eqp_ClosingBalance,  ''), '0')   Eqp_ClosingBalance,
            -- FIX 5 (Rev7): Eligible_NonEligible passed through as-is
            --               (logic already applied correctly in STEP 4)
            SAR.Eligible_NonEligible
        FROM  #FAMSSARS_FTP SAR
    )
    SELECT * FROM cte_DuplicateDispensing
    WHERE  rnk = 1
    AND    TankID IS NOT NULL
    ORDER BY [Date] ASC;


    -- =========================================================================
    -- STEP 6: Cleanup — drop all temp tables
    -- =========================================================================
    IF OBJECT_ID('tempdb.dbo.#TempKPISARS_FTP', 'U') IS NOT NULL DROP TABLE #TempKPISARS_FTP;
    IF OBJECT_ID('tempdb.dbo.#TempData_FTP',     'U') IS NOT NULL DROP TABLE #TempData_FTP;

    DROP TABLE IF EXISTS #TempOpening_FTP;
    DROP TABLE IF EXISTS #TempStockDataRaw_FTP;
    DROP TABLE IF EXISTS #TempMinMaxReadingRaw_FTP;
    DROP TABLE IF EXISTS #TempMinMaxReading_FTP;
    DROP TABLE IF EXISTS #Delivery_FTP;
    DROP TABLE IF EXISTS #TempData_Final_FTP;
    DROP TABLE IF EXISTS #FAMSSARS_FTP;
    DROP TABLE IF EXISTS #ATGBalancing_FTP;
    DROP TABLE IF EXISTS #EqpBalances_FTP;

END
