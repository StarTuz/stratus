# Contributing to Stratus ATC

We aim for **top-tier software engineering**: every change is reviewed, tested, and aligned with our quality bar. This document explains how to contribute and what we expect.

---

## 1. Development setup

### Prerequisites

- **Rust**: Latest stable (`rustup default stable`)
- **Linux**: Primary development target (Arch/Ubuntu/Fedora)
- **Tools**: `cmake`, `clang` (for X-Plane plugin); `speech-dispatcher` for TTS

### Clone and build

```bash
git clone https://github.com/StarTuz/stratus.git
cd stratus/stratus-rs
cargo build --release
```

### Run the stack

- **Voice service**: `cargo run --bin stratus-voice` (needs input device access for PTT)
- **GUI**: `cargo run --bin stratus-gui`
- **Scenario suite**: `cargo run -p stratus-eval` (optional: Ollama for `llm_judge` steps)

---

## 2. Quality gates (mandatory before PR)

All of the following **must** pass locally before you open or update a PR. CI will run the same checks.

### 2.1 Format

```bash
cd stratus-rs
cargo fmt --all
```

We use `rustfmt` with project settings in `stratus-rs/rustfmt.toml`. CI runs `cargo fmt --all -- --check`.

### 2.2 Lint

```bash
cd stratus-rs
cargo clippy --all-targets --all-features -- -D warnings
```

Fix all Clippy warnings. No exceptions for “style” unless the team explicitly agrees and documents it.

### 2.3 Unit tests

```bash
cd stratus-rs
cargo test
```

Every bugfix or behavior change should be covered by or aligned with tests.

### 2.4 Scenario regression (mock-only)

Deterministic ATC scenario tests without Ollama/BitNet:

```bash
cd stratus-rs
STRATUS_EVAL_MOCK_ONLY=1 cargo run --release -p stratus-eval
```

Use this before pushing to catch regressions in prompt/state/command logic.

### 2.5 Full scenario suite (optional, for ATC changes)

With Ollama running (`ollama serve`, plus a small model for the judge):

```bash
cargo run --release -p stratus-eval
```

This runs all scenarios including `llm_judge` and BIT-* (BitNet) scenarios. Not required for every PR but recommended when touching ATC behavior or phraseology.

---

## 3. Branching and PRs

- **Base branch**: `main` (or `master`). All changes land via pull/merge request.
- **Branch names**: Prefer `feature/description`, `fix/description`, or `docs/description`.
- **PR scope**: One logical change per PR. Keep diffs reviewable.
- **CI**: All CI jobs must be green before merge. Maintainers may request additional tests or docs.
- **Qodo**: PRs get an automated AI review (Qodo Merge). You can trigger `/review`, `/describe`, `/improve`, `/ask`, or `/summarize` in a PR comment. See **docs/QUALITY_AND_CI.md** (§ 2b).

---

## 4. Code and design standards

- **Rust**: Follow standard Rust idioms and the project’s existing style. Use the types and patterns already in the codebase where applicable.
- **Safety**: No new `unsafe` without a short comment justifying it. Prefer safe abstractions.
- **Documentation**: Document public APIs and non-obvious behavior. Update `README.md`, `PROJECT_STATUS.md`, or `docs/` when you change behavior or architecture.
- **Guardrails**: Respect `GUARDRAILS.md`. No changes that violate the no-touch zones or validation requirements.
- **Aviation domain**: For ATC phraseology or procedure logic, align with our references (e.g. `docs/PHRASEOLOGY_GUIDE.md`, `docs/ATC_REFERENCE.md`) and consider a quick sanity check with the documented personas (`TEAM_STRUCTURE.md`) if the change is subtle.

---

## 5. Testing expectations

- **Core/commands/ATC**: Changes to `stratus-core` (especially `atc.rs`, `commands.rs`) should add or update unit tests and/or scenario steps in `stratus-rs/stratus-eval/scenarios/`.
- **New features**: Prefer a short scenario or unit test that would fail without your change.
- **Regressions**: If you fix a bug, add a test that would have caught it (or extend an existing scenario).

---

## 6. CI pipeline reference

| Job        | Purpose                                      |
|-----------|-----------------------------------------------|
| **check** | `cargo fmt -- --check`, `cargo clippy`        |
| **test**  | `cargo build --release`, `cargo test`         |
| **eval**  | Scenario suite with `STRATUS_EVAL_MOCK_ONLY=1`|
| **audit** | `cargo audit` (advisory check; may be non-blocking) |

See `.github/workflows/ci.yml` for the exact commands and triggers.

---

## 7. Questions and governance

- **Issues**: Use GitHub issues for bugs, features, and design discussions.
- **Governance**: See `TEAM_STRUCTURE.md` for advisory roles and how we make decisions.
- **Legal**: This project is for **entertainment only**. See the disclaimer in `ASSESSMENT_AND_ROADMAP.md`.

Thank you for helping make Stratus ATC best-in-class.
