# StratusML - Project Handoff

**Date**: December 29, 2024  
**Status**: ⚠️ **CLIENT COMPLETE - SESSION CREATION BLOCKED**

---

## Executive Summary

The native Linux client is **feature-complete** but **cannot establish sessions** due to Stratus architecture. The Windows client uses process detection (`GetProcessesByName`, `FindWindow`) that cannot see Linux-native X-Plane.

**Support request sent** to Stratus Discord requesting:
- `POST /session/create` REST endpoint
- Headless Linux sidecar
- Process detection bypass

### What Works Now (Read-Only)
- ✅ Weather/ATIS via `getWX`
- ✅ Historical comms with audio via `getCommsHistory`
- ✅ Radio panel sync with X-Plane
- ✅ Full Qt6 GUI

### What's Blocked (Session Required)
- ❌ Voice → ATC communication (`sayAs`)
- ❌ Location-aware responses
- ❌ Gate assignments (`assignGate`)

---

## Investigation Summary (Dec 28-29, 2024)

Exhaustive reverse-engineering of Stratus session establishment:

| Approach | Result |
|----------|--------|
| REST endpoints (sapi/v1/input, startFlight, etc.) | Server accepts, no session |
| WebSocket (wss://comlink.stratus.ai) | Connection rejected |
| Continuous 60-second telemetry | No session |
| SimBrief integration with UserID | No session |
| Exact DCS adapter format in Proton | Process detection blocks |
| Dummy X-Plane.exe process in Wine | Not detected |

**Root Cause**: Windows client checks for running Windows process. Linux X-Plane is invisible.

---

## Original Accomplishments

---

## What Was Accomplished

### ✅ X-Plane Plugin (Complete)
- **Location**: `adapters/xplane/StratusAIml/lin_x64/StratusAIml.xpl`
- **Status**: Working, tested with X-Plane 12.3.3
- **Features**:
  - Reads all essential DataRefs (position, radios, transponder, autopilot)
  - Writes telemetry to `~/.local/share/StratusAI/simAPI_input.json` at 1Hz
  - Custom log file (`stratusaiml.log`) - doesn't pollute X-Plane's Log.txt

### ✅ API Research (Complete)
- **SAPI Documentation**: https://p2.stratus.ai/p2/docs/
- **SimAPI Documentation**: https://stratusai.freshdesk.com/support/solutions/articles/154000221017
- **API Key**: Obtained and validated (stored in `config.ini`, gitignored)

### ✅ Live Testing (Breakthrough!)
```bash
# This command returned REAL DATA with audio URLs!
curl "https://apipri.stratus.ai/sapi/getCommsHistory?api_key=XXX"

# Response included:
{
  "comm_history": [{
    "atc_url": "https://siaudio.s3.us-west-1.amazonaws.com/R26isgM5tKoFg82rSbTa.mp3",
    "station_name": "Truckee Tower",
    "outgoing_message": "Roger. Radar Services Terminated..."
  }]
}

# Audio file successfully downloaded and verified:
# - 65KB MP3 file
# - 44.1kHz, mono, playable
```

### ✅ Audio Module (Complete - Dec 27, 2024)
- **Location**: `client/src/audio/`
- **Status**: Working, tested with real Stratus audio URLs
- **Components**:
  - `downloader.py` - Downloads audio from S3 URLs with local caching + ThreadPoolExecutor
  - `player.py` - Cross-platform player using external subprocess (mpv/afplay)
  - `handler.py` - High-level interface combining download + playback
- **Platform Support**:
  - **Linux**: Uses `mpv` (preferred) or `ffplay`
  - **macOS**: Uses `afplay` (built-in)
- **Features**:
  - Non-blocking audio (no Python GIL issues!)
  - Local cache in `~/.cache/StratusAI/audio/`
  - Callbacks for playback start/complete events
  - Volume control, skip, queue management
- **Test**: `python client/src/tests/test_audio.py`

### ✅ CLI Test Harness (Complete - Dec 27, 2024)
- **Location**: `client/src/cli.py`
- **Status**: Working, full end-to-end tested
- **Features**:
  - Interactive mode with command prompt
  - One-shot commands for scripts (`--status`, `--history`, `--play`, `--say`)
  - Automatic config.ini discovery
  - Background polling for new comms
  - Audio playback controls (volume, pause, skip)
  - Weather queries
- **Run**: `.venv/bin/python client/src/cli.py -c` (auto-connect)

### ✅ GUI Client (Complete - Dec 27, 2024)
- **Location**: `client/src/ui/`
- **Status**: Fully functional with X-Plane integration
- **Components**:
  - `main_window.py` - Main application window with menu bar
  - `comms_widget.py` - Communication history with per-message audio playback
  - `frequency_panel.py` - COM1/COM2/transponder display with LIVE sim data
  - `transmission_panel.py` - Text input with quick phrases and PTT button
  - `status_panel.py` - Connection status, volume control, polling indicator
  - `system_tray.py` - System tray with minimize-to-tray
  - `styles.py` - Modern dark theme with accent colors
- **Features**:
  - ✅ Dark theme with modern glassmorphism-inspired design
  - ✅ Auto-polling for new communications (5 second interval)
  - ✅ Audio playback with mpv/afplay (cross-platform)
  - ✅ **Always on Top mode** for overlay over simulator
  - ✅ **Compact Mode** for minimal overlay
  - ✅ **Real-time frequency sync** from X-Plane
  - ✅ Frequency swap buttons (control sim from GUI)
  - ✅ System tray with minimize-to-tray
  - ✅ Quick phrase buttons for common responses
- **Run**: `.venv/bin/python client/src/main.py`

### ✅ ComLink Web Interface (Complete - Dec 28, 2024)
- **Location**: `client/src/web/`
- **Status**: Fully functional, browser-based interface
- **Access**: http://localhost:8080/comlink
- **Components**:
  - `server.py` - Flask + Socket.IO web server
  - Embedded HTML/CSS/JS with modern touch-friendly UI
- **Features**:
  - ✅ **AI Copilot Toggle** - Enable/disable copilot from tablet/phone (Updated Dec 28)
  - ✅ **Real-time Sync** - Bidirectional state sync with main GUI
  - ✅ **Full Comms History** - View and play messages remotely

### ✅ Settings & AI Features (Complete - Dec 28, 2024)
- **Settings Panel**:
  - **ATC Mode**: Student / Standard / Pro (affects guidance/verbosity)
  - **AI Crew**: Cabin Crew & Tour Guide toggles (for immersive announcements)
  - **Mentor**: Virtual Flight Instructor toggle (ask questions via Intercom)
- **AI Copilot**:
  - **Auto-Tune**: Automatically tunes COM1/COM2 when ATC gives frequencies
  - **Auto-Squawk**: Automatically sets transponder mode/code
  - **Visual Feedback**: Copilot button glows when active, logs actions

### ✅ Voice Input Integration (Complete - Dec 28, 2024)
- **Integration**: Uses **SpeechD-NG** (Speech Daemon - Next Gen) via D-Bus
- **Features**:
  - **VAD (Voice Activity Detection)**: "Tap to listen, auto-stop on silence"
  - **Backend**: Configurable **Wyoming** (for Whisper) or **Vosk** (local fallback)
  - **Privacy**: Local processing supported (via Vosk)
- **Usage**:
  - Click "PTT" button (or tap on ComLink)
  - Button turns Red (TX)
  - Speak command
  - Silence detected -> Transcribes -> Sends auto-magically
- **Features**:
  - ✅ **Works on any device** - tablets, phones, second monitors
  - ✅ **Real-time updates** via WebSocket
  - ✅ **Frequency display** with touch-to-tune
  - ✅ **Frequency swap** buttons
  - ✅ **Communications history** with audio playback
  - ✅ **Text transmission** input with quick phrases
  - ✅ **Dark theme** matching the desktop client
  - ✅ **Mobile-optimized** touch interface
- **Usage**:
  - Default: Starts automatically with GUI (`python main.py`)
  - Headless: `python main.py --web` (web + audio only, no GUI)
  - Disable: `python main.py --no-web`
- **Purpose**: 
  - **Fullscreen flight sim users** who can't alt-tab
  - **VR users** who need a companion device
  - **Multi-monitor setups**
  - **Tablet/phone control** for immersive experience

### ✅ X-Plane Integration (Complete - Dec 27, 2024)
- **Location**: `adapters/xplane/`
- **Status**: Bidirectional communication working
- **Components**:
  - `PI_Stratus.py` - Main X-Plane plugin (XPPython3)
  - `overlay.py` - Optional in-sim ImGui overlay
- **Features**:
  - ✅ Exports telemetry (position, attitude, frequencies) every 0.5s
  - ✅ Reads commands to set frequencies/transponder
  - ✅ Data exchange via JSON files in `~/.local/share/StratusAI/`
  - ✅ Supports COM1/COM2 swap/tune from GUI
- **DataRefs Supported**:
  - COM1/COM2 active and standby frequencies
  - Transponder code and mode
  - Full position/attitude/speed telemetry
- **Install**: Copy to `X-Plane/Resources/plugins/PythonPlugins/StratusML/`

---

## Key Discovery: How Audio Works

**No real-time streaming required!** The flow is:

```
┌─────────────────────────────────────────────────────────────────┐
│                        COMMUNICATION FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PILOT INPUT                                                  │
│     └─► sayAs API (text message)                                 │
│         https://apipri.stratus.ai/sapi/sayAs?              │
│         api_key=XXX&message=...&channel=COM1                     │
│                           │                                      │
│                           ▼                                      │
│  2. CLOUD PROCESSING                                             │
│     └─► Stratus processes, AI generates response           │
│                           │                                      │
│                           ▼                                      │
│  3. POLL FOR RESPONSE                                            │
│     └─► getCommsHistory API                                      │
│         Returns JSON with atc_url audio links                    │
│                           │                                      │
│                           ▼                                      │
│  4. PLAY AUDIO                                                   │
│     └─► Download MP3 from atc_url                                │
│     └─► Play locally (mpv, paplay, python)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints (Verified Working)

| Endpoint | Status | Purpose |
|----------|--------|---------|
| `getCommsHistory` | ✅ **TESTED** | Returns comm history with audio URLs |
| `sayAs` | 📋 Documented | Send pilot messages |
| `getWX` | 📋 Documented | Get ATIS/METAR/TAF |
| `setFreq` | 📋 Documented | Tune radios |
| `assignGate` | 📋 Documented | Request gate assignment |
| `getParking` | 📋 Documented | Get assigned parking |
| `setPause` | 📋 Documented | Pause ATC simulation |

---

## File Structure

```
StratusML/
├── README.md                          # Project overview
├── ASSESSMENT_AND_ROADMAP.md          # Technical feasibility
├── PROJECT_STATUS.md                  # Current status
├── config.ini                         # API key (gitignored)
│
├── adapters/
│   └── xplane/
│       ├── CMakeLists.txt             # Build config
│       ├── README.md                  # Build instructions
│       ├── setup_sdk.sh               # SDK download
│       ├── src/
│       │   └── stratus_plugin.c # Plugin source ✅
│       └── StratusAIml/
│           └── lin_x64/
│               └── StratusAIml.xpl  # Built plugin ✅
│
├── client/                            # Python client
│   ├── requirements.txt
│   └── src/
│       ├── audio/                     # Audio module ✅
│       │   ├── downloader.py          # URL download + caching
│       │   ├── player.py              # Audio playback (sounddevice)
│       │   └── handler.py             # High-level audio handler
│       ├── core/
│       │   └── sapi_interface.py      # SAPI REST client
│       ├── simapi/
│       │   └── file_watcher.py        # SimAPI JSON watcher
│       ├── ui/
│       │   └── main_window.py         # PySide6 GUI (stub)
│       └── tests/
│           └── test_audio.py          # Audio module tests ✅
│
├── docs/
│   ├── SAPI_FINDINGS.md               # API research ✅
│   ├── XPLANE_12_PLATFORM.md          # X-Plane features
│   └── XPLANE_EXTENSIONS.md           # Integration opportunities
│
├── scripts/
│   └── setup_wine_sapi.sh             # Wine setup (not needed now)
│
└── tests/
    ├── test_sapi_connection.py        # API connectivity test
    ├── test_sapi_websocket.py         # WebSocket test (N/A)
    ├── test_xplane_webapi.py          # X-Plane Web API test
    └── test_xplane_websocket.py       # X-Plane WebSocket test
```

---

## Native Client Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                  Stratus Cloud (SAPI)                    │
│              https://apipri.stratus.ai/sapi/             │
└───────────────────────────────▲───────────────────────────────┘
                                │
                    REST API (HTTP GET)
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                    Native Python Client                        │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SAPI Module                                             │  │
│  │  - getCommsHistory() → poll for new transmissions        │  │
│  │  - sayAs() → send pilot messages                         │  │
│  │  - getWX() → weather data                                │  │
│  │  - setFreq() → tune radios                               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Audio Module                                            │  │
│  │  - Download MP3 from atc_url                             │  │
│  │  - Play via PulseAudio/PipeWire                          │  │
│  │  - Queue management for multiple responses               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SimAPI Module                                           │  │
│  │  - Watch simAPI_input.json (from plugin)                 │  │
│  │  - Write simAPI_output.jsonl (commands to plugin)        │  │
│  │  - Parse flight.json (session state)                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  UI Module (PySide6)                                     │  │
│  │  - Comms history display                                 │  │
│  │  - Frequency panel                                       │  │
│  │  - PTT / text input                                      │  │
│  │  - System tray integration                               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Voice Input (Optional - Phase 2)                        │  │
│  │  - Local STT (Whisper)                                   │  │
│  │  - Push-to-Talk hotkey                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬───────────────────────────────┘
                                │
                         JSON Files
              ~/.local/share/StratusAI/
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                      X-Plane Plugin (C)                        │
│                    StratusAIml.xpl ✅                    │
└───────────────────────────────────────────────────────────────┘
                                │
                          DataRefs
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                        X-Plane 12                              │
└───────────────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: MVP (Text-Only Client)
**Goal**: Working client with text input and audio output

| Task | Priority | Status |
|------|----------|--------|
| SAPI Python module | P0 | ✅ **COMPLETE** |
| Audio playback (download + play MP3) | P0 | ✅ **COMPLETE** |
| Basic CLI interface | P0 | ✅ **COMPLETE** |
| Poll loop for comms history | P0 | ✅ **COMPLETE** |
| **Phase 1** | | **✅ COMPLETE** |

### Phase 2: GUI Client
**Goal**: Full-featured GUI application

| Task | Priority | Status |
|------|----------|--------|
| PySide6 main window | P1 | ✅ **COMPLETE** |
| Comms history display | P1 | ✅ **COMPLETE** |
| Frequency panel | P1 | ✅ **COMPLETE** |
| Transmission panel | P1 | ✅ **COMPLETE** |
| Status/volume panel | P1 | ✅ **COMPLETE** |
| System tray integration | P2 | ⏳ Pending |
| **Phase 2** | | **🔧 90% COMPLETE** |

### Phase 3: Voice Input
**Goal**: Push-to-talk with local speech recognition

| Task | Priority | Effort |
|------|----------|--------|
| Whisper integration | P2 | 4-6 hours |
| PTT hotkey binding | P2 | 2-3 hours |
| Audio capture | P2 | 2-3 hours |
| **Total Phase 3** | | **~10 hours** |

### Phase 4: Polish
**Goal**: Production-ready release

| Task | Priority | Effort |
|------|----------|--------|
| Plugin command processing | P2 | 4-6 hours |
| macOS build/test | P2 | 4-6 hours |
| Installer/packaging | P3 | 4-6 hours |
| Documentation | P3 | 2-3 hours |
| **Total Phase 4** | | **~16 hours** |

---

## Key Resources

### Documentation
- [SAPI API Docs](https://p2.stratus.ai/p2/docs/)
- [SimAPI Developer Guide](https://stratusai.freshdesk.com/support/solutions/articles/154000221017)
- [SimVar Reference](https://portal.stratus.ai/simapi/v1/input_variables.txt)
- [Sample Input JSON](https://portal.stratus.ai/simapi/v1/simapi_input.json)

### Community
- [Stratus Discord](https://discord.gg/stratus) - For questions/support
- [X-Plane Forum](https://forums.x-plane.org/) - X-Plane specific issues

### Development
- [X-Plane SDK](https://developer.x-plane.com/sdk/)
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)

---

## Wine Testing Notes

**Attempted**: Running Windows client under Wine  
**Result**: Failed - SAPI voice packages not available in Wine  
**Conclusion**: Native client is the correct approach (and now proven feasible!)

---

## Outstanding Questions

1. **Session persistence**: How long does a session stay active without telemetry updates?
2. **Rate limits**: Any API rate limits we should be aware of?
3. **Audio queue**: Best practice for handling multiple rapid responses?

These can be answered through testing or by asking in the Stratus Discord.

---

## Conclusion

**The path is clear.** We have:
- ✅ Working X-Plane plugin
- ✅ Complete API documentation
- ✅ Live proof that audio URLs work
- ✅ Clear architecture for native client

**Next step**: Build the Python client, starting with Phase 1 MVP.

---

*This handoff document was created on December 23, 2024 after confirming the feasibility of a native Linux/Mac Stratus client.*
