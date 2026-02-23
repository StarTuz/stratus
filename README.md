# StratusATC

**A Next-Generation, Open-Source ATC for X-Plane 12 (Linux-First)**

StratusATC is a local, privacy-focused Air Traffic Control system for X-Plane 12. It uses local LLMs (Ollama) and neural speech recognition to provide a fluid, realistic ATC experience without relying on cloud APIs or subscriptions.

## Architecture (Pure Rust)

The system needs **ZERO Python**. It is built entirely in Rust for performance and stability.

```mermaid
graph TD
    User((Pilot)) -- "Voice (PTT)" --> Voice[stratus-voice (Service)]
    Voice -- "D-Bus Signal" --> GUI[stratus-gui (App/Brain)]
    GUI -- "Ollama Generation" --> LLM[Ollama (Llama 3)]
    GUI -- "Text-to-Speech" --> Spd[speech-dispatcher]
    GUI -- "Processing" --> Core[stratus-core]
    Core -- "Commands (.jsonl)" --> Sim[X-Plane 12]
    Sim -- "Telemetry (.json)" --> GUI
```

### Components

* **`stratus-voice`**: A background service that monitors your PTT key, handles audio capture, performs Voice Activity Detection (VAD), and transcribes speech. Emits D-Bus signals.
* **`stratus-gui`**: The main application window. It acts as the "Brain", receiving voice signals, managing the conversation context with the LLM, and displaying the UI.
* **`stratus-core`**: Shared library containing the "AtcEngine", command parsing logic, and state management.
* **`stratus-commander`**: Rust FFI library linked into the X-Plane C plugin for controlling the simulator.

## Prerequisites

* **OS**: Linux (Arch/Ubuntu/Fedora)
* **Simulator**: X-Plane 12 (Native C Plugin provided)
* **AI Backend**: [Ollama](https://ollama.com/) running `llama3` or compatible model.
* **TTS**: `speech-dispatcher` (`sudo pacman -S speech-dispatcher` or equivalent).
* **Build Tools**: Rust (Cargo), `cmake`, `clang`.

## Installation & Running

### 1. Build the Project

```bash
cd stratus-rs
cargo build --release
```

### 2. Configure PTT

Edit `stratus-rs/stratus-voice/src/ptt_hook.rs` to point to your specific input device (e.g., `/dev/input/by-id/...`).
*(Future versions will have a config file)*

### 3. Run the Voice Service

This service needs access to input devices.

```bash
cd stratus-rs
cargo run --bin stratus-voice
```

### 4. Run the GUI

Launch the main application.

```bash
cd stratus-rs
cargo run --bin stratus-gui
```

## Development & quality

We run a **full CI pipeline** on every push and PR: format check, Clippy, unit tests, and scenario regression (mock-only). See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the local checklist and **[docs/QUALITY_AND_CI.md](docs/QUALITY_AND_CI.md)** for pipeline details.

```bash
cd stratus-rs
cargo fmt --all && cargo clippy --all-targets -- -D warnings && cargo test
STRATUS_EVAL_MOCK_ONLY=1 cargo run --release -p stratus-eval   # scenario regression
```

## Legacy

The old Python prototype has been archived to `.legacy_client/` and is no longer used.

## License

MIT
