---
name: fams-tanks-business-specialized
description: Use when calculating tank volume from depth (horizontal cylinder geometry or strapping table interpolation), classifying capacity/fill status (the 95%/85%/15%/5% threshold matrix), determining telemetry offline status (10-minute rule), or building Tank/TankStatus/TelemetrySnapshot domain models. Consumes parsed data from fams-atg-communications; feeds display data to fams-vue-core.
---

# FAMS Tank Core Business Logic — Specialized Skill

## 📋 Metadata
| Field | Value |
|-------|-------|
| **VERSION** | 1.0.0 (Pilot #1 Grounded) |
| **OWNER** | Operations & IoT Leader (Team 09) |
| **STATUS** | ✅ VALID |
| **VALIDATED** | 2026-09-01 |
| **DEPENDENCIES** | `/src/FAMS.Core/Domain/Tanks/`, fams-atg-communications/SKILL.md |
| **TESTED** | Claude 3.5 Sonnet (Challenger Verified) |
| **NEXT REVIEW** | 2026-11-01 |

---

## Quick Reference

**When to Use This Skill:**
- Implementing tank volume calculations
- Building capacity warning systems
- Validating tank telemetry data
- Creating tank domain models
- Designing tank-related APIs

**Don't Use This For:**
- Frontend components (see fams-vue-core/SKILL.md)
- ATG protocol details (see fams-atg-communications/SKILL.md)
- API contracts (see FAMS_API_CORE-v2.md)

---

## 1. Scope & Pilot #1 Boundary

### Phase 5 Frozen Requirements

**Pilot #1 (Tank Communication & Health Card) includes:**
- ✅ Real-time volume calculations
- ✅ Capacity percentage tracking
- ✅ Status alert thresholds
- ✅ Communication health monitoring

**Pilot #1 Explicitly EXCLUDES:**
- ❌ Predictive run-out forecasting
- ❌ Machine learning models
- ❌ Historical trend analysis
- ❌ Advanced inventory projections

**Core Inputs:**
- Wet fuel depth (mm)
- Current temperature (°C)
- Tank physical dimensions
- Communication timestamp

---

## 2. Physical Volume Calculations for Horizontal Cylindrical Tanks

### 2.1 Geometric Segment Formula (Exact Mathematics)

**Problem:** For a horizontal cylinder, the relationship between wet depth and volume is **non-linear**. A simple linear calculation is inaccurate.

**Solution:** Use the circular segment formula with trigonometry.

### Mathematical Derivation

Given:
- $R$ = tank radius (meters)
- $h$ = wet depth height (meters, where $0 \le h \le 2R$)
- $L$ = tank length (meters)

**Step 1: Calculate Angle of Segment ($\theta$ in radians)**

The angle subtended by the liquid surface at the center:
$$\theta = 2 \cdot \arccos\left(\frac{R - h}{R}\right)$$

Where:
- If $h = 0$ (empty): $\theta = 0$
- If $h = R$ (half-full): $\theta = \pi$
- If $h = 2R$ (full): $\theta = 2\pi$

**Step 2: Calculate Segment Cross-Sectional Area ($A$ in m²)**

The area of the circular segment:
$$A = \frac{1}{2} R^2 (\theta - \sin\theta)$$

Where:
- $\sin\theta$ accounts for the triangular portion that needs subtraction
- Result is always in square meters

**Step 3: Calculate Total Wet Volume ($V_{raw}$ in m³)**

Multiply cross-sectional area by tank length:
$$V_{raw} = A \cdot L$$

**Step 4: Convert to Liters**

$$V_{liters} = V_{raw} \cdot 1000$$

### C# Implementation

```csharp
namespace FAMS.Core.Domain.Tanks.Calculations
{
    /// Mathematical calculations for horizontal cylindrical tanks
    public class HorizontalCylinderCalculator
    {
        /// Calculate wet volume of a horizontal cylinder given depth
        /// 
        /// Params:
        ///   radiusMeters: Cylinder radius (half of diameter)
        ///   lengthMeters: Cylinder length
        ///   depthMeters: Current wet depth (0 to 2*radius)
        ///   
        /// Returns: Volume in liters (decimal precision)
        public static decimal CalculateVolume(
            decimal radiusMeters,
            decimal lengthMeters,
            decimal depthMeters)
        {
            // Validation: depth must be between 0 and 2*radius
            if (depthMeters < 0 || depthMeters > 2 * radiusMeters)
                throw new ArgumentOutOfRangeException(
                    nameof(depthMeters),
                    "Depth must be between 0 and 2*radius");

            // Convert to double for Math functions (decimal doesn't have trig)
            double r = (double)radiusMeters;
            double h = (double)depthMeters;
            double l = (double)lengthMeters;

            // Step 1: Calculate theta (angle of segment)
            double theta = 2 * Math.Acos((r - h) / r);

            // Step 2: Calculate segment cross-sectional area
            double segmentArea = (r * r / 2) * (theta - Math.Sin(theta));

            // Step 3: Calculate total wet volume in cubic meters
            double volumeM3 = segmentArea * l;

            // Step 4: Convert to liters
            decimal volumeLiters = (decimal)(volumeM3 * 1000);

            return Math.Round(volumeLiters, 2); // Round to 2 decimals
        }

        /// Calculate percentage of tank capacity
        public static decimal CalculateCapacityPercentage(
            decimal currentVolumeLiters,
            decimal safeCapacityLiters)
        {
            if (safeCapacityLiters <= 0)
                throw new ArgumentException("Capacity must be positive");

            decimal percentage = (currentVolumeLiters / safeCapacityLiters) * 100;
            return Math.Min(Math.Max(percentage, 0), 100); // Clamp to 0-100%
        }
    }
}
```

### Example Calculation

**Scenario:** 20,000L horizontal tank (R=0.73m, L=12.15m)
- Current depth: 1.425m
- Safe capacity: 19,000L (95% of nominal)

```
θ = 2 * arccos((0.73 - 1.425) / 0.73)
  = 2 * arccos(-0.952)
  ≈ 2 * 2.837
  ≈ 5.674 radians

A = (0.73² / 2) * (5.674 - sin(5.674))
  = 0.267 * (5.674 - (-0.471))
  = 0.267 * 6.145
  ≈ 1.641 m²

V_raw = 1.641 * 12.15
      ≈ 19.94 m³

V_liters = 19.94 * 1000
         = 19,940 L

Cap% = (19,940 / 19,000) * 100
     ≈ 105.0%  ← WARNING: Over 95% safe fill!
```

---

## 2.2 Strapping Table Interpolation (Fallback Method)

**Use Case:** When geometric calculations are impractical (e.g., tilted tanks, physical deformities)

**Method:** Linear interpolation against physical tank calibration table

### Algorithm

Given two strapping points: $(h_1, V_1)$ and $(h_2, V_2)$ where $h_1 \le h_{current} \le h_2$:

$$V_{current} = V_1 + \frac{h_{current} - h_1}{h_2 - h_1} \cdot (V_2 - V_1)$$

### C# Implementation

```csharp
public class StrappingTableCalculator
{
    /// Strapping table entries: (depth_mm, volume_liters)
    private readonly List<(decimal DepthMm, decimal VolumeLiters)> _strapTable;

    public StrappingTableCalculator(List<(decimal, decimal)> strapTable)
    {
        // Validate: table must be sorted ascending by depth
        _strapTable = strapTable.OrderBy(x => x.DepthMm).ToList();
    }

    public decimal InterpolateVolume(decimal currentDepthMm)
    {
        // Boundary cases
        if (currentDepthMm <= _strapTable[0].DepthMm)
            return _strapTable[0].VolumeLiters;

        if (currentDepthMm >= _strapTable[^1].DepthMm)
            return _strapTable[^1].VolumeLiters;

        // Find surrounding strapping points
        var lower = _strapTable.Last(x => x.DepthMm <= currentDepthMm);
        var upper = _strapTable.First(x => x.DepthMm >= currentDepthMm);

        if (lower.DepthMm == upper.DepthMm)
            return lower.VolumeLiters; // Exact match

        // Linear interpolation
        decimal t = (currentDepthMm - lower.DepthMm) / 
                    (upper.DepthMm - lower.DepthMm);

        decimal volumeLiters = lower.VolumeLiters + 
                              t * (upper.VolumeLiters - lower.VolumeLiters);

        return Math.Round(volumeLiters, 2);
    }
}
```

---

## 3. Capacity Percentage Calculation

### Formula
$$\text{Capacity \%} = \frac{\text{Current Volume (Liters)}}{\text{Total Safe Fill Capacity (Liters)}} \times 100$$

### Safe Fill Limit Definition

**95% Rule (Default):**
- Nominal tank capacity: 20,000L
- Safe fill capacity: 20,000L × 0.95 = **19,000L**
- Unsafe zone (overfill prevention): 20,000L - 19,000L = 1,000L

**Local Overrides:**
- Some regions may require stricter (90%) or looser (97%) safe fill limits
- Must be configured per fuel site in the database
- Always validated during telemetry ingestion

### C# Domain Model

```csharp
namespace FAMS.Core.Domain.Tanks
{
    public class Tank
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public int TankNumber { get; set; }
        
        // Physical dimensions
        public decimal NominalCapacityLiters { get; set; }
        public decimal SafeFillPercentage { get; set; } = 0.95m; // 95% default
        
        // Calculated properties
        public decimal SafeFillCapacityLiters 
            => NominalCapacityLiters * SafeFillPercentage;
        
        public decimal CurrentVolumeLiters { get; set; }
        
        public decimal CapacityPercentage 
            => CurrentVolumeLiters / SafeFillCapacityLiters * 100;
        
        // Status derived from capacity %
        public TankStatus Status => CalculateStatus();
        
        private TankStatus CalculateStatus()
        {
            var pct = CapacityPercentage;
            
            if (pct >= 95.0m) return TankStatus.Critical;      // Overfill
            if (pct >= 85.0m) return TankStatus.Warning;       // High fill
            if (pct > 15.0m) return TankStatus.Healthy;        // Normal
            if (pct > 5.0m) return TankStatus.Warning;         // Low fill
            return TankStatus.Critical;                        // Run-out
        }
    }
    
    public enum TankStatus
    {
        Healthy,    // 15-85% capacity
        Warning,    // 5-15% or 85-95% capacity
        Critical,   // <5% or >=95% capacity
        Offline,    // No telemetry
        Unknown     // Uninitialized
    }
}
```

---

## 4. Threshold Alert & Trigger Rules

### Status Decision Matrix

| Capacity % | Status | UI Color | Action | Warning Message |
|-----------|--------|----------|--------|-----------------|
| ≥ 95.0% | `Critical` | 🔴 Red (Flashing) | Overfill Lockout Event | "CRITICAL: Tank overfill detected! Stop all deliveries immediately." |
| 85-95% | `Warning` | 🟠 Amber | High Fill Alert | "WARNING: Tank approaching capacity (85%+). Schedule delivery planning." |
| 15-85% | `Healthy` | 🟢 Emerald | Standard Operation | null |
| 5-15% | `Warning` | 🟠 Amber | Low Fill Run-out Alert | "WARNING: Tank approaching empty (5-15%). Schedule fuel delivery." |
| ≤ 5.0% | `Critical` | 🔴 Red | Critical Run-out Event | "CRITICAL: Tank nearly empty! Immediate fuel delivery required." |

### C# Threshold Configuration

```csharp
public static class TankThresholds
{
    // Capacity boundaries (in percentages)
    public const decimal CRITICAL_OVERFILL_THRESHOLD = 95.0m;
    public const decimal WARNING_HIGH_FILL_THRESHOLD = 85.0m;
    public const decimal WARNING_LOW_FILL_THRESHOLD = 15.0m;
    public const decimal CRITICAL_RUNOUT_THRESHOLD = 5.0m;
    
    public static TankAlertConfig GetAlertConfig(decimal capacityPercentage)
    {
        if (capacityPercentage >= CRITICAL_OVERFILL_THRESHOLD)
            return new TankAlertConfig
            {
                Status = TankStatus.Critical,
                Severity = AlertSeverity.Critical,
                UiColor = "red",
                UiFlashing = true,
                WarningMessage = "CRITICAL: Tank overfill detected! Stop all deliveries immediately.",
                ActionEvent = TankActionEvent.OverfillLockoutTriggered,
                DispatchTeam = "Team 10 (Maintenance)"
            };
        
        if (capacityPercentage >= WARNING_HIGH_FILL_THRESHOLD)
            return new TankAlertConfig
            {
                Status = TankStatus.Warning,
                Severity = AlertSeverity.Warning,
                UiColor = "amber",
                UiFlashing = false,
                WarningMessage = "WARNING: Tank approaching capacity (85%+). Schedule delivery planning.",
                ActionEvent = TankActionEvent.HighFillAlertIssued
            };
        
        if (capacityPercentage > WARNING_LOW_FILL_THRESHOLD)
            return new TankAlertConfig
            {
                Status = TankStatus.Healthy,
                Severity = AlertSeverity.Info,
                UiColor = "emerald",
                UiFlashing = false,
                WarningMessage = null
            };
        
        if (capacityPercentage > CRITICAL_RUNOUT_THRESHOLD)
            return new TankAlertConfig
            {
                Status = TankStatus.Warning,
                Severity = AlertSeverity.Warning,
                UiColor = "amber",
                UiFlashing = false,
                WarningMessage = "WARNING: Tank approaching empty (5-15%). Schedule fuel delivery.",
                ActionEvent = TankActionEvent.LowFillAlertIssued
            };
        
        return new TankAlertConfig
        {
            Status = TankStatus.Critical,
            Severity = AlertSeverity.Critical,
            UiColor = "red",
            UiFlashing = true,
            WarningMessage = "CRITICAL: Tank nearly empty! Immediate fuel delivery required.",
            ActionEvent = TankActionEvent.CriticalRunoutTriggered,
            DispatchTeam = "Team 10 (Maintenance)"
        };
    }
}
```

---

## 5. Telemetry & Communication Status Logic

### Offline Boundary Detection

**Rule:** If ATG telemetry is not received for more than **10 minutes**, mark the tank as `Offline`

```csharp
public class TelemetryStatusValidator
{
    private const int OFFLINE_THRESHOLD_MINUTES = 10;

    public CommunicationStatus GetCommunicationStatus(
        DateTime lastAtgUpdateUtc,
        DateTime nowUtc,
        bool isSimulated = false)
    {
        TimeSpan timeSinceUpdate = nowUtc - lastAtgUpdateUtc;

        if (timeSinceUpdate.TotalMinutes > OFFLINE_THRESHOLD_MINUTES)
        {
            return new CommunicationStatus
            {
                Status = "Offline",
                SimpleWarning = "ATG Telemetry Offline for >10 mins. " +
                    "Check local RS-232 link or cellular gateway state.",
                IsSimulated = isSimulated,
                LastUpdateUtc = lastAtgUpdateUtc,
                TimeSinceUpdateMs = (long)timeSinceUpdate.TotalMilliseconds,
                AlertLevel = AlertLevel.Critical,
                DispatchTeam = "Team 10 (Maintenance & Diagnostics)"
            };
        }

        return new CommunicationStatus
        {
            Status = "Healthy",
            SimpleWarning = null,
            IsSimulated = isSimulated,
            LastUpdateUtc = lastAtgUpdateUtc,
            TimeSinceUpdateMs = (long)timeSinceUpdate.TotalMilliseconds,
            AlertLevel = AlertLevel.Info
        };
    }
}
```

### Simulated Data Annotation

**Rule:** If `isSimulated = true`, all system logs and alerts must be marked "[EMULATED]" to prevent physical maintenance dispatch during testing

```csharp
public static string AnnotateIfSimulated(
    string message,
    bool isSimulated)
{
    if (isSimulated)
        return $"[EMULATED] {message}";
    return message;
}

// Usage:
var warningMessage = "Tank volume critically low";
var annotated = AnnotateIfSimulated(warningMessage, frame.IsSimulated);
// Result: "[EMULATED] Tank volume critically low"

// Logging
_logger.LogWarning(annotated); // Won't trigger real dispatch
```

### Domain Model Example

```csharp
public class TankTelemetrySnapshot
{
    // Identity
    public string TankId { get; set; }
    public string DeviceId { get; set; }
    
    // Physical measurements (from ATG)
    public decimal CurrentVolumeLiters { get; set; }
    public decimal FuelHeightMm { get; set; }
    public decimal WaterHeightMm { get; set; }
    public decimal TemperatureCelsius { get; set; }
    
    // Calculated
    public decimal CapacityPercentage { get; set; }
    public TankStatus Status { get; set; }
    
    // Communication health
    public string CommunicationStatus { get; set; } = "Healthy";
    public string SimpleWarning { get; set; }
    public DateTime LastUpdateUtc { get; set; }
    
    // Test flag
    public bool IsSimulated { get; set; } = false;
}
```

---

## 6. Validation Pipeline

### Pre-Persistence Checks

```csharp
public class TankDataValidator
{
    public ValidationResult Validate(TankTelemetrySnapshot snapshot)
    {
        var errors = new List<string>();

        // Physical constraints
        if (snapshot.CurrentVolumeLiters < 0)
            errors.Add("Volume cannot be negative");

        if (snapshot.CurrentVolumeLiters > snapshot.SafeCapacityLiters * 1.1m)
            errors.Add("Volume exceeds 110% of safe capacity (overfill danger)");

        if (snapshot.FuelHeightMm < 0 || snapshot.FuelHeightMm > 3000)
            errors.Add("Fuel height out of physical bounds (0-3000mm)");

        if (snapshot.WaterHeightMm < 0)
            errors.Add("Water height cannot be negative");

        if (snapshot.TemperatureCelsius < -40 || snapshot.TemperatureCelsius > 60)
            errors.Add("Temperature out of operational range (-40 to +60°C)");

        // Calculated consistency
        if (Math.Abs(snapshot.CapacityPercentage - 
            CalculateExpectedCapacity(snapshot)) > 5)
            errors.Add("Capacity percentage inconsistent with volume");

        return new ValidationResult
        {
            IsValid = errors.Count == 0,
            Errors = errors,
            Timestamp = DateTime.UtcNow
        };
    }

    private decimal CalculateExpectedCapacity(TankTelemetrySnapshot snapshot)
    {
        return (snapshot.CurrentVolumeLiters / snapshot.SafeCapacityLiters) * 100;
    }
}
```

---

## Summary

**This skill covers:**
- ✅ Horizontal cylinder volume calculations (geometric + strapping)
- ✅ Capacity percentage tracking (95% safe fill rule)
- ✅ Threshold alert thresholds (5 status levels)
- ✅ Communication health monitoring (10-minute offline boundary)
- ✅ Simulated data annotation ("[EMULATED]" flag)
- ✅ Validation pipeline & business rules

**Related Skills:**
- fams-atg-communications/SKILL.md (sensor data source)
- fams-vue-core/SKILL.md (UI representation)
- fams-portal-master skill Part 6 (API integration)

**Next Review:** 2026-11-01
