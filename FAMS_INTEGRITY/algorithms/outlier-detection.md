# Outlier Detection

General approach for flagging abnormal volumes per equipment:

```sql
WITH stats AS (
    SELECT EquipmentID, AVG(Volume) AS mean_vol, STDEV(Volume) AS sd_vol
    FROM UsageDispensing
    WHERE AccountID = {AccountID} AND Createdate >= '{StartDate}' AND Volume > 0
    GROUP BY EquipmentID
)
SELECT u.*, s.mean_vol, s.sd_vol,
       (u.Volume - s.mean_vol) / NULLIF(s.sd_vol, 0) AS z_score
FROM UsageDispensing u
JOIN stats s ON u.EquipmentID = s.EquipmentID
WHERE u.AccountID = {AccountID} AND u.Createdate >= '{StartDate}'
  AND ABS((u.Volume - s.mean_vol) / NULLIF(s.sd_vol, 0)) > 3
ORDER BY u.Createdate;
```
If the distribution is skewed (common for fuel volumes), prefer an IQR rule
over z-score — see `algorithms/z-score.md` for when each applies.
