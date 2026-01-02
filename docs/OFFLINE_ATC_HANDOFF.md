# ARCHITECTURE HANDOFF: Offline ATC Separation

**IMPORTANT**: This document defines the strict project boundaries for Stratus and its speech backend.

## 1. Project Roles

- **Stratus (Client)**: **THE BRAIN**.
  - Responsible for: X-Plane data, Radio/Frequency tracking, ATC logic, Prompt Engineering.
  - Controls: The "Content" of the speech and the "Logic" of the ATC.
- **speechserverdaemon (External)**: **THE MOTOR**.
  - Responsible for: TTS (Piper), STT (Wyoming/Vosk), LLM (Ollama).
  - Controls: The "Physicality" of the speech and the raw AI "Inference".

## 2. Strict Boundary Rules

1. **NEVER** modify the `speechserverdaemon` source code from a Stratus task. The daemon is a standalone, release-stage service used by other apps.
2. If the daemon lacks a feature (e.g., frequency tracking), **implement it in the Stratus client** by maintaining state and injecting it into the context of the `Think(context)` call.
3. **STT Fallback**: The daemon handles STT engines. It is configured via `Speech.toml` to prefer Wyoming but falls back to Vosk and other internal mechanisms. Stratus should simply call `ListenVad` and handle the result.

## 3. Latency & Timeouts

- GUI D-Bus calls use background threads. Status polling happens every 5s.
- **LLM Reasoning**: Initial cold-starts and long generations can take up to **30 seconds**. The daemon is configured for a 30s timeout; the client handles this asynchronously to avoid UI freezes.

## 4. User Customization

- **Basic Management**: Stratus provides native buttons for starting/stopping the Ollama service and pulling models via the "Local AI (Ollama)" section in Settings.
- **Advanced Config**: For deep customization (audio devices, wake-word sensitivity, etc.), users edit **`~/.config/speechd-ng/Speech.toml`**.
