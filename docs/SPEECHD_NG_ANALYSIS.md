# Analysis: SpeechD-NG & BitNet Integration

**Date:** January 2026
**Subject:** Feasibility of speechd-ng as Core AI/Voice Orchestrator

## Executive Summary

**SpeechD-NG** (StarTuz) is a next-generation speech and AI orchestration daemon for Linux. It exposes a D-Bus interface (`org.speech.Service`) to handle TTS, STT, and LLM queries.

**Crucially, it is NOT an inference engine.** It does not embed `bitnet.cpp` or `llama.cpp` directly. Instead, it acts as a **client** that routes queries to an external backend:

1. **Ollama** (Default)
2. **BitNet** (via OpenAI-compatible server API)

## 1. Architecture Alignment

To use `speechd-ng` in Stratus, we would effectively replace `stratus-voice`'s internal logic with D-Bus calls to `speechd-ng`.

| Feature | Current (`stratus-voice`) | Proposed (`speechd-ng`) |
| :--- | :--- | :--- |
| **STT** | Internal VAD + Whisper (?) | `org.speech.Service.ListenVad()` |
| **TTS** | Internal `speech-dispatcher` client | `org.speech.Service.Speak()` |
| **Brain** | `stratus-core` calls Ollama directly | `stratus-core` calls `org.speech.Service.Think()` |

## 2. BitNet Support

The "BitNet support" in `speechd-ng` refers to its ability to talk to a **BitNet Server**.

* **Configuration**: The daemon has an `ai_backend` setting.
* **Implementation**: It uses standard HTTP/REST calls to a local server (e.g., `localhost:8000`).
* **Implication**: Using `speechd-ng` usually does **not** solve the problem of *running* the BitNet model. We (Stratus components) would still need to ensure a BitNet server is running, OR `speechd-ng` would need to be configured by the user to point to one.

## 3. Recommendation

**Adopting `speechd-ng` would be a major architectural pivot.**

* **Pros**:
  * **Unified Audio**: Solves Linux audio conflict issues (ALSA/Pulse/PipeWire) by offloading to a dedicated daemon.
  * **Abstraction**: We stop caring *which* LLM is running; we just ask the daemon to "Think."
  * **Native**: Aligns with the "Linux First" philosophy.

* **Cons**:
  * **Dependency**: Adds a hard dependency on an external daemon that users must install/configure.
  * **Does not solve Inference**: We still need to help the user set up the actual BitNet/Ollama server that backend `speechd-ng`.

**Verdict**:
If `speechd-ng` is available on the system, Stratus should prefer it. However, we cannot rely on it as the *sole* inference engine provider without bundling the underlying model server.
