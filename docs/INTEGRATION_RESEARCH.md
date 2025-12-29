# Stratus.AI Integration Research

**Date**: December 27, 2024  
**Purpose**: Understanding how Stratus.AI works with flight simulators

---

## 🎯 Key Question

> "Shouldn't there be a plugin for X-Plane which shows the settings in game?"

**Answer**: Yes, there should be! The official Windows client has in-sim components. Let's understand what they provide and what we need to replicate.

---

## Official Stratus Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    SAYINTENTIONS.AI ARCHITECTURE                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌────────────────┐  │
│  │   FLIGHT SIMULATOR  │    │   SI DESKTOP CLIENT │    │  SI CLOUD      │  │
│  │   (X-Plane / MSFS)  │◀──▶│   (Windows App)     │◀──▶│  (AI Backend)  │  │
│  └─────────────────────┘    └─────────────────────┘    └────────────────┘  │
│           │                          │                                      │
│           ▼                          ▼                                      │
│  ┌─────────────────────┐    ┌─────────────────────┐                        │
│  │   IN-SIM PLUGINS    │    │   VOICE CAPTURE     │                        │
│  │   - VR Toolbar      │    │   - PTT + STT       │                        │
│  │   - Taxi arrows     │    │   - Speaker output  │                        │
│  │   - EFB (MSFS)      │    └─────────────────────┘                        │
│  └─────────────────────┘                                                    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Windows Client Features

### Desktop Application (External Window)
| Feature | Description |
|---------|-------------|
| **Comms History** | Shows ATC/pilot message transcripts |
| **Frequency Display** | Shows tuned COM1/COM2/NAV frequencies + transponder |
| **Connection Status** | Shows simulator connection status |
| **Flight Plan** | SimBrief integration |
| **Voice Capture** | PTT button + speech recognition |
| **Settings** | API key, voice settings, hotkeys |

### MSFS In-Sim Plugins (Community Folder)
| Plugin | Description |
|--------|-------------|
| `stratus-efb` | Electronic Flight Bag panel inside MSFS |
| `Stratus-VR-Toolbar-Plugin` | VR-specific toolbar integration |
| `Stratus-SimObjects-Optional` | AI aircraft models |
| `stratus-fly-in-library` | Scenery objects |

### X-Plane In-Sim Features
| Feature | Description |
|---------|-------------|
| **VR Add-On** | Downloadable plugin for VR toolbar |
| **Taxi Arrows** | On-ground taxi guidance arrows |
| **ComLink** | View history + tune frequencies from any device (web/VR) |

---

## What We Currently Have (StratusML)

### ✅ Implemented
| Component | Location | Status |
|-----------|----------|--------|
| Desktop GUI Client | `client/src/ui/` | ✅ Working |
| SAPI Communication | `client/src/core/sapi_interface.py` | ✅ Working |
| Audio Playback | `client/src/audio/` | ✅ Working |
| X-Plane Telemetry Plugin | `adapters/xplane/PI_Stratus.py` | ⚠️ Basic |

### ❌ Missing for Parity
| Feature | Priority | Notes |
|---------|----------|-------|
| **In-sim frequency tuning** | High | Read/write COM1/COM2 from X-Plane |
| **In-sim transponder** | High | Read/write transponder code |
| **In-sim overlay/panel** | Medium | X-Plane widget showing comms/status |
| **VR toolbar** | Medium | For VR users |
| **Taxi arrows** | Low | Scenery injection |
| **SimBrief integration** | Low | Flight plan import |

---

## X-Plane Integration Architecture

