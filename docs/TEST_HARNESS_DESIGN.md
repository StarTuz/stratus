# Design: Stratus ATC Verification Suite (`stratus-eval`)

**Date:** January 2026
**Goal:** Automated verification of ATC logic against FAA Order 7110.65.

## 1. Architecture

We will create a new binary/crate `stratus-eval` (or a dedicated `tests/` integration suite) that acts as a **headless simulator**.

```mermaid
graph TD
    A[Test Runner (stratus-eval)] -->|Load| B(Golden Scenarios .yaml)
    A -->|Mock Telemetry| C[Stratus Core (ATC Logic)]
    C -->|Query| D[Mocked LLM (Wiremock/Ollama)]
    C -->|Response| A
    A -->|Validate| E[Assertions]
    E -->|Regex| F[Strict Syntax]
    E -->|LLM-Judge| G[Semantic Compliance]
```

## 2. "Golden Scenarios" Format

We will define test cases in YAML to ensure they are readable by pilots/controllers.

```yaml
# tests/scenarios/vfr_pattern_01.yaml
meta:
  id: "VFR-001"
  description: "Basic VFR Departure to Pattern"
  difficulty: "Easy"

context:
  airport: "KSFO"
  aircraft: "N172SP (Cessna 172)"
  weather: "Wind 280 at 10, Visibility 10+"

steps:
  - id: 1
    action: "Initial Contact"
    telemetry:
      lat: 37.61
      lon: -122.37
      alt: 10
      speed: 0
      on_ground: true
    input_voice: "San Francisco Tower, Skyhawk 172SP, holding short runway 28L, ready for takeoff, remaining in the pattern."
    
    expectations:
      - type: regex
        value: "(RUNWAY|RWY) 28L"
        severity: critical
      - type: regex
        value: "CLEARED FOR TAKEOFF"
        severity: critical
      - type: regex
        value: "MAKE (LEFT|RIGHT) TRAFFIC"
        severity: warning
      - type: llm_judge
        prompt: "Did the ATC instruction include a specific departure crossover or pattern entry instruction?"
```

## 3. Implementation Plan

### Phase 1: The Runner (Red/Green Testing)

* **Tools**: Rust `cargo test`, `wiremock`.
* **Logic**:
    1. Parse YAML.
    2. Instantiate `stratus_core::AtcSession`.
    3. Mock the `OllamaClient` using `wiremock` to return pre-recorded LLM responses (determinism) OR forward to a live model (verification).
    4. Run assertions on the output string.

### Phase 2: The Judge (Compliance)

* **Tools**: `async-openai` (connecting to a "smart" model like GPT-4o or Llama3-70B).
* **Logic**:
  * For complex checks (e.g., "Was the tone professional?"), the runner sends the Transcript + Rules to the Judge LLM.
  * Judge returns `pass/fail` + reasoning.

## 4. Why this approach?

1. **Determinism**: By mocking the LLM response in Phase 1, we prove our *State Machine* (logic) works.
2. **Accuracy**: By using live LLMs in Phase 2, we prove the *Model* works.
3. **Safety**: We can strictly enforce "Safety Critical" phrases (e.g., "CLEARED TO LAND") using simple Regex, ensuring no hallucination omits them.

## 5. Roadmap

* **Step 1**: Implement `stratus-eval` skeleton.
* **Step 2**: Write `scenarios/basic_vfr.yaml`.
* **Step 3**: Use this harness to TDD the new VFR State Machine.
