# Tiny Canary Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the existing weather paper profit candidate through deterministic offline readiness gates to `TINY_CANARY_READY_FOR_MANUAL_ARMING` without enabling live trading, authentication, signing, order transmission, or cancellation.

**Current continuation note:** Later PR #55 work extended this original Sequence 55 plan into canary-grade crypto spot, money-worthy proof, autonomous no-transmit rehearsal, independent fresh-worktree proof, and final human-governed armability review under `reports/canary_grade_live_sim/**`. Treat those later lanes as a continuation of the same safety boundary, not as weather Sequence 55 output.

**Done rule update:** Before marking any high-stakes task in this plan or its continuation as done, validate it with an adversarial subagent review. Resolve Critical or Important findings, and record the review outcome in the generated report or final response.

**Portfolio margin note:** Tiny canary review remains spot-only and cash-only. Portfolio margin, cross-collateral, leverage, shorting, futures, perps, options, portfolio checks, and account-balance checks must remain disabled unless a later human-owned plan explicitly changes the safety model.

**Architecture:** Add Sequence 55 gate modules that read the existing profit campaign and weather Sequence 52 reports, produce gate-specific JSON/Markdown reports under `reports/canary_readiness`, and keep a resumable `latest_state`. Execution-facing gates emit only unsigned local intent previews and ledger placeholders with explicit no-send flags.

**Tech Stack:** Python, Typer CLI, pytest, existing Quant OS reports, `make.cmd` smoke targets.

---

### Task 1: Sequence 55 Tests

**Files:**
- Create: `tests/test_sequence55_tiny_canary_readiness.py`

- [ ] **Step 1: Write failing tests**

Cover the required audit, lineage, replay, robustness, cost/fill, shadow, dry-run, risk, kill-switch, reconciliation, manual packet, final readiness, forbidden-path, CLI, and make target behavior.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sequence55_tiny_canary_readiness.py -q`

Expected: fail because Sequence 55 modules and CLI commands do not exist yet.

### Task 2: Gate Implementations

**Files:**
- Create: `src/quant_os/readiness/canary_readiness_common.py`
- Create required gate modules under `src/quant_os/readiness`, `src/quant_os/proving`, `src/quant_os/execution`, and `src/quant_os/risk`

- [ ] **Step 1: Implement minimal deterministic gates**

Each gate reads local artifacts, enforces no-live safety flags, writes its required report, and updates `reports/canary_readiness/state/latest_state.*`.

- [ ] **Step 2: Run Sequence 55 tests**

Run: `python -m pytest tests/test_sequence55_tiny_canary_readiness.py -q`

Expected: pass.

### Task 3: CLI And Smoke Targets

**Files:**
- Modify: `src/quant_os/cli.py`
- Modify: `make.cmd`

- [ ] **Step 1: Add CLI commands**

Add the requested `readiness`, `proving`, `execution`, and `risk` commands with local imports.

- [ ] **Step 2: Add make targets**

Add `canary-readiness-smoke` and `sequence55-smoke`, both fixture-safe and no-network.

- [ ] **Step 3: Run CLI smoke**

Run: `.\make.cmd sequence55-smoke`

Expected: pass without credentials, network, or live order authority.

### Task 4: Final Verification And Reporting

**Files:**
- Reports under `reports/canary_readiness/**`

- [ ] **Step 1: Generate all gate reports**

Run each Sequence 55 CLI command in order.

- [ ] **Step 2: Run required validation**

Run requested smoke, lint, guard-live, freqtrade validate, and diff checks.

- [ ] **Step 3: Push draft PR if validation is safe**

Preserve prior Phase 53 work, keep live defaults disabled, and publish the Sequence 55 branch as a draft PR.
