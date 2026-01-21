# Stratus ATC Guardrails Requirements

> These are NON-NEGOTIABLE requirements. Code that violates these MUST NOT be merged.

## 1. AIAM: Agent Governance

### No-Touch Zones

- **FORBIDDEN:** Modifying or deleting system binaries (e.g., `/usr/bin/`, `/home/startux/.local/bin/`).
- **FORBIDDEN:** Modifying X-Plane installation files outside `Output/plugins/StratusATC/`.

### Action Risk Tiers

| Tier | Risk Level | Examples |
|:-----|:-----------|:---------|
| **T0** | Safe | Read-only, linting, UI state, `view_file` |
| **T1** | Normal | Incremental code edits, new feature files, test additions |
| **T2** | High-Risk | Dependency changes (`Cargo.toml`), API changes, schema changes |
| **T3** | Restricted | File DELETIONS, binary changes, system config, X-Plane SDK updates |

### Mandatory Verification (EV)

- **REQUIRED:** Before T2/T3 actions, agents MUST use `view_file` or `ls -l` to verify current state.
- **REQUIRED:** All T3 actions must be logged with a `justification` in the audit log.

---

## 2. Input Validation (Rust)

### LLM Response Validation

```rust
// REQUIRED: Validate Ollama responses before TTS
if response.trim().len() < 3 {
    warn!("Empty or invalid LLM response, skipping TTS");
    return;
}

// REQUIRED: Sanitize unexpected contents
if response.contains("<|") || response.contains("```") {
    warn!("LLM response contains markup, cleaning...");
    // clean_llm_response(response)
}
```

### Telemetry Validation

```rust
// REQUIRED: Validate telemetry before prompt injection
fn validate_telemetry(data: &Telemetry) -> bool {
    data.latitude != 0.0 && data.longitude != 0.0
}
```

---

## 3. Output Validation

### Destructive Action Confirmation

```rust
// REQUIRED: High-risk sim control commands need parsing checks
const DANGEROUS_COMMANDS: &[&str] = &["emergency", "mayday", "squawk 7700"];
if DANGEROUS_COMMANDS.iter().any(|&cmd| response.to_lowercase().contains(cmd)) {
    // Flag for confirmation manually
    warn!("Dangerous command detected in LLM response");
}
```

---

## 4. Error Handling

### No Silent Failures

```rust
// FORBIDDEN:
let _ = send_to_ollama(prompt);

// REQUIRED:
if let Err(e) = send_to_ollama(prompt).await {
    error!("Ollama request failed: {}", e);
}
```

### Timeout Handling

```rust
// REQUIRED: Handle LLM cold-start timeouts gracefully
use tokio::time::timeout;
match timeout(Duration::from_secs(30), ollama.generate(prompt)).await {
    Ok(result) => handle(result),
    Err(_) => warn!("LLM response timed out after 30s"),
}
```

---

## 5. Async Safety (Rust/Tokio)

### No Blocking in Async

```rust
// FORBIDDEN: Blocking calls in async context
let status = std::process::Command::new("ls").status()?;

// REQUIRED: Use tokio::process or spawn_blocking
tokio::process::Command::new("ls").status().await?;
```

### File I/O in Async

```rust
// REQUIRED: Use tokio::fs for file operations
use tokio::fs;
let telemetry = fs::read_to_string(TELEMETRY_INPUT_PATH).await?;
```

---

## 6. X-Plane Plugin Safety

### Plugin Boundaries

```c
// REQUIRED: Plugin must not crash X-Plane on failure
if (json_file == NULL) {
    XPLMDebugString("StratusATC: Failed to open telemetry file, skipping write\n");
    return;  // Graceful degradation, NOT a crash
}
```

### DataRef Access

```c
// REQUIRED: Validate DataRefs before use
XPLMDataRef alt_ref = XPLMFindDataRef("sim/flightmodel/position/elevation");
if (alt_ref == NULL) {
    XPLMDebugString("StratusATC: elevation DataRef not found\n");
    return;
}
```

---

## Summary: Critical Invariants

1. **ZERO PYTHON**: Do not introduce new Python dependencies.
2. **Validate all telemetry** before injecting into prompts.
3. **Handle 30s LLM timeouts** without freezing the UI.
4. **No silent failures** - every error path must be logged.
5. **Plugin must not crash X-Plane** - graceful degradation only.
