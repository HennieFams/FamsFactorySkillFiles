# Z-Score

`z = (x - mean) / stdev`. Good for roughly-normal volume distributions per
equipment. Common threshold in this domain: |z| > 3. If a distribution is
heavily skewed or has many zero/near-zero transactions, prefer IQR-based
outlier detection instead (median ± 1.5×IQR) — z-score will under- or
over-flag on skewed data.
