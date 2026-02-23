# X-Plane 12 State of the Platform (December 2024)

This document tracks X-Plane 12 features and SDK capabilities relevant to the StratusAIml project.

---

## Platform Versions

| Version | Status | Key Features |
|---------|--------|--------------|
| 12.1.3 | Released Nov 2024 | Major ATC overhaul |
| 12.1.4 | Released Jan 2025 | Web API v2, ATC fixes |
| 12.2.0 | Released Early 2025 | Graphics overhaul, wheel chocks |
| 12.2.1 | Released 2025 | Continual circuits (touch & go) |
| 12.3.0 | Current | Weather radar, WX/WXR API |

---

## 1. ATC System Improvements (12.1.x)

X-Plane 12.1.3 introduced a **major ATC overhaul** that significantly changes the competitive landscape:

### New ATC Features
- **Radio Checks**: Request radio checks from controllers
- **Clearance Requests**: IFR clearance delivery flow
- **SID/STAR Support**: ATC issues and follows SID/STAR procedures
- **VFR Flight Following**: Controller hand-overs, frequency corrections
- **Altimeter & Weather Updates**: Request current altimeter/weather
- **Emergency Procedures**: Transponder failures, position reports
- **Diversion Support**: Change destination during approach

### Impact on Our Project
⚠️ **Consideration**: X-Plane's built-in ATC is now much more capable. Stratus still offers:
- Natural language voice interaction
- AI copilot features
- Integration with real-world procedures
- Better voice quality and variety

But the "gap" between native ATC and Stratus is smaller on X-Plane 12.1+ than before.

---

## 2. Ground Services (12.2.x)

### Native Ground Handling
- **Shift+G**: Opens ground handling menu
- **Jetways**: Native animated jetways (WED 2.5+ airports)
- **Dual Jetways**: Supported since 12.1.2
- **Wheel Chocks**: New in 12.2.0 - alternative to parking brake

### New Commands
```
sim/ground_ops/jetway_01             # Toggle jetway 1
sim/ground_ops/jetway_02             # Toggle jetway 2
sim/ground_ops/chocks                # Toggle wheel chocks
sim/ground_ops/request_boarding      # Request boarding
sim/ground_ops/request_deboarding    # Request deboarding
```

### New DataRefs
```
sim/cockpit2/switches/chocks_on      # Wheel chocks deployed
sim/cockpit/engine/parking_brake     # Parking brake state
```

---

## 3. Web API (12.1.1+)

**Status**: Partially functional in X-Plane 12.3.3

### What Works (Tested December 2024)
```bash
# List all DataRefs (works!)
curl -s -H "Accept: application/json" "http://localhost:8086/api/v2/datarefs"
# Returns: 7500+ DataRefs with id, name, is_writable, value_type
```

### What Doesn't Work (In Our Testing)
- **Reading individual DataRef values** - 404 errors
- **WebSocket subscriptions** - ws://localhost:8086/api/v2/websocket returns 404
- **Value writing** - Not tested due to read issues

### Findings
The `/api` endpoint returns the DataRef **listing** but:
- Values are NOT included in the listing (only metadata)
- Individual DataRef reads return 404
- WebSocket endpoint appears non-functional

### Possible Causes
1. API may require enabling in X-Plane settings
2. Version 12.3.3 may have different endpoints than documented
3. May need specific authentication/headers

### Endpoints Tested
| Endpoint | Status |
|----------|--------|
| `GET /api/v2/datarefs` | ✅ Works (listing only) |
| `GET /api` | ✅ Works (same as above) |
| `GET /api/v2/datarefs/{id}` | ❌ 404 |
| `GET /api/v2/datarefs/{name}` | ❌ 404 |
| `WS /api/v2/websocket` | ❌ 404 |

### Impact on Our Project
⚠️ **The Web API cannot currently replace our native plugin** for reading values.

**Decision (December 2024)**: Continue with native C plugin approach:
- Reliable, proven method
- Works with all X-Plane 12.x versions  
- Our plugin is already functional and tested
- Web API investigation deferred for future evaluation

---

## 4. SDK Updates (XPLM 4.0+)

### Current SDK Version: 4.2.0 (for X-Plane 12.3.0+)

### Key Features
- **ARM64 Support**: Native Apple Silicon compilation
- **DataRef Notifications**: `XPLM_MSG_DATAREFS_ADDED` message when new DataRefs appear
- **Deprecation Warnings**: Some old DataRefs deprecated, check `DataRefs.txt`

### Our Plugin Compatibility
Our current plugin targets XPLM 3.0 which is fine for:
- X-Plane 11.50+
- X-Plane 12.x

To target XPLM 4.0+ features:
```c
#define XPLM400  // Enable 4.0 features
#define XPLM_WANTS_DATAREF_NOTIFICATIONS 1  // Get notified of new DataRefs
```

---

## 5. Upcoming Features (12.3.0 / 12.4.0)

### X-Plane 12.3.0 (Current)
- Weather Radar (WX/WXR)
- WX/WXR API for plugins
- G1000 Synthetic Vision
- A330 improvements

### X-Plane 12.4.0 (Beta)
- Enhanced ATC transmitter ranges
- Automatic check-in options
- Wind corrections for "fly heading" instructions

---

## 6. Third-Party Plugin Ecosystem

### Relevant Plugins for Integration

| Plugin | Purpose | Integration Priority |
|--------|---------|---------------------|
| Better Pushback | Pushback control | **P1** |
| OpenSAM | Jetways (legacy airports) | P1 |
| AviTab | In-sim tablet/EFB | P2 |
| World Traffic 3 | AI traffic | P3 |
| Pilot2ATC | Alternative ATC | Consider |

---

## 7. Recommendations for Our Project

### Immediate Actions

1. **Evaluate Web API Integration**
   - Test REST API for DataRef reading
   - Test WebSocket for real-time telemetry
   - Compare latency with file-based approach

2. **Update Plugin for 12.2+ Features**
   - Add wheel chocks command support
   - Add native jetway command support
   - Detect and use Web API if running 12.1.1+

3. **Document ATC Comparison**
   - Create comparison of X-Plane native ATC vs Stratus
   - Highlight Stratus value-add features

### Architecture Update

Consider dual-mode client:

```
┌─────────────────────────────────────────────────┐
│                 Python Client                    │
├─────────────────────────────────────────────────┤
│                 Adapter Layer                    │
│  ┌─────────────────┐  ┌─────────────────┐       │
│  │   File I/O      │  │   Web API       │       │
│  │  (stratus_telemetry JSON)  │  │ (REST/WebSocket)│       │
│  └─────────────────┘  └─────────────────┘       │
│         ↓                    ↓                   │
│  ┌─────────────────┐  ┌─────────────────┐       │
│  │  Native Plugin  │  │   X-Plane 12.1+ │       │
│  │      (C)        │  │   (Built-in)    │       │
│  └─────────────────┘  └─────────────────┘       │
└─────────────────────────────────────────────────┘
```

---

## 8. Resources

- [X-Plane 12 Release Notes](https://www.x-plane.com/kb/x-plane-12-release-notes/)
- [X-Plane SDK Documentation](https://developer.x-plane.com/sdk/)
- [X-Plane Web API Documentation](https://developer.x-plane.com/article/web-api/)
- [DataRefs.txt Reference](https://developer.x-plane.com/datarefs/)
