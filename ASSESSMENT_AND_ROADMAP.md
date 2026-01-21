# Stratus ATC - Linux & Mac Implementation Roadmap

## Executive Summary

Stratus ATC is an **open source, fully local AI ATC** for flight simulators. It runs entirely on your hardware using Ollama for LLM inference and local TTS, requiring no cloud services or subscriptions.

The architecture is "Rust Trio":

1. **stratus-gui (The Brain)**: All ATC logic, telemetry tracking, and AI prompt construction.
2. **stratus-voice (The Ears)**: Local speech engine (D-Bus interface).
3. **stratus-commander (The Hands)**: FFI Library for Sim Control.

> [!CAUTION]
> **LEGAL DISCLAIMER**: This software and any associated AI features (Mentor, Co-Pilot, ATC) are for **ENTERTAINMENT PURPOSES ONLY**. They are NOT for real flight training, certified instruction, or use in actual aircraft. The advice given by the AI may be inaccurate, dangerous, or contrary to real-world aviation regulations.

## 1. Technical Architecture

### 1.1 Core Components

1. **Local AI (Ollama)**: Runs on your machine (Llama 3 recommended).
2. **The Client App (Rust/Iced)**:
   - Captures microphone audio (via `stratus-voice` D-Bus signal)
   - Displays ATC communications
   - Reads telemetry from simulator
   - Generates context-aware ATC prompts
   - Sends Text-to-Speech commands
3. **The Simulator Adapter (Native C)**:
   - Reads simulator internal state
   - Writes to `stratus_telemetry.json` (1Hz update)
   - Reads `stratus_commands.jsonl` and executes commands via `stratus-commander`.

### 1.2 Data Exchange (Telemetry)

File-based interface at `~/.local/share/StratusATC`:

- **Input**: `stratus_telemetry.json` (Sim → Client)
- **Output**: `stratus_commands.jsonl` (Client → Sim)

---

## 2. Platform Support

### 2.1 Linux (X-Plane)

- **X-Plane 11/12**: Native C plugin (`StratusATC.xpl`) embedding Rust logic.
- **MSFS (Proton)**: Possible via SimConnect bridge (future work).

### 2.2 macOS (X-Plane)

- Universal Binary (ARM64/x86_64) plugin can be built from `stratus-commander`.

---

## 3. Technology Stack

- **Language**: Rust
- **GUI Framework**: Iced
- **Audio**: cpal + webrtc-vad (in `stratus-voice`)
- **LLM**: Ollama (local)
- **STT**: speechd-ng / whisper.cpp (via `stratus-voice`)
- **TTS**: speech-dispatcher
- **IPC**: D-Bus

---

## 4. Implementation Phases

### ✅ Phase 1: Core Infrastructure (Complete)

- X-Plane native plugin (telemetry export)
- Local AI integration (Ollama)
- Rust Iced GUI client

### ✅ Phase 2: ATC Logic (Complete)

- FAA VFR phraseology
- Context-aware prompts
- `AtcEngine` state machine in Rust

### ✅ Phase 3: Voice Input (Complete)

- `stratus-voice` service created
- D-Bus signal emission (`SpeechRecognized`)
- PTT via `evdev`

### ✅ Phase 4: Sim Control (Complete)

- `stratus-commander` FFI library
- Command parsing in `AtcEngine`
- Execution in X-Plane

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
| **Zero Python** | ✅ | No external dependencies |

### 5.2 DataRefs We Leverage

```
sim/flightmodel/position/latitude
sim/flightmodel/position/longitude
sim/cockpit2/radios/actuators/com1_frequency_hz_833
sim/cockpit/radios/transponder_code
```

---

## 6. Next Steps

1. Package `stratus-voice` and `stratus-gui` for distribution.
2. Refine LLM prompts for better accuracy.
