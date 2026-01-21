# Market Analysis & Gap Evaluation

**Date:** January 2026
**Topic:** SayIntentions vs. Stratus ATC (Product Viability)

## 1. Market Benchmark: SayIntentions

Analysis of the X-Plane community sentiment (Source: [X-Plane.org Forum Thread 317846](https://forums.x-plane.org/forums/topic/317846-xplane12-sayintentions-atc/)) reveals the current gold standard for AI ATC.

### Key Strengths (User Expectations)

* **Speech Freedom:** Users value "non-scripted" interactions.
* **VFR Perfection:** It is considered the gold standard for VFR, handling the ambiguity of visual flight well.
* **Immersion Features:** Includes "Entourage" (cabin crew, dispatch) and background chatter.
* **Pro-Mode:** A strict mode for serious simmers that penalizes incorrect phraseology, separating "gamers" from "pilots."

### Key Weaknesses (Opportunity)

* **Cost:** ~$150/year subscription is a major friction point.
* **Online Only:** Relies on cloud servers; latency was historically an issue.
* **Platform Bias:** Perceived neglect of X-Plane / Linux in favor of MSFS/Windows.

## 2. Technical Gap Analysis: Stratus (Current)

Comparing our current codebase against these expectations reveals Stratus is a **Prototype**, not a Product.

### Critical Deficiencies

| Feature | Market Standard | Stratus Current Implementation | Severity |
| :--- | :--- | :--- | :--- |
| **State Tracking** | **Stateful**: aware of "Cleared to Land," traffic sequencing, and airspace transitions. | **Stateless**: `stratus-core/src/atc.rs` relies entirely on LLM context window. No persistent rigid state. | 🔴 **CRITICAL** |
| **Voice Quality** | **Neural/Cloud**: Indistinguishable from human. | **Local**: `speech-dispatcher` is robotic/functional. | 🟡 HIGH |
| **Logic** | **Hybrid**: LLM for chat + Rigid Logic for safety/rules. | **Pure LLM**: "Hallucination-prone." No guardrails ensuring FAA 7110.65 compliance. | 🔴 **CRITICAL** |
| **Scope** | IFR + VFR + Ground + Emergency | VFR Pattern (Basic) | 🟡 MEDIUM |

### VFR Viability

* **Current Status**: The VFR logic is currently "fragile." It can handle a basic "pattern" request but lacks the capability to manage:
  * Traffic sequencing (no awareness of other planes).
  * Airspace transitions (Class B/C/D boundaries).
  * Complex taxi routing (no airport graph awareness).

## 3. Conclusion

Stratus excels in **Privacy** (Local), **Cost** (Free), and **OS Support** (Linux), but fails to meet the **Functional Baseline** required for a general release.

**Recommendation**: Do NOT package. Focus development on:

1. **State Machine**: Implement a rigid Rust-based state machine (Ground -> Takeoff -> Pattern -> Landing) to guide the LLM.
2. **Context Injection**: Feed the LLM specific valid states rather than open-ended prompts.
