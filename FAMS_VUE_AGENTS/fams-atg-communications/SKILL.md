---
name: fams-atg-communications-specialized
description: Use when working on the IoT/edge layer — RS-232 serial config, TCP/IP socket connections, Veeder-Root VR-S90 protocol framing, checksum (XOR) validation, parsing raw telemetry frames, or the communication watchdog/offline-detection logic. Backend IoT/edge layer only — for what happens to parsed data afterward, load fams-tanks-business.
---

# FAMS ATG Communications — Specialized IoT/Edge Skill

## 📋 Metadata
| Field | Value |
|-------|-------|
| **VERSION** | 1.0.0 (Pilot #1 Seed) |
| **OWNER** | IoT/Edge Leader (Team 09) |
| **STATUS** | ✅ VALID |
| **VALIDATED** | 2026-09-01 |
| **DEPENDENCIES** | `/src/FAMS.IoT/`, `/src/FAMS.Gateway/`, Veeder-Root VR-S90 |
| **TESTED** | Claude 3.5 Sonnet (Challenger Verified) |
| **NEXT REVIEW** | 2026-11-01 |

---

## Quick Reference

**When to Use This Skill:**
- Writing ATG serial/Modbus parsers
- Integrating physical tank gauge telemetry
- Building IoT edge gateway logic
- Validating telemetry frame integrity
- Handling socket/serial communication

**Don't Use This For:**
- Frontend components (see fams-vue-core/SKILL.md)
- Business logic (see FAMS_TANKS_SPECIALIZED.md)
- API contracts (see FAMS_API_CORE-v2.md)

---

## 1. Physical & Network Transport Layer

### Hardware Connection Modes

**Option A: RS-232 Serial (Local Connections)**
```
┌─────────────────────┐
│  Fuel Site Console  │
│  (Veeder-Root ATG)  │
└──────────┬──────────┘
           │ RS-232 Serial
           │ 9600 8N1
           │
┌──────────▼──────────┐
│ Edge Gateway Device │
│  (Teltonika, etc.)  │
└─────────────────────┘
```

**Option B: TCP/IP Socket (Remote/Cellular)**
```
┌─────────────────────┐
│  Fuel Site Console  │
│  (Veeder-Root ATG)  │
└──────────┬──────────┘
           │ Ethernet / Cellular
           │ TCP Socket
           │
┌──────────▼──────────┐
│  Cloud Gateway      │
│  (TCP Listener)     │
└─────────────────────┘
```

### Serial Port Configuration (Locked Standard)

**9600 8N1 (9600 Baud, 8 Data Bits, No Parity, 1 Stop Bit)**

```csharp
// C# SerialPort Configuration
var serialPort = new SerialPort
{
    PortName = "/dev/ttyUSB0",        // Device path (Linux/Docker)
    BaudRate = 9600,                  // ✅ Locked standard
    DataBits = 8,                     // ✅ Locked standard
    StopBits = StopBits.One,          // ✅ Locked standard
    Parity = Parity.None,             // ✅ Locked standard
    Handshake = Handshake.None,       // ✅ No flow control
    ReadTimeout = 5000,               // Hard timeout: 5 seconds
    WriteTimeout = 5000
};

serialPort.Open();
```

### TCP/IP Socket Configuration

```csharp
// TCP Client with Auto-Retry & Connection Pool
public class TelemetrySocketClient
{
    private const int MAX_RETRIES = 3;
    private const int INITIAL_BACKOFF_MS = 2000;
    private const int SOCKET_READ_TIMEOUT_MS = 5000;

    public async Task<string> ConnectAndReadAsync(string hostname, int port)
    {
        int retryCount = 0;
        int backoffMs = INITIAL_BACKOFF_MS;

        while (retryCount < MAX_RETRIES)
        {
            try
            {
                using (var client = new TcpClient())
                {
                    client.ReceiveTimeout = SOCKET_READ_TIMEOUT_MS;
                    await client.ConnectAsync(hostname, port);

                    using (var stream = client.GetStream())
                    {
                        var buffer = new byte[1024];
                        int bytesRead = stream.Read(buffer, 0, buffer.Length);
                        return Encoding.ASCII.GetString(buffer, 0, bytesRead);
                    }
                }
            }
            catch (SocketTimeoutException ex)
            {
                Logger.LogWarning($"Socket timeout on attempt {retryCount + 1}");
                retryCount++;
                if (retryCount < MAX_RETRIES)
                    await Task.Delay(backoffMs);
                backoffMs *= 2; // Exponential backoff
            }
            catch (Exception ex)
            {
                Logger.LogError($"Connection failed: {ex.Message}");
                throw;
            }
        }

        throw new TimeoutException($"Failed to connect after {MAX_RETRIES} attempts");
    }
}
```

---

## 2. Veeder-Root S90 Protocol Standard (VR-S90)

### Frame Structure

**ASCII Control Characters:**
- `<SOH>` = `0x01` (Start of Header, Ctrl-A)
- `<ETX>` = `0x03` (End of Text, Ctrl-C)
- `<CHECKSUM>` = 4-digit hex XOR of payload

### Command Set for Pilot #1

#### 2.1 In-Tank Inventory Command (`i20100`)

**Request Frame:**
```
<SOH>i20100<ETX>{CHECKSUM}
```

**Example (Hex):**
```
01 69 32 30 31 30 30 03 [CHECKSUM]
```

**Response Frame:**
```
<SOH>I20100
YY-MM-DD HH:MM:SS
TANK  PRODUCT               VOLUME    HEIGHT    WATER     TEMP      CAPACITY
  1   Diesel                14250.5   1425.20   0.0       22.5      20000.0
  2   Gasoline              18750.2   1875.10   0.5       21.8      20000.0
<ETX>{CHECKSUM}
```

### 2.2 Checksum Calculation

**Algorithm: XOR Sum (Bitwise)**

```csharp
/// Calculate Veeder-Root 4-digit hex checksum
/// XOR of all bytes from after <SOH> up to and including <ETX>
public static string CalculateChecksum(byte[] payload)
{
    byte xorSum = 0;
    
    // XOR all bytes in payload (including <ETX>)
    foreach (byte b in payload)
        xorSum ^= b;
    
    // Convert to 4-digit hex uppercase
    return xorSum.ToString("X4");
}

// Example Usage:
byte[] payload = Encoding.ASCII.GetBytes("I20100\r\n...<ETX>");
string checksum = CalculateChecksum(payload);  // E.g., "1A2B"
```

### 2.3 Response Format (Fixed-Width Columns)

**Header Line:**
```
TANK  PRODUCT               VOLUME    HEIGHT    WATER     TEMP      CAPACITY
```

**Column Positions (Fixed-Width String Parsing):**
| Field | Start Pos | Width | Type | Unit |
|-------|-----------|-------|------|------|
| TANK | 0 | 5 | int | tank number |
| PRODUCT | 6 | 20 | string | fuel type |
| VOLUME | 27 | 10 | decimal | Liters |
| HEIGHT | 38 | 10 | decimal | Millimeters |
| WATER | 49 | 10 | decimal | Millimeters |
| TEMP | 60 | 10 | decimal | Celsius |
| CAPACITY | 71 | 10 | decimal | Liters |

---

## 3. Parsing Logic & Type Checking

### C# Domain Model

```csharp
namespace FAMS.IoT.Core.Models
{
    /// Strongly-typed telemetry frame from Veeder-Root ATG
    public class AtgInventoryFrame
    {
        /// Unique device identifier for audit trails
        public string DeviceId { get; set; } = string.Empty;

        /// Tank number (1-8 typical)
        public int TankNumber { get; set; }

        /// Product name (Diesel, Gasoline, etc.)
        public string ProductName { get; set; } = string.Empty;

        /// Current fuel volume in liters (decimal precision)
        public decimal VolumeLiters { get; set; }

        /// Wet depth height in millimeters
        public decimal FuelHeightMm { get; set; }

        /// Water content height in millimeters
        public decimal WaterHeightMm { get; set; }

        /// Fuel temperature in Celsius
        public decimal TemperatureCelsius { get; set; }

        /// Total safe fill capacity in liters (typically 95% of tank)
        public decimal CapacityLiters { get; set; }

        /// UTC timestamp from ATG device
        public DateTime TimestampUtc { get; set; }

        /// Validation flag: is this frame data valid?
        public bool IsValid { get; set; }

        /// Communication latency in milliseconds
        public int ReadLatencyMs { get; set; }
    }
}
```

### Parsing Pipeline (Step-by-Step)

```csharp
public class AtgFrameParser
{
    /// Parse raw serial buffer into strongly-typed telemetry
    public AtgInventoryFrame ParseInventoryResponse(
        string rawBuffer, 
        string deviceId)
    {
        var frame = new AtgInventoryFrame { DeviceId = deviceId };

        try
        {
            // STEP 1: Framing Check
            if (!rawBuffer.Contains("\x01") || !rawBuffer.Contains("\x03"))
                throw new TelemetryFrameCorruptedException("Missing SOH/ETX delimiters");

            // STEP 2: Checksum Verification
            int sohIdx = rawBuffer.IndexOf('\x01');
            int etxIdx = rawBuffer.IndexOf('\x03');

            if (etxIdx < sohIdx)
                throw new TelemetryFrameCorruptedException("Invalid frame order");

            string payloadWithETX = rawBuffer.Substring(sohIdx + 1, etxIdx - sohIdx);
            string checksumString = rawBuffer.Substring(etxIdx + 1, 4);

            byte[] payloadBytes = Encoding.ASCII.GetBytes(payloadWithETX);
            byte calculatedChecksum = payloadBytes.Aggregate((byte)0, (acc, b) => (byte)(acc ^ b));

            if (calculatedChecksum.ToString("X4") != checksumString.ToUpper())
                throw new ChecksumMismatchException(
                    $"Expected {checksumString}, got {calculatedChecksum:X4}");

            // STEP 3: Tokenization (Split by newline)
            string[] lines = payloadWithETX.Split(new[] { '\n', '\r' }, 
                StringSplitOptions.RemoveEmptyEntries);

            if (lines.Length < 3)
                throw new TelemetryFrameCorruptedException("Insufficient response lines");

            // Extract timestamp (line 1)
            string timestampLine = lines[1];
            if (DateTime.TryParseExact(
                timestampLine, 
                "yy-MM-dd HH:mm:ss", 
                CultureInfo.InvariantCulture, 
                DateTimeStyles.AssumeUniversal,
                out var timestamp))
            {
                frame.TimestampUtc = timestamp;
            }

            // STEP 4: Parse tank data (line 2 onwards, fixed-width columns)
            for (int i = 2; i < lines.Length; i++)
            {
                string line = lines[i];
                if (line.Length < 80) continue; // Skip incomplete lines

                // Extract fixed-width columns
                frame.TankNumber = int.Parse(line.Substring(0, 5).Trim());
                frame.ProductName = line.Substring(6, 20).Trim();
                frame.VolumeLiters = decimal.Parse(line.Substring(27, 10).Trim());
                frame.FuelHeightMm = decimal.Parse(line.Substring(38, 10).Trim());
                frame.WaterHeightMm = decimal.Parse(line.Substring(49, 10).Trim());
                frame.TemperatureCelsius = decimal.Parse(line.Substring(60, 10).Trim());
                frame.CapacityLiters = decimal.Parse(line.Substring(71, 10).Trim());

                // Validation checks
                if (frame.VolumeLiters < 0 || frame.FuelHeightMm < 0)
                    throw new InvalidTelemetryException("Negative physical measurements detected");

                frame.IsValid = true;
            }

            return frame;
        }
        catch (Exception ex)
        {
            Logger.LogError($"Frame parsing failed: {ex.Message}");
            frame.IsValid = false;
            throw;
        }
    }
}
```

---

## 4. Telemetry Fault Shielding & Logging

### Invalid Frame Handling

```csharp
public class TelemetryValidator
{
    private readonly ILogger<TelemetryValidator> _logger;
    private readonly IMetricsCollector _metrics;

    public bool ValidateAndPersist(AtgInventoryFrame frame)
    {
        try
        {
            // Validation rules
            if (!frame.IsValid)
            {
                LogValidationFailure(frame, "Frame marked invalid by parser");
                return false;
            }

            if (frame.VolumeLiters > frame.CapacityLiters)
            {
                LogValidationFailure(frame, "Volume exceeds capacity");
                return false;
            }

            if (frame.FuelHeightMm > 3000) // Physical impossibility
            {
                LogValidationFailure(frame, "Height measurement out of bounds");
                return false;
            }

            // All checks passed
            return true;
        }
        catch (Exception ex)
        {
            LogValidationFailure(frame, ex.Message);
            return false;
        }
    }

    private void LogValidationFailure(AtgInventoryFrame frame, string reason)
    {
        // Structured logging with Serilog
        _logger.LogCritical(
            "TelemetryParseFailure | DeviceId={DeviceId} | Tank={Tank} | " +
            "RawFrame={RawFrame} | Reason={Reason}",
            frame.DeviceId,
            frame.TankNumber,
            SerializeFrame(frame),
            reason
        );

        // Increment failure counter
        _metrics.IncrementCounter("TelemetryParseFailure", new[] {
            new KeyValuePair<string, object>("deviceId", frame.DeviceId),
            new KeyValuePair<string, object>("tankNumber", frame.TankNumber)
        });

        // DO NOT persist invalid frame to database
        // DO NOT emit to API response
    }
}
```

### Communication Watchdog (Offline Detection)

```csharp
public class CommunicationWatchdog
{
    private const int OFFLINE_THRESHOLD_MINUTES = 10;
    private Dictionary<string, DateTime> _lastHeartbeat = new();

    public void RecordHeartbeat(string deviceId)
    {
        _lastHeartbeat[deviceId] = DateTime.UtcNow;
    }

    public CommunicationStatus CheckStatus(string deviceId)
    {
        if (!_lastHeartbeat.TryGetValue(deviceId, out var lastUpdate))
            return CommunicationStatus.Unknown;

        var timeSinceUpdate = DateTime.UtcNow - lastUpdate;

        if (timeSinceUpdate.TotalMinutes > OFFLINE_THRESHOLD_MINUTES)
        {
            return new CommunicationStatus
            {
                Status = "Offline",
                SimpleWarning = "ATG Telemetry Offline for >10 mins. " +
                    "Check local RS-232 link or cellular gateway state.",
                AlertLevel = AlertLevel.Critical,
                LastUpdateUtc = lastUpdate,
                DispatchToTeam = "Team 10 (Maintenance & Diagnostics)"
            };
        }

        return new CommunicationStatus
        {
            Status = "Healthy",
            SimpleWarning = null,
            AlertLevel = AlertLevel.Info,
            LastUpdateUtc = lastUpdate
        };
    }
}
```

### Error Sanitization (Wrapping Raw Exceptions)

```csharp
/// Custom domain error wrapping raw socket/serial exceptions
public class TelemetryException : Exception
{
    public string ErrorCode { get; set; }
    public string UserMessage { get; set; }

    public TelemetryException(string errorCode, string message)
        : base(message)
    {
        ErrorCode = errorCode;
        UserMessage = SanitizeMessage(message);
    }

    private static string SanitizeMessage(string rawMessage)
    {
        // Never expose raw socket/serial errors to API
        return rawMessage switch
        {
            string msg when msg.Contains("SocketTimeoutException") 
                => "ATG_COMMUNICATION_TIMEOUT",
            string msg when msg.Contains("SerialPortException") 
                => "ATG_SERIAL_ERROR",
            string msg when msg.Contains("ConnectionRefused") 
                => "ATG_CONNECTION_REFUSED",
            _ => "ATG_UNKNOWN_ERROR"
        };
    }
}
```

---

## 5. Automated Edge Validation Pipeline

### Pre-Merge Checklist

```bash
# 1. Hardware Emulation Verification (100 frames)
/src/FAMS.IoT/test/emulator.sh --frames=100 --latency-ms=200

# 2. Telemetry Contract Tests
dotnet test --filter Category=Telemetry --verbose

# 3. Checksum Unit Tests (5 scenarios with corrupted bits)
dotnet test --filter Category=ChecksumValidation

# 4. Load Test (High throughput)
dotnet test --filter Category=LoadTest --timeout=60000

# 5. Integration Test (E2E serial → database)
dotnet test --filter Category=Integration
```

### Test Scenarios

```csharp
[TestFixture]
public class ChecksumValidationTests
{
    [Test]
    public void CalculateChecksum_ValidPayload_ReturnsCorrectHex()
    {
        var payload = Encoding.ASCII.GetBytes("I20100\r\n...");
        var checksum = AtgFrameParser.CalculateChecksum(payload);
        Assert.That(checksum, Is.EqualTo("1A2B")); // Example
    }

    [Test]
    public void ValidateChecksum_OneFlipBit_ThrowsException()
    {
        var frame = "...checksum is 1A2B...";
        var corrupted = frame.Replace("1A2B", "1A3B"); // 1-bit flip
        
        Assert.Throws<ChecksumMismatchException>(() =>
            AtgFrameParser.ParseInventoryResponse(corrupted, "device1")
        );
    }

    [Test]
    public void ParseInventoryResponse_MissingETX_ThrowsException()
    {
        var incomplete = "<SOH>I20100\r\n..."; // Missing <ETX>
        Assert.Throws<TelemetryFrameCorruptedException>(() =>
            AtgFrameParser.ParseInventoryResponse(incomplete, "device1")
        );
    }
}
```

---

## Summary

**This skill covers:**
- ✅ RS-232 serial & TCP/IP socket configuration
- ✅ Veeder-Root VR-S90 protocol (framing, checksums, commands)
- ✅ Frame parsing with type checking
- ✅ Error handling & fault shielding
- ✅ Communication watchdog & offline detection
- ✅ Validation pipeline & test strategies

**Related Skills:**
- FAMS_TANKS_SPECIALIZED.md (business logic for parsed data)
- FAMS_API_CORE-v2.md (API contracts for telemetry)
- fams-portal-master skill Part 6 (API integration patterns)

**Next Review:** 2026-11-01
