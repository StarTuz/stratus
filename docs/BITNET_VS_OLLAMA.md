# Technical Assessment: BitNet vs. Ollama

**Date:** January 2026
**Topic:** Feasibility of BitNet (1.58-bit) as default inference engine.

## Executive Summary

**BitNet (1.58-bit)** is a viable, high-performance alternative to the standard 4-bit quantization used by Ollama. It drastically reduces memory usage and improves CPU inference speed, making it an ideal "safe default" for users with lower-end hardware (e.g., laptops without dedicated GPUs).

However, **Ollama** does not yet officially support the BitNet format (`TQ2_0`) in its stable release. To use BitNet *today* without Python, we would need to integrate `bitnet.cpp` directly via Rust bindings, bypassing Ollama for this specific model, or wait for upstream `llama.cpp` support to land in Ollama.

---

## 1. Comparison Matrix

| Feature | Ollama (Current Default) | BitNet b1.58 (Candidate) |
| :--- | :--- | :--- |
| **Model Format** | GGUF (4-bit / Q4_K_M standard) | TQ2_0 (1.58-bit Ternary {-1, 0, 1}) |
| **Memory (8B Model)** | **~5.1 GB** VRAM/RAM | **~1.8 - 2.0 GB** VRAM/RAM (63% Saving) |
| **Speed (CPU)** | Moderate (User dependent) | **Fast** (Optimized for CPU arithmetic) |
| **Integration** | Easy (External API) | Complex (Requires embedded C++ engine or custom build) |
| **Safety** | Low (User can load 70B model & crash) | **High** (Hard to "accidentally" overflow RAM) |
| **Ecosystem** | Huge (Thousands of models) | Small (Llama3-8B, Falcon-7B, BitNet-3B) |

## 2. Technical Findings

### 2.1 The "Zero Python" Path

We do **not** need Python to run BitNet.

* **Engine**: Microsoft provides `bitnet.cpp`, a C++ inference framework based on `ggml`.
* **Bindings**: Rust bindings exist (`bitnet-cpp-rs`), allowing us to embed the engine directly into `stratus-voice` or `stratus-gui`.

### 2.2 Availability

* **Models**: Pre-trained 1.58-bit versions of **Llama 3 8B** are available on Hugging Face.
* **Software**: Support is currently being merged into `llama.cpp` (the backend of Ollama). Once merged, Ollama will likely support it natively.

## 3. Risk Assessment

* **Pros**:
  * **Massively lower footprint**: Users with 8GB RAM laptops can run Llama 3 8B comfortably + X-Plane.
  * **Latency**: Faster Token-Per-Second (TPS) on CPU-only machines.
  * **Green**: Lower energy consumption.

* **Cons**:
  * **Fragmentation**: We would need two logic paths: one for Ollama (standard) and one for embedded BitNet.
  * **Model Quality**: 1.58-bit quantization is "lossy" compared to 4-bit. While papers claim parity, real-world instruction following (especially for strict ATC syntax) needs verification.

## 4. Recommendation

**Short Term (Now):**
Do **not** replace Ollama yet. The engineering effort to embed `bitnet.cpp` via FFI is non-trivial compared to the "it just works" nature of Ollama API.

**Medium Term (Q2 2026):**
Wait for `llama.cpp` PRs to merge. Once Ollama supports `TQ2_0` (BitNet format), we can simply *ship* a BitNet Modelfile as the default. This gives us all the performance benefits with **zero code changes**.

**Strategic Decision:**
If the team wants to control the "first run experience" tightly and avoid the "Ollama Install" step, embedding `bitnet-cpp-rs` is a valid (but expensive) path to a standalone "one-click" app.

---

### Proposed Action Items

1. **Monitor `llama.cpp`**: Watch for `TQ2_0` merge.
2. **Benchmark**: Manually compile `bitnet.cpp` and test `Llama3-8B-1.58` against our ATC prompts to verify if the "brain" is smart enough at this quantization.
3. **Stick with Ollama** for now, but advise users with low RAM to use `Llama3-8B-Q2_K` (2-bit) as a temporary stopgap if needed.
