# Stratus ATC - Session Handoff (January 2, 2025)

## Session Summary

This session completed a **full codebase scrub** to remove legacy cloud references and rebrand the X-Plane plugin.

### Completed Tasks

#### 1. Dead Code Removal ✅

- Deleted `client/src/core/sapi_interface.py` (820 lines of dead cloud API code)
- Deleted `client/src/core/providers/cloud.py`
- Deleted `sidecar.py` (cloud telemetry forwarder)
- Deleted 50+ test/debug files targeting external APIs
- Deleted obsolete documentation (`LOCAL_VS_CLOUD.md`, `SAPI_FINDINGS.md`)

#### 2. Plugin Rebranding ✅

- Renamed plugin: `SayIntentionsAIml` → `StratusATC`
- Updated source: `stratus_plugin.c`
- Updated CMakeLists.txt
- New data directory: `~/.local/share/StratusATC/`
- New log file: `stratus_atc.log`

#### 3. Documentation Updates ✅

- Rewrote `ASSESSMENT_AND_ROADMAP.md`
- Rewrote `PROJECT_STATUS.md`

---

## Architecture Reminders

### Brain vs Motor Separation

- **Stratus (Client)**: All ATC logic, prompts, telemetry tracking.
- **speechserverdaemon**: TTS/STT/LLM engine (do NOT modify from Stratus context).

### Key Files

| File | Purpose |
|:-----|:--------|
| `client/src/ui/main_window.py` | Main GUI, `build_atc_prompt`, settings persistence |
| `client/src/ui/settings_panel.py` | Settings UI including Identity Overrides |
| `adapters/xplane/src/stratus_plugin.c` | X-Plane C plugin (telemetry export) |
| `client/src/core/sim_data.py` | Telemetry reading from JSON files |

---

## Next Steps (Suggested)

1. **Voice Input (Phase 3)** - Whisper STT, PTT hotkey binding
2. **Sim Control (Phase 4)** - Parse AI responses to control aircraft
3. **Frequency Validation** - ATC silent if pilot on wrong frequency
4. **Packaging** - AppImage/deb for distribution

---

## Test Commands

```bash
# Run the client
cd /home/startux/Code/Stratus && python client/src/main.py

# Run tests
cd /home/startux/Code/Stratus && PYTHONPATH=. pytest tests/

# Check X-Plane plugin logs
tail -f ~/.local/share/StratusATC/stratus_atc.log
```

---

## Git Status

All changes are local. Commit with:

```
refactor: Remove legacy cloud code, rebrand plugin to StratusATC

- Deleted cloud provider code (sapi_interface.py, cloud.py, sidecar.py)
- Deleted 50+ debug/test files targeting external APIs
- Renamed X-Plane plugin: SayIntentionsAIml → StratusATC
- Updated data directory: ~/.local/share/StratusATC/
- Rewrote ASSESSMENT_AND_ROADMAP.md and PROJECT_STATUS.md
- Stratus is now fully local-only (Ollama + speechd-ng)
```
