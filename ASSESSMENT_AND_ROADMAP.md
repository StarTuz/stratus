# Stratus Client - Linux & Mac Port Assessment and Roadmap

## Executive Summary
Building a native Linux and Mac client for Stratus AI is **highly feasible**. The architecture of Stratus relies on a decoupled "SimAPI" (file-based JSON exchange) which allows the core client logic to be platform-agnostic, provided it can access the filesystem and audio devices.

The primary development effort will focus on two areas:
1.  **The Native Client Application**: A cross-platform (Linux/macOS) application to handle User Interface, Audio I/O, API communication (SAPI), and File I/O (SimAPI).
2.  **The Simulator Adapters**:
    *   **X-Plane**: A native plugin (Linux/macOS) to bridge X-Plane DataRefs to the SimAPI JSON format.
    *   **MSFS (Linux Only)**: A strategy to bridge the Windows-only MSFS (running via Proton) to the native Linux client.

---

## 1. Technical Architecture & Requirements

### 1.1 Core Components
The system consists of three distinct parts:
1.  **The Cloud Brain (SAPI)**: The remote Stratus server (`apipri.stratus.ai`) handling the LLM and logic.
2.  **The Client App (The "Hub")**:
    *   **Responsibilities**: Authenticates user, captures microphone audio, streams audio to/from SAPI, reads `simAPI_input.json` (telemetry), writes `simAPI_output.jsonl` (commands).
    *   **Target Stack**: Python 3.10+ is recommended for rapid development and excellent cross-platform support for Audio (PyAudio/SoundDevice) and UI (PyQt6/PySide6).
3.  **The Simulator Adapter (The "Spoke")**:
    *   **Responsibilities**: Reads simulator internal state, writes to `simAPI_input.json` (1Hz update), reads `simAPI_output.jsonl` and executes commands.

### 1.2 Data Exchange (SimAPI)
The interface is entirely file-based, located ideally in a standard user directory (e.g., `~/.local/share/StratusAI` or `~/Documents/StratusAI`).
*   **Input**: `simAPI_input.json` (Sim -> Client)
*   **Output**: `simAPI_output.jsonl` (Client -> Sim)
*   **Metadata**: `flight.json` (Auth/Session info)

---

## 2. Platform Specific Strategy

### 2.1 Linux (X-Plane & MSFS)
*   **X-Plane (Native)**:
    *   X-Plane supports native Linux plugins (C/C++ or Python via XPPython3).
    *   **Strategy**: Develop a Python-based X-Plane plugin (`PI_Stratus.py`) or a C++ plugin (`lin.xpl`) that queries DataRefs and dumps them to the JSON file.
*   **MSFS (Proton/Wine)**:
    *   MSFS does not run natively on Linux; it runs via Steam Proton (Wine).
    *   **Strategy**: The "Adapter" must run inside the Proton container to access SimConnect. We can attempt to run the existing Windows Adapter (from the Windows installer) inside the same Proton prefix, or write a lightweight SimConnect bridge.
    *   **Bridge**: The Windows Adapter writes to `Z:\home\user\...\simAPI_input.json`. The Linux Native Client reads that same file from `/home/user/...`.
    *   **Risk**: Path mapping translation between Wine (`Z:\...`) and Linux (`/home/...`) needs to be handled in configuration.

### 2.2 macOS (X-Plane Only)
*   **X-Plane (Native)**:
    *   Similar to Linux, requires a Universal Binary (ARM64/x86_64) plugin.
    *   **Security**: macOS specific entitlements (Microphone access) must be handled if packaging as a standalone `.app`.
*   **MSFS**: Not applicable (MSFS does not run on macOS).

---

## 3. Technology Stack Recommendation

To maximize code sharing between Linux and Mac (and potentially Windows):
*   **Language**: **Python 3.11**
*   **GUI Framework**: **PySide6 (Qt)** or **Tkinter** (Simpler, but less "premium"). Recommended: **PySide6**.
*   **Audio**: **SoundDevice** (PortAudio wrapper) for robust cross-platform audio I/O.
*   **Packaging**: **PyInstaller** (Linux binary / macOS .app bundle).

---

## 4. Implementation Phase Plan

### Phase 1: Investigation & Prototyping (Weeks 1-2)
*   **Goal**: Validate the API and Audio chain without a simulator.
*   **Tasks**:
    1.  Create a "Dummy Adapter" script that generates fake `simAPI_input.json` data.
    2.  Build a CLI "Client" that:
        *   Authenticates with SAPI (using a valid API Key).
        *   Streams Microphone audio to SAPI.
        *   Plays back received audio.
        *   Prints received actions (from SAPI) to console.

