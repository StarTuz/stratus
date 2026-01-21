# Decision Record: SpeechD-NG Adoption

**Date:** January 2026
**Status:** Deferred

## Context

We investigated `speechd-ng` as a potential replacement for our audio/AI stack. It functions as a D-Bus orchestrator that can route queries to BitNet or Ollama servers.

## Decision

**We will NOT adopt speechd-ng in the current "Repair" phase.**

## Rationale

1. **Priority**: The critical flaw in Stratus is the "Brain" (Logic/State), not the "Mouth" (Audio). Replacing audio infrastructure now would distract from fixing the hallucinations.
2. **Complexity**: Adopting it requires users to install an external daemon, increasing setup friction before we have a working MVP.
3. **Inference**: It does not solve the inference problem itself; we still need to manage the underlying LLM server.

## Future Trigger

We will revisit this decision when:

* The VFR State Machine is robust and working.
* We look to package the application (AppImage/Flatpak), where `speechd-ng` could simplify audio dependencies.
