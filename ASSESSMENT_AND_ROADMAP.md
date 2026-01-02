# Stratus ATC - Linux & Mac Implementation Roadmap

## Executive Summary

Stratus ATC is an **open source, fully local AI ATC** for flight simulators. It runs entirely on your hardware using Ollama for LLM inference and local TTS, requiring no cloud services or subscriptions.

The architecture is "Brain vs Motor":

1. **Stratus (The Brain)**: All ATC logic, FAA phraseology, telemetry tracking, and AI prompt construction.
2. **speechserverdaemon (The Motor)**: TTS/STT/LLM engine (D-Bus interface).

> [!CAUTION]
> **LEGAL DISCLAIMER**: This software and any associated AI features (Mentor, Co-Pilot, ATC) are for **ENTERTAINMENT PURPOSES ONLY**. They are NOT for real flight training, certified instruction, or use in actual aircraft. The advice given by the AI may be inaccurate, dangerous, or contrary to real-world aviation regulations.

## 1. Technical Architecture

### 1.1 Core Components

1. **Local AI (Ollama)**: Runs on your machine, provides LLM responses for ATC.
2. **The Client App (Python/Qt6)**:
   - Captures microphone audio (STT via Whisper)
   - Displays ATC communications
   - Reads telemetry from simulator
   - Generates context-aware ATC prompts
3. **The Simulator Adapter (The "Spoke")**:
   - Reads simulator internal state
   - Writes to `simAPI_input.json` (1Hz update)
   - Reads `simAPI_output.jsonl` and executes commands

### 1.2 Data Exchange (SimAPI)

File-based interface at `~/.local/share/StratusATC`:

- **Input**: `simAPI_input.json` (Sim → Client)
- **Output**: `simAPI_output.jsonl` (Client → Sim)

---

## 2. Platform Support

### 2.1 Linux (X-Plane)

- **X-Plane 11/12**: Native C plugin (`StratusATC.xpl`) or Python via XPPython3
- **MSFS (Proton)**: Possible via SimConnect bridge (future work)

### 2.2 macOS (X-Plane)

- Universal Binary (ARM64/x86_64) plugin
- Entitlements for Microphone access required

---

## 3. Technology Stack

- **Language**: Python 3.11
- **GUI Framework**: PySide6 (Qt6)
- **Audio**: SoundDevice (PortAudio wrapper)
- **LLM**: Ollama (local)
- **STT**: Whisper (local)
- **TTS**: speechd-ng (local)
- **Packaging**: PyInstaller (AppImage/deb)

---

## 4. Implementation Phases

### ✅ Phase 1: Core Infrastructure (Complete)

- X-Plane native plugin (telemetry export)
- Local AI integration (Ollama)
- Qt6 GUI client
- ComLink web interface

### ✅ Phase 2: ATC Logic (Complete)

- FAA VFR phraseology
- Context-aware prompts
- Manual identity overrides

### 🚧 Phase 3: Voice Input (In Progress)

- Whisper STT integration
- PTT hotkey binding

### 📋 Phase 4: Sim Control

- Parse AI responses → control aircraft
- Set squawk codes, frequencies via DataRefs

### 📋 Phase 5: Packaging & Release

- Linux AppImage/deb
- macOS dmg (signed/notarized)

---

## 5. X-Plane Specific Notes

### 5.1 Features Unique to Stratus

| Feature | Status | Notes |
|---------|--------|-------|
| **Fully Offline** | ✅ | No internet required |
| **No Subscription** | ✅ | Open source, free forever |
| **Linux Native** | ✅ | First-class support |
| **Voice Privacy** | ✅ | Audio stays on your machine |

### 5.2 DataRefs We Leverage

```
sim/flightmodel/position/latitude
sim/flightmodel/position/longitude
sim/cockpit2/radios/actuators/com1_frequency_hz_833
sim/cockpit/radios/transponder_code
```

---

## 6. Advanced Features (Future)

### Mentor System

- Radio handling (Full/Partial/None)
- Real-time flight advice
- "Certified Fun Flight Lessons" mode

### Co-Pilot Control (Research)

- Full flight automation via DataRefs
- Challenge: AI control of yoke/throttle

---

## 7. Next Steps

1. Complete PTT/Voice Input (Phase 3)
2. Implement Sim Control (Phase 4)
3. Package for distribution