### Phase 2: X-Plane Native Adapter (Weeks 3-4)
*   **Goal**: Connect X-Plane (Linux) to the JSON SimAPI.
*   **Tasks**:
    1.  Develop `PI_Stratus.py` (XPPython3 Plugin).
    2.  Map core DataRefs (Lat, Lon, Alt, Heading, Radio Freqs, Transponder) to the SimAPI JSON schema.
    3.  Implement the file writer (1Hz update rate).
    4.  Implement the command reader (Poll `simAPI_output.jsonl` -> Apply DataRefs).

### Phase 3: The Native Client UI (Weeks 5-6)
*   **Goal**: A user-friendly GUI replacing the CLI.
*   **Tasks**:
    1.  Design a modern UI (PySide6) matching the "Premium" aesthetic.
    2.  Implement Settings (Audio Device selection, API Key management).
    3.  Implement Status Dashboard (Connection status, Current Frequency, Mode).

### Phase 4: MSFS Proton Integration (Week 7)
*   **Goal**: Verify MSFS support on Linux.
*   **Tasks**:
    1.  Test running the official Stratus Windows Adapter executable inside the MSFS Proton prefix.
    2.  Configure directory bindings to ensure the Windows Adapter acts on the same JSON files as the Linux Client.

### Phase 5: Packaging & Release (Week 8)
*   **Goal**: Distributable binaries.
*   **Tasks**:
    1.  Build Linux `.AppImage` or `.deb`.
    2.  Build macOS `.dmg` (Signed/Notarized).
    3.  Create installation scripts.

---

## 5. X-Plane Feature Limitations (vs MSFS)

The official Stratus Windows client has **reduced functionality** when used with X-Plane compared to MSFS. These limitations are documented by Stratus and represent potential opportunities for community tooling.

### 5.1 Features NOT Supported on X-Plane

| Feature | MSFS | X-Plane | Notes |
|---------|------|---------|-------|
| **AI Traffic Injection** | ✅ | ❌ | Stratus can spawn AI traffic in MSFS; not possible in X-Plane via SimAPI |
| **Follow-Me Cars** | ✅ | ❌ | Ground vehicle guidance to gates |
| **Marshaller/Docking** | ✅ | ❌ | Visual docking guidance at gates |
| **Pushback Tug Control** | ✅ | ❌ | Automatic pushback from gate |
| **Gate Assignment Display** | ✅ | ⚠️ | Works but no visual SimBrief integration |
| **EFB (Electronic Flight Bag)** | ✅ | ❌ | In-sim tablet UI not available for X-Plane |
| **VR Toolbar** | ✅ | ⚠️ | Separate VR Panel Add-on required |

### 5.2 Technical Reasons

1. **Traffic Injection**: MSFS provides SimConnect APIs that allow spawning SimObjects. X-Plane has no equivalent public API for injecting AI aircraft that integrate with ATC.

2. **Ground Services**: MSFS exposes ground service state via SimVars. X-Plane ground handling is typically managed by third-party plugins (GSX equivalent doesn't exist natively).

3. **EFB/UI**: MSFS has an in-sim browser (Coherent GT) that can render web content. X-Plane uses native OpenGL windows, requiring plugin-based solutions.

### 5.3 Opportunities for Community Projects

These gaps could be filled by standalone or complementary projects:

| Gap | Potential Solution |
|-----|-------------------|
| **AI Traffic** | Integration with plugins like X-Plane's built-in AI, World Traffic 3, or similar |
| **Ground Services** | Integration with Better Pushback, OpenSAM, or similar X-Plane plugins |
| **Follow-Me Car** | A custom X-Plane plugin that spawns a ground vehicle object and moves it along taxi paths |
| **EFB** | Integration with AviTab or a standalone web-based EFB |
| **Visual Docking** | Integration with SAM (Scenery Animation Manager) jetway and docking systems |

### 5.4 DataRefs We Could Leverage

X-Plane exposes DataRefs that could enable some missing features:

```
# AI Traffic (limited)
sim/multiplayer/position/plane*_*    # Read other aircraft positions

# Ground Services
sim/cockpit/engine/APU_running       # APU state for ground power decisions
sim/flightmodel/weight/m_fuel*       # Fuel state for refueling

# Pushback (if integrating with Better Pushback)
bp/connected                         # Better Pushback connection state
bp/started                           # Pushback in progress

# OpenSAM Integration
opensam/jetway/status                # Jetway docking state
```

---

## 6. Next Steps
1.  **Approve this Roadmap.**
2.  Provide a valid **API Key** for testing (Required for SAPI authentication).
3.  Confirm preference for **Python/Qt** stack for the client.
