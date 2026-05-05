# Strategy Constitution

1. AI never places live orders.
2. Deterministic risk rules win over strategy output, optimizer output, alerts, reports, and AI suggestions.
3. The kill switch wins over everything.
4. No leverage first.
5. No options first.
6. No futures first.
7. No withdrawal permissions ever.
8. No live trading in Milestone 1.
9. No strategy self-promotion.
10. No optimizer self-promotion.
11. No live code edits during market hours in future live phases.
12. No broker or exchange secrets in the repository.
13. Data drift, execution drift, or reconciliation drift can disable trading.
14. Strategy quarantine blocks all trading for that strategy.
15. Capital unlock rules are required before any scaling.
16. Freqtrade is dry-run-only until a future explicit human-approved phase.
17. Freqtrade configs must never include exchange keys in this repo.
18. Autonomous operations may report Freqtrade status but may not start Freqtrade by default.
19. Dry-run comparison evidence may support research and shadow decisions, but live promotion remains blocked until a future explicit human-approved canary phase.
20. Trade artifact reconciliation may inspect local dry-run artifacts only and may never become permission to trade live.
21. Market-structure and SMC features are measurable research inputs, not proof of edge.
22. Strategy leaderboards may rank research candidates but must never emit a live-ready status.
23. Overfitting warnings block confidence and require human review before any future dry-run promotion.
24. Synthetic expanded datasets are evidence plumbing only; they are not real market proof.
25. Evidence scoring must always block live promotion until a future explicit human-approved live phase exists.
26. Historical data improves evidence quality, but never grants live-trading authority by itself.
27. Proving mode may prove repeated dry-run behavior, but never grants live-trading authority by itself.
28. Tiny-live canary policy gates are planning scaffolds only and cannot unlock live trading.
29. Human approval, permission checks, stoploss-on-exchange readiness, and incident runbooks are prerequisites, not authority to trade.
30. Canary rehearsals, arming tokens, and final gates are proof scaffolds only and cannot create live order authority.
31. Tiny-live canary execution is default-off, manual-only, spot-only, tiny-notional, one-position-max, and cannot be started by autonomous or AI workflows.
32. Single-exchange canary adapters must be fake-only by default, require local settings outside the repo, and may never bypass permission, approval, arming, stoploss, reconciliation, symbol, notional, kill-switch, or incident gates.

This project starts as a local deterministic simulation foundation. It is not safe for real money.
