# Stratus API (SAPI) Findings

**Date**: December 23, 2024  
**API Key Tested**: s4GH8119xFyX (confirmed working)

---

## 🎉 BREAKTHROUGH: Native Client Confirmed Working!

After reviewing the official SAPI documentation at https://p2.stratus.ai/p2/docs/, we found that **audio communication works via REST API + audio file URLs** - not real-time streaming!

### Live Test Results (December 23, 2024)

**With X-Plane running and our plugin writing telemetry:**

```bash
curl "https://apipri.stratus.ai/sapi/getCommsHistory?api_key=XXX"
```

**Response (REAL DATA!):**
```json
{
  "comm_history": [{
    "atc_url": "https://siaudio.s3.us-west-1.amazonaws.com/R26isgM5tKoFg82rSbTa.mp3",
    "station_name": "Truckee Tower",
    "ident": "KTRK",
    "frequency": "120.575",
    "outgoing_message": "Roger. Radar Services Terminated. Squawk VFR. Frequency change approved.",
    "incoming_message": "Cancel flight following."
  }]
}
```

**Audio File Verified:**
```
-rw-r--r-- 1 startux startux 65110 Dec 23 12:04 /tmp/atc_test.mp3
/tmp/atc_test.mp3: Audio file with ID3 version 2.4.0, MPEG ADTS, layer III, 44.1 kHz, Monaural
```

✅ **Audio URLs are real, downloadable, and playable!**

---

## API Overview

**Base URL**: `https://apipri.stratus.ai/sapi/`  
**Authentication**: API key as URL parameter (`?api_key=XXX`)  
**Documentation**: https://p2.stratus.ai/p2/docs/

---

## Audio Communication Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                       Native Linux Client                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. CAPTURE: Record pilot's voice (local speech-to-text)          │
│     OR: Use keyboard/text input                                   │
│                                                                   │
│  2. SEND: POST sayAs?api_key=XXX&message=...&channel=COM1         │
│     → Pilot's message sent to Stratus cloud                 │
│                                                                   │
│  3. POLL: GET getCommsHistory?api_key=XXX                         │
│     → Returns JSON with audio file URLs:                          │
│        {                                                          │
│          "atc_url": "https://storage.../atc_response.mp3",        │
│          "pilot_url": "https://storage.../pilot_message.mp3"      │
│        }                                                          │
│                                                                   │
│  4. PLAY: Download and play the atc_url audio file                │
│     → ATC/Co-pilot response plays through speakers                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Key SAPI Endpoints

### Communication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `sayAs` | GET | Make entity speak. Params: `message`, `channel` (COM1/COM2/INTERCOM), `entity` (atc/copilot/crew) |
| `getCommsHistory` | GET | **Critical**: Returns transmission history with `atc_url` and `pilot_url` audio links |

### Weather & Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `getWX` | GET | ATIS, METAR, TAF for ICAO codes |
| `getTFRs` | GET | GeoJSON flight restrictions |
| `getVATSIM` | GET | VATSIM traffic data |

### Airport Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `assignGate` | GET | Request specific gate |
| `getParking` | GET | Current assigned parking (lat/lon/hdg) |

### Flight Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `setFreq` | GET | Update radio frequencies |
| `setVar` | GET | Set simulator variables |
| `setPause` | GET | Pause/resume ATC simulation |

### VA Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `importVAData` | POST | Custom crew/dispatcher data |

---

## Files and Session Management

### flight.json
- Location: `%LOCALAPPDATA%\StratusAI\flight.json` (Windows)
- Linux equivalent: `~/.local/share/StratusAI/flight.json`
- Contains: `api_key`, current frequencies, flight status
- **We should read this for session context**

### simAPI_input.json
- Our X-Plane plugin writes this ✅
- Contains: Aircraft telemetry, position, radios, transponder

### simAPI_output.jsonl
- Stratus writes commands to this
- Our plugin should read and execute ⏳ (TODO)

---

## Native Client Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                  Stratus Cloud (SAPI)                    │
│  https://apipri.stratus.ai/sapi/                        │
└───────────────────────────────▲───────────────────────────────┘
                                │
                    REST API (HTTP GET/POST)
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                    Native Python Client                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SAPI Interface                                          │  │
│  │  - Poll getCommsHistory (every 1-2 sec)                  │  │
│  │  - Send sayAs for pilot transmissions                    │  │
│  │  - Get weather, gate info                                │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Audio Handler                                           │  │
│  │  - Download audio URLs from comms history                │  │
│  │  - Play via PulseAudio/PipeWire                          │  │
│  │  - Optional: Local STT for pilot voice input             │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SimAPI Handler                                          │  │
│  │  - Read simAPI_input.json (from plugin)                  │  │
│  │  - Write simAPI_output.jsonl (commands to plugin)        │  │
│  │  - Read flight.json (session state)                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  UI (PySide6)                                            │  │
│  │  - Comms history display                                 │  │
│  │  - Frequency controls                                    │  │
│  │  - PTT button / text input                               │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬───────────────────────────────┘
                                │
                         JSON Files
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                      X-Plane Plugin (C)                        │
│                    StratusAIml.xpl ✅                    │
└───────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

### Phase 1: Core Client (MVP)
1. ✅ X-Plane plugin (DONE)
2. SAPI interface - `sayAs`, `getCommsHistory`
3. Audio playback - download and play `atc_url` files
4. Basic UI - text input for pilot messages

### Phase 2: Full Voice
1. Local speech-to-text (Whisper or similar)
2. PTT (Push-to-Talk) support
3. Comms history display

### Phase 3: Polish
1. Frequency panel with auto-tune
2. Weather display
3. Gate assignment
4. Settings/preferences

---

## Wine Testing Notes

**Result**: Failed due to SAPI voice packages  
**Conclusion**: Wine approach abandoned; native client is the way forward

---

## Resources

- [SAPI Documentation](https://p2.stratus.ai/p2/docs/)
- [SimAPI Developer Guide](https://stratusai.freshdesk.com/support/solutions/articles/154000221017)
- [SimVar List](https://portal.stratus.ai/simapi/v1/input_variables.txt)
- [Sample Input JSON](https://portal.stratus.ai/simapi/v1/simapi_input.json)
