# Stratus ATC - Session Handoff

**Last Updated:** January 14, 2026

---

## Session Summary (January 14, 2026)

### Major Changes This Session

#### 1. Zero Python Migration (Complete) ✅

The entire system has been migrated to Rust.

- **Legacy Python Client**: Archived to `.legacy_client/`.
- **New Architecture**: Pure Rust (`stratus-voice`, `stratus-gui`, `stratus-core`).

#### 2. Voice Input (Rust) ✅

- Implemented `stratus-voice` service using `cpal`, `webrtc-vad`, `evdev`, and `speechd-ng` (via D-Bus).
- Emits `SpeechRecognized` signal to D-Bus.

#### 3. Sim Control & Brain (Rust) ✅

- Implemented `AtcEngine` command parsing in `stratus-core`.
- Implemented `stratus-commander` FFI library for X-Plane plugin.
- Wired up `stratus-gui` to orchestrate Voice -> Brain -> Sim.

---

## Architecture: Pure Rust

> **Critical**: NO PYTHON.

### Rust Codebase (`stratus-rs/`)

```
stratus-rs/
├── stratus-core/           # Shared logic
│   ├── voice.rs            # D-Bus Signal Listener
│   ├── commands.rs         # Command Parsing/Writing
│   └── atc.rs              # Brain Logic
├── stratus-voice/          # Voice Service (Input)
├── stratus-gui/            # GUI App (Orchestrator)
└── stratus-commander/      # FFI Library (Sim Control)
```

### Data Flow

```
Voice (PTT) ──► stratus-voice ──(D-Bus)──► stratus-gui
                                              │
                                              ▼
                                          AtcEngine (Ollama)
                                              │
        stratus_commands.jsonl ◄──(Commands)──┴──(Response)──► TTS
                  │
                  ▼
            X-Plane Plugin
```

---

## Build Commands

### Rust Workspace

```bash
cd stratus-rs
cargo build
```

### X-Plane Plugin

```bash
cd adapters/xplane
mkdir build && cd build
cmake .. && make
mv StratusATC/lin_x64/StratusATC.xpl ../StratusATC/lin_x64/
```

---

## Next Steps

### P0: Packaging

1. Create AppImage for `stratus-gui`.
2. Create systemd unit for `stratus-voice`.

### P1: Refinements

1. Improve command parsing regex in `atc.rs`.
2. Add config file for PTT device path.

---

## Prohibited Patterns

| Pattern | Reason |
|:--------|:-------|
| Python Code | Zero Python Mandate |
| Cloud APIs | 100% Offline Mandate |
