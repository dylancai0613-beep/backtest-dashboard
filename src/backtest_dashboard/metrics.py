"""通用交易级指标，供适配器和测试复用。"""

from __future__ import annotations

from statistics import median
from typing import Iterable


def summarize_trade_results(returns: Iterable[float], net_pnls: Iterable[float], nominal_capital: float = 100_000.0) -> dict[str, float | int | None]:
    values = [float(value) for value in returns]
    pnls = [float(value) for value in net_pnls]
    if len(values) != len(pnls):
        raise ValueError("收益率与净盈亏长度必须一致")
    count = len(pnls)
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = sum(value for value in pnls if value < 0)
    return {
        "trade_count": count,
        "win_rate": sum(value > 0 for value in pnls) / count if count else None,
        "mean_return": sum(values) / count if count else None,
        "median_return": median(values) if values else None,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": gross_profit / abs(gross_loss) if gross_loss else None,
        "net_pnl": sum(pnls),
        "capital_weighted_return": sum(pnls) / (count * nominal_capital) if count else None,
    }
