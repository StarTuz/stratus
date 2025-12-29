# X-Plane Extensions & Integrations

This document tracks potential extensions and integrations that could bring MSFS-level features to X-Plane users of Stratus.AI.

## Overview

The official Stratus client has reduced functionality on X-Plane compared to MSFS. This is due to platform differences, not intentional limitations. This document explores how community plugins and custom development could bridge these gaps.

---

## 1. AI Traffic Integration

### The Gap
Stratus on MSFS can inject AI traffic that appears in the sim and interacts with ATC. On X-Plane, this is not supported.

### Potential Solutions

#### 1.1 World Traffic 3 Integration
**Plugin**: [World Traffic 3](https://www.yourcontrols.aero/worldtraffic)

World Traffic 3 is the most popular AI traffic solution for X-Plane.

**Integration Approach**:
- WT3 uses flight plan files to spawn traffic
- We could write flight plans to WT3's folder based on Stratus traffic data
- WT3 exposes DataRefs for traffic positions

**DataRefs**:
```
wt3/traffic/count                    # Number of AI aircraft
wt3/traffic/*/icao                   # Aircraft ICAO type
wt3/traffic/*/lat, lon, alt          # Position
wt3/traffic/*/callsign               # Callsign
```

**Feasibility**: Medium - Requires reverse engineering WT3's file format

#### 1.2 X-Plane Native AI
X-Plane has built-in AI capability via multiplayer slots.

**DataRefs**:
```
sim/multiplayer/position/plane1_x    # Position (OpenGL coords)
sim/multiplayer/position/plane1_y
sim/multiplayer/position/plane1_z
sim/multiplayer/position/plane1_psi  # Heading
sim/multiplayer/position/plane1_the  # Pitch
sim/multiplayer/position/plane1_phi  # Roll
```

**Feasibility**: High - We can write to these DataRefs to position AI aircraft

**Limitations**: 
- Limited to 19 AI aircraft
- No ground movement/taxi logic
- No AI decision making

#### 1.3 Custom Traffic Plugin
Build a dedicated traffic plugin that:
1. Receives traffic data from Stratus (via the SimAPI JSON)
2. Spawns OBJ models at correct positions
3. Animates movement along defined paths

**Feasibility**: High complexity, but complete control

---

## 2. Ground Services Integration

### The Gap
Stratus on MSFS can trigger ground services (pushback, fuel, catering). On X-Plane, no native ground services exist.

### Potential Solutions

#### 2.1 Better Pushback Integration
**Plugin**: [Better Pushback](https://github.com/skiselkov/BetterPushback)

Better Pushback is the de-facto standard for X-Plane pushback.

**DataRefs** (exposed by Better Pushback):
```
bp/started                           # Pushback in progress (int, read)
bp/can_pushback                      # Can we start? (int, read)
bp/slave_mode                        # Slave mode enabled (int, write)
```

**Commands**:
```
BetterPushback/start                 # Start pushback
BetterPushback/stop                  # Stop pushback
BetterPushback/connect               # Connect tug
BetterPushback/disconnect            # Disconnect tug
```

**Integration Approach**:
When Stratus issues a "pushback approved" command:
1. Check `bp/can_pushback`
2. If available, execute `BetterPushback/start` command
3. Monitor `bp/started` for completion

**Feasibility**: High - Well-documented API

#### 2.2 X-Plane 12 Native Jetways
**Built-in since X-Plane 12.0**

X-Plane 12 includes native animated jetway support at default airports created with WED 2.5+.

**User Interaction**:
- Press **Shift+G** to open Ground Handling window
- Select "Toggle jetway attachment" to connect/disconnect
- Also available via Flight menu → Ground Operations

**Commands**:
```
sim/ground_ops/jetway_01            # Toggle jetway 1
sim/ground_ops/jetway_02            # Toggle jetway 2 (for dual jetways, XP 12.1.2+)
```

**Limitations**:
- Only works at airports built with X-Plane 12's WED 2.5+ tooling
- Many payware/third-party sceneries still use OpenSAM or static jetways
- Aircraft must be properly aligned at the gate

**Integration Approach**:
1. Try native command `sim/ground_ops/jetway_01` first
2. If no native jetway, fall back to OpenSAM if available
3. Provide user feedback on which system is active

**Feasibility**: High - Native support, no plugin required

#### 2.3 OpenSAM Integration (Fallback)
**Plugin**: [OpenSAM](https://forums.x-plane.org/index.php?/files/file/82166-opensam/)

OpenSAM handles jetways, docking guidance, and ground equipment at compatible airports. Required for airports not using X-Plane 12's native jetway system.

**DataRefs**:
```
opensam/jetway/status               # Jetway state (0=idle, 1=moving, 2=docked)
opensam/dgs/available               # Docking guidance available
opensam/dgs/status                  # DGS state
opensam/jw/door1_x                  # Door position for jetway targeting
```

**Commands**:
```
opensam/jw/toggle                   # Toggle jetway
opensam/dgs/toggle                  # Toggle docking guidance
```

**Integration Approach**:
When at a gate with OpenSAM support:
1. Query `opensam/dgs/available`
2. If available and Stratus assigns gate, enable DGS
3. After parking, trigger `opensam/jw/toggle` to connect jetway

**Feasibility**: High - Active development, good documentation

---

## 3. Follow-Me Car

### The Gap
MSFS can display a follow-me car that guides the aircraft from runway to gate. X-Plane has no equivalent.

### Potential Solutions

#### 3.1 Custom Follow-Me Plugin
Build a plugin that:
1. Loads a ground vehicle OBJ model
2. Receives taxi route from Stratus (part of gate assignment data)
3. Animates the vehicle along the route
4. Player follows visually

**Required Components**:
- Vehicle OBJ model (can use existing library objects)
- Taxi route parser (routes come from airport navigation data)
- Animation system (position interpolation)

**DataRefs to Create**:
```
siai/followme/active                 # Follow-me mode enabled
siai/followme/lat, lon               # Current vehicle position
siai/followme/heading                # Vehicle heading
siai/followme/speed                  # Vehicle speed
```

**Feasibility**: Medium - Requires taxi graph navigation logic

#### 3.2 GroundTraffic Plugin Integration
Some sceneries include GroundTraffic plugin for animated ground vehicles.

**Limitation**: GroundTraffic follows predefined routes, not dynamic ones.

---

## 4. EFB (Electronic Flight Bag)

### The Gap
MSFS has an in-sim EFB panel. X-Plane does not.

### Potential Solutions

#### 4.1 AviTab Integration
**Plugin**: [AviTab](https://github.com/fpw/avitab)

AviTab provides an in-sim tablet with web browser capability.

**Integration Approach**:
1. Stratus could expose a web-based EFB at a local URL
2. User opens this URL in AviTab's browser
3. Full EFB functionality available

**Implementation**:
Our client could host a local web server (e.g., Flask):
```python
from flask import Flask
app = Flask(__name__)

@app.route('/efb')
def efb():
    return render_template('efb.html', 
                           flight_data=get_current_flight(),
                           clearances=get_clearances())
```

**Feasibility**: High - AviTab browser works well

#### 4.2 Standalone Window
Create a PySide6 window that overlays the sim:
- Always-on-top
- Semi-transparent optional
- Drag to position

**Feasibility**: High - Part of native client development

---

## 5. Implementation Priority

| Extension | Complexity | User Value | Priority |
|-----------|------------|------------|----------|
| X-Plane 12 Native Jetways | Very Low | High | **P0** |
| Better Pushback Integration | Low | High | **P1** |
| OpenSAM Jetway Integration (Fallback) | Low | Medium | **P1** |
| AviTab Web EFB | Medium | High | **P2** |
| Follow-Me Car | High | Medium | **P3** |
| AI Traffic (Native) | Medium | Medium | **P3** |
| World Traffic 3 Integration | High | Medium | **P4** |

---

## 6. DataRef Reference

### Stratus Custom DataRefs (Proposed)

Our plugin could expose these DataRefs for other plugins to read:

```
# Connection Status
siai/connected                       # Connected to Stratus server
siai/mode                            # Current mode (0=off, 1=ATC, 2=copilot)

# Current Clearance
siai/clearance/type                  # Type (0=none, 1=taxi, 2=takeoff, etc.)
siai/clearance/runway                # Assigned runway (string)
siai/clearance/altitude              # Cleared altitude
siai/clearance/squawk                # Assigned squawk code

# Gate/Parking
siai/gate/assigned                   # Assigned gate name (string)
siai/gate/lat, lon                   # Gate position

# Frequencies
siai/freq/active                     # Currently tuned ATC frequency
siai/freq/next                       # Next frequency to tune
```

---

## 7. Development Notes

### Testing Without API Key
Most extension work can proceed without a Stratus API key by:
1. Mocking the SimAPI input/output files
2. Using test flight scenarios
3. Validating plugin integrations independently

### Plugin Detection
To detect if Better Pushback or OpenSAM are installed:
```c
XPLMDataRef bp_check = XPLMFindDataRef("bp/started");
if (bp_check != NULL) {
    // Better Pushback is installed
}

XPLMDataRef sam_check = XPLMFindDataRef("opensam/jetway/status");
if (sam_check != NULL) {
    // OpenSAM is installed
}
```

---

## 8. Resources

- [X-Plane DataRef Documentation](https://developer.x-plane.com/datarefs/)
- [X-Plane Command Documentation](https://developer.x-plane.com/commands/)
- [Better Pushback GitHub](https://github.com/skiselkov/BetterPushback)
- [OpenSAM Documentation](https://stairport.github.io/openSAM-docs/)
- [AviTab GitHub](https://github.com/fpw/avitab)
- [World Traffic 3](https://www.yourcontrols.aero/worldtraffic)
