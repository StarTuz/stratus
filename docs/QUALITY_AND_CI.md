# Stratus ATC — Quality and CI/CD

This document describes our quality bar and how CI/CD enforces it. We treat this as a **top-tier engineering** project: every push and PR is checked automatically, and contributors are expected to meet the same bar locally.

---

## 1. Quality principles

1. **No broken main**: The default branch must always build, pass tests, and pass lint.
2. **Deterministic tests**: Unit tests and the mock-only scenario suite must be fully deterministic (no flake).
3. **Explicit over implicit**: Format and lint are configured in-repo; CI runs the same commands as contributors.
4. **Security awareness**: Dependencies are audited (e.g. `cargo audit`); known-vulnerable deps are addressed.

---

## 2. CI pipeline (GitHub Actions)

**Workflow file**: `.github/workflows/ci.yml`

**Triggers**: Push and pull requests to `main` / `master`.

| Job       | What it does |
|----------|----------------|
| **check** | `cargo fmt --all -- --check`, then `cargo clippy --all-targets --all-features -- -D warnings`. Fast feedback on style and lint. |
| **test**  | `cargo build --release`, then `cargo test`. Ensures the workspace builds and all unit tests pass. |
| **eval**  | Builds `stratus-eval`, then runs it with `STRATUS_EVAL_MOCK_ONLY=1`. Runs all non-BIT scenarios with mocked LLM; regex and state expectations are enforced. No Ollama or BitNet required. |
| **audit**  | Runs `cargo audit` in `stratus-rs`. Currently `continue-on-error: true` so advisories don’t block merge; fix reported advisories in follow-up PRs and switch to blocking once the baseline is clean. |

All jobs use Cargo cache keyed by `Cargo.lock` and `**/Cargo.toml` for faster runs.

---

## 2b. Qodo Merge (PR Agent)

**Workflow**: `.github/workflows/pr_agent.yml`  
**Config**: `.pr-agent.toml`

[Qodo](https://github.com/qodo-ai/pr-agent) runs on push to `main`/`master`, on PR open/reopen/sync, and on issue comments that use PR Agent commands. It provides:

- **Automated PR review**: AI review focused on ATC logic, safety (GUARDRAILS), FFI/unsafe, and Rust quality.
- **PR description**: Suggests descriptions using conventional commits (`feat:`, `fix:`, etc.).
- **Comment commands** (on PRs, by OWNER/MEMBER/COLLABORATOR): `/review`, `/describe`, `/improve`, `/ask`, `/summarize`.

**Setup**: Add an **`OPENAI_KEY`** repository secret (Settings → Secrets and variables → Actions) for the action to call the AI. Without it, the workflow may run but review/description steps will not succeed.

**Customization**: Edit `.pr-agent.toml` to change `ignore_pr_source_files`, `pr_reviewer.extra_instructions`, or `pr_description.extra_instructions`.

---

## 3. Local quality checklist (before PR)

1. **Format**: `cargo fmt --all` (from `stratus-rs`).
2. **Lint**: `cargo clippy --all-targets --all-features -- -D warnings`.
3. **Tests**: `cargo test`.
4. **Scenarios (mock-only)**: `STRATUS_EVAL_MOCK_ONLY=1 cargo run --release -p stratus-eval`.

Optional for ATC/phraseology changes:

5. **Full scenarios**: `cargo run --release -p stratus-eval` with Ollama (and optionally BitNet) available.

See **CONTRIBUTING.md** for full development and PR workflow.

---

## 4. Scenario suite (stratus-eval)

- **Purpose**: Regression and correctness of ATC logic (state machine, command parsing, phraseology) against FAA-style expectations.
- **Format**: YAML files in `stratus-rs/stratus-eval/scenarios/`. Each scenario has steps with telemetry, optional pilot input, mocked LLM response, and expectations (regex, state, llm_judge).
- **Mock-only mode** (`STRATUS_EVAL_MOCK_ONLY=1`):
  - Skips `llm_judge` expectations (no live Ollama).
  - Skips scenarios whose `meta.id` starts with `BIT-` (BitNet-only).
  - Used in CI and for quick local regression.
- **Full mode**: Runs all scenarios; `llm_judge` steps require Ollama; BIT-* scenarios require BitNet.

Design details: **docs/TEST_HARNESS_DESIGN.md**.

---

## 5. Dependency and security

- **Audit**: CI runs `cargo audit` in `stratus-rs`. Resolve advisories in a timely manner; the aim is to make audit blocking once the baseline is clean.
- **Updates**: Keep dependencies up to date; test and run the full checklist after upgrading.

---

## 6. Branch protection (recommended)

For repositories where you have admin access, we recommend:

- Require status checks for **check**, **test**, and **eval** before merge.
- Require at least one review for PRs targeting `main`/`master`.
- No force-push to the default branch.

Configure these in the repo’s **Settings → Branches → Branch protection rules**.

---

## 7. Testing the pipeline locally

Before pushing, run the same steps CI runs:

```bash
cd stratus-rs
cargo fmt --all -- --check && cargo clippy --all-targets -- -D warnings
cargo test
STRATUS_EVAL_MOCK_ONLY=1 cargo run --release -p stratus-eval
```

All four must pass. Then push (or open a PR) to trigger GitHub Actions and, on PRs, Qodo.

---

## 8. Future improvements

- **Release automation**: Tag-triggered workflow to build artifacts (e.g. Linux tarball, AppImage) and attach them to releases.
- **cargo-deny**: Add `deny.toml` for duplicate crates, banned crates, and license policy.
- **Strict audit**: Switch `cargo audit` to blocking once known advisories are cleared.
- **Benchmarks**: Optional benchmark job to track latency/throughput of critical paths.
