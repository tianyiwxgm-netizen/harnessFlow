# Contributing to harnessFlow

Thank you for considering contributing to harnessFlow! This document outlines the contribution workflow.

## TL;DR

1. Read the [3-Solution documentation](docs/3-1-Solution-Technical/) — every change must trace back to a contract in `docs/3-1-Solution-Technical/integration/ic-contracts.md` or a DoD predicate in `docs/3-3-Monitoring-Controlling/dod-specs/general-dod.md`.
2. Open an issue first for non-trivial changes.
3. Branch from `main` · keep PRs ≤ 400 lines diff (excluding tests/docs).
4. All tests must pass: `pytest tests/` · 753 E2E TC + module unit tests.
5. `bash scripts/quality_gate.sh` must PASS (no Mermaid · no FILL · PlantUML pairing OK).
6. Conventional commit message: `feat/fix/refactor/test/docs(scope): summary`.

## Setup

```bash
git clone https://github.com/<your-fork>/harnessFlow.git
cd harnessFlow
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify environment
pytest tests/shared -v   # 69 selfcheck tests, < 1s
bash scripts/quality_gate.sh
```

## Architecture Constraints (Hard)

- **PM-14**: every artifact path must root at `projects/<project_id>/...`. No cross-project read/write.
- **PM-08**: never write to `audit-ledger.jsonl` directly — always go through the IC-09 single-sink event bus (`app.l1_09.event_bus`).
- **PM-05**: DoD expressions only use the 22-predicate whitelist (`docs/3-3-Monitoring-Controlling/dod-specs/general-dod.md §2.2`). Adding a new predicate requires an ADR + whitelist version bump.
- **PM-07**: every `verdict=PASS` must carry `evidence_ref` linking to evidence YAML. Missing → INCONCLUSIVE → defaults to BLOCK.
- **Hard redline SLO ≤ 100 ms** for halt / panic / IC-15 (current benchmark: 0.02–3.28 ms).

## Workflow

### 1. Open an issue

For features: describe the use case + which IC contract (IC-XX) it touches. For bugs: include reproduction steps + expected vs. actual.

### 2. Branch + commit

```bash
git checkout -b feat/<short-name>
# … make changes …
git add <specific files>   # never `git add -A` — protects against committing secrets
git commit -m "feat(<scope>): summary

Why: …
Impact: …"
```

### 3. Test locally

```bash
# Unit + integration + acceptance + perf
pytest tests/ -v --tb=short

# Lint + type check
ruff check app/ tests/
mypy app/

# Documentation gate (Mermaid / FILL / PlantUML pairing)
bash scripts/quality_gate.sh
```

### 4. Open a PR

- Title: same as commit summary
- Body must include:
  - **What**: 1-3 sentence description
  - **Why**: link to the issue or describe the user-facing motivation
  - **Test plan**: what new tests cover · how reviewer can verify
  - **IC impact**: list IC-XX contracts touched, if any
- Push & open PR; CI will run lint + 4 test suites + quality-gate + skill packaging
- Tag a maintainer when CI is green

## Test Categories

| Suite | What | Target |
|---|---|---|
| `tests/shared/_selfcheck/` | Validates the 8 helper modules | `< 1s` |
| `tests/integration/ic_XX/` | One folder per IC contract | each `< 5s` |
| `tests/integration/matrix/` | 10×10 cross-L1 matrix | each row `< 1s` |
| `tests/integration/pm14_isolation/` | PM-14 root cross-project rejection | `< 1s` |
| `tests/integration/failure_propagation/` | Cross-L1 failure cascade | `< 2s` |
| `tests/integration/cross_session_state/` | Crash recovery | `< 3s` |
| `tests/acceptance/scenario_NN_*/` | Full Given-When-Then user flows | each `< 1s` |
| `tests/performance/` | 7 SLO benchmarks | `~ 32s` |

## Documentation Update Rules

- Changing an IC contract → update `docs/3-1-Solution-Technical/integration/ic-contracts.md` + corresponding consumer/producer L2 tech-design + 3-2 TDD mirror
- Changing a DoD predicate → update `docs/3-3-Monitoring-Controlling/dod-specs/general-dod.md` + L2-02 `WHITELIST_V1_0` frozen set + bump `whitelist_version`
- Changing a hard redline → update `docs/3-3-Monitoring-Controlling/hard-redlines.md` + L2-03 `pattern_db` + L2-03 tests
- All diagrams must use **PlantUML** (`@startuml/@enduml`) — Mermaid is prohibited (caught by Gate 1)

## Code Style

- `ruff` line-length = 110, target Python 3.11
- `mypy` warn_return_any + warn_unused_configs
- File length ≤ 600 lines (soft drift rule #1)
- Function ≤ 80 lines (soft drift rule #2)

## License

By contributing, you agree that your contributions will be licensed under the MIT License (see `LICENSE`).
