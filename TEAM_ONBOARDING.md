# Team Onboarding: Stratus ATC

Welcome to the team! This document covers the environment setup, architecture, and workflows for the **Rust-based** Stratus ATC system.

## ⚡ Quick Start (Linux)

### 1. System Dependencies

You will need Rust, Clang, and Audio libraries.

**Arch Linux:**

```bash
sudo pacman -S rust cargo clang cmake speech-dispatcher alsa-lib systemd-libs
```

**Ubuntu/Debian:**

```bash
sudo apt install cargo clang cmake libspeechd-dev libasound2-dev libsystemd-dev libdbus-1-dev
```

### 2. AI Backend (Ollama)

Install and run Ollama with the Llama 3 model.

```bash
ollama serve
# In another terminal:
ollama pull llama3
```

### 3. Build the Project

```bash
cd stratus-rs
cargo build
```

### 4. Run the Stack

You need two terminals.

Terminal 1 (Voice Service):

```bash
cargo run --bin stratus-voice
```

Terminal 2 (GUI):

```bash
cargo run --bin stratus-gui
```

---

## Architecture Overview

**Mandate: Zero Python.**
We use Rust for everything performance-critical and UI-related to ensure low latency and easy distribution.

### 1. crates

* `stratus-voice`: The ears. Handles device inputs and VAD.
* `stratus-gui`: The face and brain. Handles user interaction and LLM prompting.
* `stratus-core`: The logic. Shared types and state machines.
* `stratus-commander`: The hands. Library that talks to X-Plane.

### 2. IPC

* **D-Bus**: Used for `voice` -> `gui` communication (`SpeechRecognized` signal).
* **Files**: JSON/JSONL files in `~/.local/share/StratusATC` for X-Plane telemetry and commands.

---

## Development Workflows

### Editing the Brain

Logic for the ATC resides in `stratus-core/src/atc.rs`.

* `AtcEngine`: Manages the conversation history.
* `OllamaClient`: Handles API requests.

### Editing the Voice Pipeline

Logic resides in `stratus-voice/src/main.rs`.

* Uses `cpal` for audio capture.
* Uses `webrtc-vad` for silence detection.

### X-Plane Plugin

The C plugin (`adapters/xplane/src/stratus_plugin.c`) links against `stratus-commander`.
If you modify `stratus-commander`, you must rebuild the X-Plane plugin:

```bash
cd adapters/xplane
mkdir -p build && cd build
cmake ..
make
mv StratusATC/lin_x64/StratusATC.xpl ../StratusATC/lin_x64/
```

---

## Rules of Engagement

1. **NO PYTHON**. Do not add Python scripts for core functionality.
2. **Verify Commits**: Ensure `cargo check` passes before pushing.
3. **Strict Types**: Use Rust's type system to enforce valid ATC commands.
