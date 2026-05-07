# External Repo Synthesis

This synthesis records what QuantOS should borrow from external benchmark repositories and what it should explicitly avoid. It is grounded in the repo's first principle: QuantOS is a local-first autonomous QuantOps factory where deterministic code owns validation, replay, OMS/PMS state, routing, sizing, exits, reconciliation, risk, kill switch, and live gating. AI remains support-only.

Live execution stays default-off. This tranche adds source provenance, read-only manifests, and benchmark reporting. It does not add signing, wallet authority, order posting, order cancellation, market making, copy trading, or prediction-market execution.

## Consensus

The highest-value overlap across the useful repos is not more autonomous trading. It is:

1. A source registry that separates source integration from downstream consumers.
2. Cache-first local manifests with provenance, licensing caveats, and schema notes.
3. Event-driven replay boundaries that can later consume realistic orderbook/trade inputs.
4. Research reports that force baseline, calibration, walk-forward, robustness, and cost evidence before live progression.
5. Skill/instruction separation where AI can research, critique, summarize, and plan, but cannot cross deterministic execution boundaries.

## Borrow / Ignore Matrix

| Repo | Borrow | Ignore | QuantOS mapping | Layers |
| --- | --- | --- | --- | --- |
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) | Provider/source separation, connect-once consume-everywhere mindset, downstream-neutral data layer. | Broad terminal scope, licensed-provider sprawl, AGPL code copying, workspace/backend/API-server expansion, and AI-agent platform direction. | `source_registry.py` records OpenBB as reference-only and turns the architectural idea into a small registry/report. | data, operator/report |
| [Qlib](https://github.com/microsoft/qlib) | Research workflow discipline, benchmark configs, loose-coupled components, cost-aware analysis. | Full ML platform adoption, online serving, auto-quant/R&D-agent breadth, RL/live execution expansion, and production order-execution scope. | Lane report prioritizes benchmark/replay/robustness before strategy proliferation. | calibration/research |
| [vn.py](https://github.com/vnpy/vnpy) | Modular engine and plugin boundaries. | Broker gateway expansion and live connectivity. | Use as a reminder to keep data, replay, OMS/PMS, risk, and reports separately testable. | replay |
| [LEAN](https://github.com/QuantConnect/Lean) | Event-driven architecture, pluggable components, realistic engine boundaries. | Live deployment commands, Docker-heavy runtime direction, broad asset integration. | Reinforces event replay realism and deterministic execution boundaries. | replay, calibration/research |
| [yfinance](https://github.com/ranaroussi/yfinance) | Optional public read-only reference data and explicit terms caveats. | Treating Yahoo data as production-grade or CI-required. | `yahoo_reference.py` inspects optional import availability and local fixtures only. | data, calibration/research |
| [machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading) | Feature engineering discipline, ML workflow, backtest pitfalls, event-driven vs vectorized backtest framing. | Notebook zoo structure, broad dependency sprawl, generic ML demonstrations. | Lane report favors calibration/walk-forward/robustness over new live shell. | calibration/research |
| [poly_data](https://github.com/warproxxx/poly_data) | Polymarket market/trade/order-filled schema ideas and provenance thinking. | GPL implementation copying, live fetching as CI dependency. | Registry marks it reference-only; future work can compare local schemas. | data, replay |
| [PMXT](https://github.com/pmxt-dev/pmxt) | Unified prediction-market data concepts and orderbook archive candidate manifests. | Trading-capable API usage, MCP/live-agent direction, venue action abstraction. | `pmxt_manifest.py` reads local manifests only and flags PMXT as live-capable but unauthorized. | data, replay |
| [py-clob-client](https://github.com/Polymarket/py-clob-client) | Clean distinction between unauthenticated public market-data paths and L1/L2 signing/order paths. | Private keys, API credential derivation, order creation, posting, cancellation, allowances, and any credentialed trade/user-order flow. | Registry and `polymarket_public.py` allow public market/book inspection only. | data, replay |
| [prediction-market-analysis](https://github.com/Jon-Becker/prediction-market-analysis) | Pre-collected market/trade archives, parquet storage, resumable collection pattern, schema docs. | Large downloads in CI, interactive download/setup, treating datasets as live authority. | `reference_datasets.py` reads local dataset manifests only. | data, calibration/research |
| [Polymarket_data](https://github.com/SII-WANGZJ/Polymarket_data) | Large cleaned Polymarket tables, market metadata linkage, unified YES-perspective research data. | Committing 100GB+ datasets, direct blockchain sync in this tranche, live trading from user tables. | Offline-cache-only registry entry and manifest reader. | data, calibration/research |
| [polymarket-cli](https://github.com/Polymarket/polymarket-cli) | Command taxonomy as a boundary reference. | Wallet/order convenience commands and authority-blurring operator flows. | Registry labels it live-capable reference-only; no CLI dependency is added. | data, operator/report |
| [prediction-market-backtesting](https://github.com/evan-kolberg/prediction-market-backtesting) | Prediction-market replay realism, staged caches, orderbook deltas, fee/slippage/latency/limits caveats. | Heavy Nautilus adoption, account-ledger copy-trading, live or exact wallet replay assumptions. | Lane report elevates local manifests and replay realism as next work. | replay, calibration/research, operator/report |

## Selective Pattern Only

| Repo | Borrow | Ignore | QuantOS mapping | Layers |
| --- | --- | --- | --- | --- |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Role separation vocabulary, opt-in checkpoint/resume shape, and persistent decision-log concept. | Multi-agent trading as alpha, agent-directed execution, broad autonomous framework, and reflective memory as a trading signal. | Keep AI roles as research/critique/report helpers only; any checkpoint or decision log must be deterministic, auditable, and non-executing. | skills/instructions |
| [scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | Skill packaging and scoped instruction bundles. | Massive skill catalog or tool sprawl. | Future skills should be narrow, testable, and authority-limited. | skills/instructions |
| [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | Financial NLP and sentiment as support-only research input. | LLM-as-trader framing, robo-advisor authority, speculative return claims. | AI may summarize/classify, not size or execute. | skills/instructions, calibration/research |
| [lightweight-charts](https://github.com/tradingview/lightweight-charts) | Future lightweight operator/report visualization. | UI work in this tranche. | Optional later charts for reports after data/replay improves. | operator/report |
| [AKShare](https://github.com/akfamily/akshare) | Source catalog mindset and explicit academic-use caveats. | Regional API sprawl and unstable scraping endpoints. | Use as a reminder to record source terms and caveats. | data |
| [awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | Curation checklist across data, backtesting, risk, visualization. | Runtime architecture or package shopping. | Helps categorize future research candidates. | operator/report |
| [Finance](https://github.com/shashankvemuri/Finance) | Educational examples for basic finance/data workflows. | Standalone script style as architecture. | Reference only; no runtime mapping. | calibration/research |

## Mostly Ignore

| Repo | Why not imitate | QuantOS boundary |
| --- | --- | --- |
| [Polymarket/agents](https://github.com/Polymarket/agents) | Autonomous AI agents, private key setup, and trade scripts conflict with support-only AI. | No AI direct live order authority. |
| [poly-maker](https://github.com/warproxxx/poly-maker) | Market-making bot path assumes liquidity provision before evidence. | No market-making as assumed-profit path. |
| [Polyseer](https://github.com/yorkeccak/Polyseer) | Product/assistant alpha direction broadens scope. | Focus stays data/replay/research. |
| [PolymarketBTC15mAssistant](https://github.com/FrondEnt/PolymarketBTC15mAssistant) | Real-time trading assistant framing is premature. | No prediction-market execution authority. |
| [trump-code](https://github.com/sstklen/trump-code) | Social/news signal claims and script sprawl are not a robust QuantOps spine. | No speculative profitability claims. |
| [500-AI-Agents-Projects](https://github.com/ashishpatel26/500-AI-Agents-Projects) | Generic agent catalog does not improve data validation, replay, calibration, or risk. | Avoid bot zoo direction. |
| [maybe](https://github.com/maybe-finance/maybe) | Archived consumer personal-finance app architecture is unrelated. | No consumer finance product pivot. |
| [union](https://github.com/unionlabs/union) | ZK bridge / DeFi interoperability architecture widens security surface and does not help research evidence. | No DeFi runtime direction. |

## Layer Placement

### Data Layer

Implement now:

- Read-only source registry with provenance, license caveats, safety classifications, and live-capable package flags.
- Optional-import adapters that degrade gracefully when external packages are missing.
- Local manifest readers for prediction-market public snapshots, PMXT archive candidates, and reference datasets.

Do not implement now:

- Internet-required CI.
- Paid data dependencies.
- Wallet, signing, or authenticated user-trade ingestion.
- Large dataset downloads.

### Replay Layer

Implement next:

- Convert local prediction-market orderbook/trade manifests into normalized replay candidates.
- Add venue-specific caveats for spread, depth, queue position, latency, fills, fees, and resolution.

Do not implement now:

- Prediction-market order posting.
- Copy-trading or wallet activity replay as executable signals.
- Market-making loops.

### Calibration / Research Layer

Implement next:

- Baselines, placebo comparisons, walk-forward splits, cost penalties, robustness reports, and dataset quality scores for any new lane.
- Conservative lane selection that compares crypto runtime proving against prediction-market read-only research.

Do not implement now:

- Profitability claims from source availability.
- New strategy families without out-of-sample and cost evidence.

### Skills / Instructions Layer

Implement later if needed:

- Narrow research, critique, and reporting skills.
- Explicit support-only AI roles.

Do not implement:

- Multi-agent trading frameworks.
- LLM-directed sizing, exits, order placement, risk override, or kill-switch bypass.

### Operator / Report Layer

Implement now:

- CLI reports for registry and external benchmark lane selection.
- Markdown/JSON reports under `reports/external_benchmarks`.

Implement later:

- Lightweight visualizations after the data/replay layer has enough stable artifacts.

## Tranche Outcome

This tranche should make QuantOS better at deciding what to ingest, why it is allowed, how it is licensed/caveated, and where it can safely feed research. It improves the path to future profitability by reducing source ambiguity and replay fantasy before adding strategy or live surface area.
