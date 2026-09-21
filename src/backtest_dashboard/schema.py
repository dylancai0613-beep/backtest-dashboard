"""看板数据协议的轻量、无第三方依赖验证。"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


class DashboardDataError(ValueError):
    """输入不满足看板数据协议。"""


REQUIRED_TOP_LEVEL = {
    "schema_version",
    "strategy",
    "strategy_explanation",
    "run",
    "authoritative_metrics",
    "population_counts",
    "trade_columns",
    "trades",
    "filters",
    "benchmark",
    "audit_cards",
    "companion",
    "run_catalog",
    "comparison_compatibility",
    "sources",
}

REQUIRED_TRADE_COLUMNS = {
    "trade_id",
    "symbol",
    "signal_date",
    "entry_datetime",
    "exit_datetime",
    "entry_price",
    "exit_price",
    "return_pct",
    "net_pnl",
    "holding_days",
    "exit_reason",
}


def _reject_non_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise DashboardDataError(f"{path} 包含 NaN 或 Infinity")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_non_finite(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{path}[{index}]")


def validate_dashboard_data(data: Mapping[str, Any]) -> None:
    """验证生成页面所需的最小稳定协议。"""
    if not isinstance(data, Mapping):
        raise DashboardDataError("输入根节点必须是对象")
    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        raise DashboardDataError(f"缺少顶层字段：{', '.join(missing)}")
    if data["schema_version"] != "backtest_dashboard_data_v1":
        raise DashboardDataError("不支持的 schema_version")
    for section in ("strategy", "strategy_explanation", "run", "filters", "benchmark", "companion"):
        if not isinstance(data[section], Mapping):
            raise DashboardDataError(f"{section} 必须是对象")
    for field in ("run_id", "period_start", "period_end", "status", "execution_semantics", "population"):
        if not data["run"].get(field):
            raise DashboardDataError(f"run.{field} 不得为空")
    columns = data["trade_columns"]
    if not isinstance(columns, list) or len(columns) != len(set(columns)):
        raise DashboardDataError("trade_columns 必须是无重复字段名的数组")
    absent_columns = sorted(REQUIRED_TRADE_COLUMNS - set(columns))
    if absent_columns:
        raise DashboardDataError(f"交易列缺失：{', '.join(absent_columns)}")
    trades = data["trades"]
    if not isinstance(trades, list):
        raise DashboardDataError("trades 必须是数组")
    for index, row in enumerate(trades):
        if not isinstance(row, list) or len(row) != len(columns):
            raise DashboardDataError(f"trades[{index}] 与 trade_columns 长度不一致")
    _reject_non_finite(data)
