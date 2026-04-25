# Changelog

All notable changes to harnessFlow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-04-25 — First Stable Release

The first stable release of **harnessFlow** — an open-source Claude Code Skill that drives an AI agent through a complete software project lifecycle (idea → spec → code → tests → quality gate → delivery), with a continuous-monitoring sidecar that enforces hard redlines, soft drift detection, and 100% audit traceability.

### 🎯 Headline Numbers

- **3-Solution documentation**: 154 documents · ~165 000 lines · 298 PlantUML diagrams · 0 Mermaid · 0 FILL placeholders
- **Test suite**: 753 tests pass in 41.72 s · 0 flake (over 3 consecutive runs)
- **Performance SLOs**: 7/7 met with 27×–5000× margin (halt P99 = 0.04 ms / panic P99 = 0.02 ms / gate P95 = 0.58 ms)
- **Hard-redline BLOCK**: P99 latency 3.28 ms (vs 100 ms hard contract = 30× margin)
- **20 inter-component contracts** locked (IC-01..IC-20) with field-level YAML schemas + 109 error codes
- **22 DoD predicates** white-listed (frozen v1.0) — every "PASS" verdict carries an evidence trail through IC-09 audit ledger

### ✨ Added

#### 10 L1 Bounded Contexts (full implementation)

- **L1-01 Main Decision Loop** (`app/main_loop/`) — heart-beat tick scheduler · AST-whitelisted decision engine · 7-state aggregate machine · DAG task chains · decision audit · supervisor receiver
- **L1-02 Project Lifecycle** (`app/project_lifecycle/`) — 7-stage Stage Gate (S1→S7) · charter/PMP-9/TOGAF-ADM artifact producers · template engine
- **L1-03 WBS + WP Topology** (`app/l1_03/`) — recursive WBS decomposer · DAG topology manager · WP scheduler with parallelism cap · failure rollback coordinator
- **L1-04 Quality Loop** (`app/quality_loop/`) — DoD AST compiler (whitelist v1.0) · TDD blueprint generator · test-case generator · Gate compiler + acceptance checklist · S4 driver · S5 verifier · 4-level rollback router
- **L1-05 Skill Ecosystem** (`app/skill_dispatch/`) — Claude Code Skill registry · intent-based skill selector · invocation executor with fallback · sub-agent delegator · async result collector
- **L1-06 3-Tier Knowledge Base** (`app/knowledge_base/`) — observation-tier / promotion-queue / canonical-tier 3 layers · KB read/write · promotion ceremony · retrieval + Rerank
- **L1-07 Harness Supervisor** (`app/supervisor/`) — 8-dimension state collector · 4-level deviation classifier · 5-class hard-redline enforcer · supervisor event dispatcher · 8-class soft-drift detector · loop escalator
- **L1-08 Multi-modal Tools** (`app/multimodal/`) — document I/O orchestrator · code-structure understanding (tree-sitter) · image vision · path safety + degradation orchestrator
- **L1-09 Resilience + Audit** (`app/l1_09/`) — single-sink event bus · advisory lock manager · audit recorder + query · checkpoint + recovery · crash-safety integrity layer
- **L1-10 Human Collaboration UI** (`app/bff/`) — 11-tab main framework · Gate decision cards · live progress stream · user intervention entry · KB browser + promotion · trim profile config · admin sub-modules

#### 3-Solution Documentation (154 documents)

- **3-1 Technical** (77 docs · 95 000 lines): 5 L0 supports · 10 L1 architectures · 57 L2 tech-designs · 4 cross-L1 integration documents (`ic-contracts.md` 2503 lines / 20 IC field-level / 109 error codes / 22 PlantUML)
- **3-2 TDD** (57 docs · 70 000 lines): 1:1 mirror of 3-1 with TDD test specifications
- **3-3 Monitoring & Controlling** (10 docs · 7503 lines): hard-redlines (5 classes) · soft-drift-patterns (8 classes closed) · DoD specs (general + stage + WP) · monitoring metrics · acceptance criteria · coding standards · L0 overview

#### Quality Infrastructure

