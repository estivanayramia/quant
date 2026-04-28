"""
QuantOSDryRunStrategy

Dry-run research only. This strategy scaffold does not claim profitability,
does not use leverage, does not short, does not use futures, does not call AI,
and does not connect to any broker outside Freqtrade dry-run simulation.
"""

from __future__ import annotations

from pandas import DataFrame

try:
    from freqtrade.strategy import IStrategy
except Exception:  # pragma: no cover - local tests validate file content only.
    class IStrategy:  # type: ignore[no-redef]
        pass


class QuantOSDryRunStrategy(IStrategy):
    """Conservative deterministic scaffold for dry-run comparison only."""

    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "5m"
    startup_candle_count = 30
    process_only_new_candles = True
    minimal_roi = {"0": 0.01}
    stoploss = -0.02
    trailing_stop = False
    use_exit_signal = True

    def leverage(self, *args, **kwargs) -> float:
        return 1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ma_fast"] = dataframe["close"].rolling(5, min_periods=1).mean()
        dataframe["ma_slow"] = dataframe["close"].rolling(20, min_periods=1).mean()
        delta = dataframe["close"].diff().fillna(0.0)
        gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
        loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
        rs = gain / loss.replace(0, 1e-12)
        dataframe["rsi"] = 100 - (100 / (1 + rs))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        entry = (dataframe["ma_fast"] > dataframe["ma_slow"]) & (dataframe["rsi"] < 70)
        dataframe.loc[entry, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        exit_signal = (dataframe["ma_fast"] < dataframe["ma_slow"]) | (dataframe["rsi"] > 80)
        dataframe.loc[exit_signal, "exit_long"] = 1
        return dataframe