### Current State
```
┌───────────────────────────────────────────────────────────────┐
│  X-Plane 12                                                   │
│  ┌─────────────────┐                                          │
│  │ PI_Stratus│──▶ Writes telemetry to JSON file         │
│  │ (Python Plugin) │                                          │
│  └─────────────────┘                                          │
│           │                                                   │
│           ▼                                                   │
│   ~/.local/share/StratusAI/simAPI_input.json            │
│           │                                                   │
└───────────────────────────────────────────────────────────────┘
           │
           ▼
┌───────────────────────────────────────────────────────────────┐
│  StratusML Client (reads JSON)                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  main.py ──▶ GUI (PySide6)                                │ │
│  │     │                                                     │ │
│  │     ▼                                                     │ │
│  │  sapi_interface.py ──▶ SAPI Cloud                         │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Proposed Enhancement
```
┌───────────────────────────────────────────────────────────────┐
│  X-Plane 12                                                   │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  Enhanced PI_Stratus (Python Plugin)             │    │
│  │  ┌───────────────┐  ┌────────────────┐  ┌───────────┐ │    │
│  │  │ Telemetry OUT │  │ Frequency SYNC │  │ In-Sim UI │ │    │
│  │  │ (position etc)│  │ (COM1/2, XPDR) │  │ (Overlay) │ │    │
│  │  └───────────────┘  └────────────────┘  └───────────┘ │    │
│  └───────────────────────────────────────────────────────┘    │
│           │                    ▲                    │         │
│           ▼                    │                    ▼         │
│   JSON telemetry         JSON commands         X-Plane Widget │
│   (out to client)        (in from client)      (comms display)│
└───────────────────────────────────────────────────────────────┘
```

---

## Key DataRefs for Full Integration

### Already Implemented
| DataRef | Purpose |
|---------|---------|
| `sim/flightmodel/position/latitude` | Position |
| `sim/flightmodel/position/longitude` | Position |
| `sim/flightmodel/position/elevation` | Altitude MSL |
| `sim/flightmodel/position/mag_psi` | Magnetic heading |
| `sim/flightmodel/position/true_airspeed` | TAS |
| `sim/flightmodel/failures/onground_all` | On ground flag |

### Needed for Frequency Sync
| DataRef | Purpose | Read/Write |
|---------|---------|------------|
| `sim/cockpit2/radios/actuators/com1_frequency_hz_833` | COM1 active | R/W |
| `sim/cockpit2/radios/actuators/com1_standby_frequency_hz_833` | COM1 standby | R/W |
| `sim/cockpit2/radios/actuators/com2_frequency_hz_833` | COM2 active | R/W |
| `sim/cockpit2/radios/actuators/com2_standby_frequency_hz_833` | COM2 standby | R/W |
| `sim/cockpit/radios/transponder_code` | Transponder squawk | R/W |
| `sim/cockpit2/autopilot/altitude_dial_ft` | Altitude selection | R |

### For Aircraft Identification
| DataRef | Purpose |
|---------|---------|
| `sim/aircraft/view/acf_tailnum` | Tail number (callsign) |
| `sim/aircraft/view/acf_ICAO` | Aircraft ICAO type |

---

## Next Steps for X-Plane Integration

### Phase 1: Bidirectional Sync (Priority: HIGH)
1. **Enhance the plugin to read COM frequencies** and include in telemetry JSON
2. **Add a command JSON file** for the client to write frequency changes
3. **Plugin watches for commands** and sets DataRefs

### Phase 2: In-Sim Overlay (Priority: MEDIUM)
1. **Create X-Plane widget** showing:
   - Connection status (green/red indicator)
   - Current comms history (last 3 messages)
   - Active frequency display
2. **Position in corner** of screen, semi-transparent

### Phase 3: VR Support (Priority: LOW)
1. **X-Plane VR toolbar integration**
2. **Large, readable fonts** for in-headset viewing

---

## MSFS Considerations

For MSFS (future work):
- Uses **SimConnect API** instead of DataRefs
- Requires a **WASM gauge module** for in-sim panel
- Or use the **Community Folder** approach like official client
- Lower priority until X-Plane is fully working

---

## Comparison: Official vs StratusML

| Feature | Official (Windows) | StratusML | Gap |
|---------|-------------------|-----------------|-----|
| Desktop client | ✅ | ✅ | None |
| Audio playback | ✅ | ✅ | None |
| Voice input | ✅ (STT) | ❌ (text only) | Phase 3 |
| Frequency display | ✅ | ⚠️ (static) | Need sync |
| Frequency tuning | ✅ | ❌ | High priority |
| In-sim overlay | ✅ | ❌ | Medium priority |
| VR toolbar | ✅ | ❌ | Low priority |
| Taxi arrows | ✅ | ❌ | Low priority |
| MSFS support | ✅ | ❌ | Future |

---

## Recommendation

**Immediate priority**: Enhance the X-Plane plugin to:
1. ✅ Export frequency data (COM1/2, transponder) in telemetry JSON
2. ✅ Import frequency commands from client
3. ✅ Sync in real-time (every 0.5 seconds)

This will make our client **first-class** - the GUI will show actual cockpit frequencies and allow tuning them, just like the official client.

**After that**: Consider a simple in-sim overlay widget for X-Plane.