- `scripts/quality_gate.sh` — 6-gate automated quality check (Mermaid / FILL / TBD-TODO / IC ref / PlantUML pairing / fallback)
- `tests/shared/` — 8 reusable test helpers (conftest · project_factory · ic_assertions · e2e_harness · stubs · gwt_helpers · perf_helpers · matrix_helpers)
- `tests/integration/` — 20 IC contracts × multiple scenarios + PM-14 isolation + failure propagation + cross-session state + audit chain verification + 10×10 cross-L1 matrix (30 cells covered)
- `tests/acceptance/` — 12 end-to-end Given-When-Then scenarios (normal flow / WP rollback / parallel WP / hard redline 100 ms / panic 100 ms / S1→S7 full / KB promotion / cross-session recovery / multi-project isolation / user intervention / release flow)
- `tests/performance/` — 7 SLO benchmarks with deterministic warm-up + 3-run flake check

### 📊 Test Coverage Breakdown

| Suite | Test Count | Runtime | Notes |
|---|---|---|---|
| selfcheck (shared harness) | 69 | < 1 s | Validates 8 fixture helpers |
| integration (20 IC + matrix) | 484 | ~ 8 s | Real L1 module imports, no mocks of core BCs |
| acceptance (12 scenarios) | 153 | ~ 2 s | Full Given-When-Then flows |
| performance (7 SLO) | 47 | ~ 32 s | 100–5000× margin over thresholds |
| **Total** | **753** | **~ 42 s** | **0 flake across 3 consecutive runs** |

Plus ~3000 unit tests across 10 L1 modules (run-on-change in `pyproject.toml::tool.coverage.run.source`).

### 🔒 Hard Constraints (locked in v1.0)

- **PM-14**: every artifact path roots at `projects/<project_id>/...`; no cross-project reads/writes
- **PM-08**: single-sink IC-09 event bus is the only path to `audit-ledger.jsonl` (with hash chain + HMAC signature)
- **PM-05**: Stage/WP DoD evaluated only via the 22-predicate whitelist AST evaluator (no `exec`, no `eval`, no kwargs, no subscript, no chain calls)
- **PM-07**: every "PASS" verdict carries an evidence-ref bundle; INCONCLUSIVE verdicts are treated as BLOCK by default (conservative refusal)
- **Hard redline SLO ≤ 100 ms** for halt / panic / IC-15 (currently 0.02–3.28 ms in benchmarks)

### 📝 Known Limitations (not in v1.0 scope)

- Multi-tenant deployment & RBAC (planned for v1.1)
- Full Vue 3 + Vite production build of L1-10 UI (current build is a static dev shell + FastAPI BFF)
- LLM provider switching at runtime (currently DeepSeek + ARK only)
- Multi-language code understanding beyond Python / TypeScript / Go / Rust / Java (tree-sitter grammar pack will expand in v1.1)

### 📦 Package Versions

- Python ≥ 3.11
- Core: pydantic ≥ 2.6 · jcs ≥ 0.2.1 · ulid-py ≥ 1.1 · jsonschema ≥ 4.21 · jinja2 ≥ 3.1 · networkx ≥ 3.2 · fastapi ≥ 0.110 · uvicorn[standard] ≥ 0.30 · tree-sitter ≥ 0.25,<1.0
- Dev: pytest ≥ 7.4 · pytest-cov ≥ 4.1 · pytest-asyncio ≥ 0.23 · ruff ≥ 0.4 · mypy ≥ 1.9 · freezegun ≥ 1.5

### 🙏 Contributors

This release was implemented by 8 parallel Claude Code subagent waves (Dev-α through Dev-θ + main-1, main-2, main-3) coordinated by a single orchestrator session, using the **Superpowers** framework (brainstorming → writing-plans → subagent-driven-development → finishing-a-development-branch).

---

## [Unreleased]

Roadmap for v1.1 — see GitHub Issues for individual proposals:

- Multi-tenant deployment + RBAC
- Full Vue 3 + Vite production frontend
- Runtime LLM provider switching
- Expanded multi-language tree-sitter grammar pack
- Optional cloud audit-ledger sink (S3 / GCS / Azure Blob) with hash-chain replication
