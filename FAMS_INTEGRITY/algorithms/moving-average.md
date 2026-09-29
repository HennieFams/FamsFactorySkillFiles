# Moving Average

Use a trailing moving average per equipment/store to detect gradual drift
(e.g. a slow leak or gradual miscalibration) that a single-point z-score
would miss. Compute daily totals per equipment, then a 7/14/30-day trailing
average, and flag sustained deviation rather than single-day spikes.
