# Market Structure Features

QuantOS treats ICT/SMC-style concepts as measurable feature interfaces, not assumed trading edge.

Implemented deterministic feature families:

- Technical: returns, log returns, moving averages, moving-average distance, rolling volatility, ATR-like range, rolling volume average, and volume z-score.
- Session/time: hour, day of week, weekend flag, UTC session bucket, rough Asia/London/New York labels, and session high/low so far.
- Liquidity/structure: prior swing high/low, rolling high/low, distance to range bounds, breakouts, breakdowns, and liquidity sweeps.
- SMC-inspired interfaces: fair value gap candidates, BOS/CHOCH candidates, order block placeholders, premium/discount location, and a transparent SMC score.

All rolling features are built from current and prior rows only. These features are inputs for research and rejection workflows; they do not prove edge and do not bypass deterministic risk controls.
