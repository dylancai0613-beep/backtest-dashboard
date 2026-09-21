"""生成 120 笔确定性合成交易，仅用于演示看板能力。"""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["trade_id", "symbol", "signal_date", "entry_datetime", "exit_datetime", "entry_price", "exit_price", "return_pct", "net_pnl", "holding_days", "exit_reason"]


def _metrics(rows: list[list]) -> dict:
    returns = [float(row[7]) for row in rows]
    pnls = [float(row[8]) for row in rows]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = sum(value for value in pnls if value < 0)
    ordered = sorted(returns)
    middle = len(ordered) // 2
    median = (ordered[middle - 1] + ordered[middle]) / 2 if len(ordered) % 2 == 0 else ordered[middle]
    return {
        "completed_trades": len(rows),
        "win_rate": sum(value > 0 for value in pnls) / len(rows),
        "mean_return": sum(returns) / len(rows),
        "median_return": median,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": gross_profit / abs(gross_loss),
        "net_pnl": sum(pnls),
        "capital_weighted_return": sum(pnls) / (len(rows) * 100_000),
        "average_holding_days": sum(row[9] for row in rows) / len(rows),
        "median_holding_days": 4,
        "return_distribution": {},
        "return_threshold_counts": {},
        "right_tail": {},
    }


def build_sample() -> dict:
    trades: list[list] = []
    reasons = ["signal_reversal", "risk_limit", "time_exit"]
    for index in range(120):
        month = index // 10 + 1
        day = index % 10 + 2
        signal = date(2025, month, min(day, monthrange(2025, month)[1]))
        holding = index % 8 + 1
        result = [0.018, -0.012, 0.0, 0.034, -0.025, 0.007, -0.006][index % 7]
        entry = 10 + (index % 17) * 0.23
        exit_price = entry * (1 + result)
        trades.append([
            f"sample-{index + 1:03d}",
            f"SYN{index % 12 + 1:03d}",
            signal.isoformat() + "T10:00:00+08:00",
            signal.isoformat() + "T10:15:00+08:00",
            (signal + timedelta(days=holding)).isoformat() + "T14:45:00+08:00",
            round(entry, 4),
            round(exit_price, 4),
            result,
            round(result * 100_000, 2),
            holding,
            reasons[index % len(reasons)],
        ])
    metrics = _metrics(trades)
    months = [f"2025-{month:02d}" for month in range(1, 13)]
    monthly = []
    for month in months:
        rows = [row for row in trades if row[2].startswith(month)]
        item = _metrics(rows)
        monthly.append({"period": month, "year": 2025, "month": int(month[-2:]), "trade_count": len(rows), "profit_factor": item["profit_factor"], "capital_weighted_return": item["capital_weighted_return"], "completeness": "FULL_MONTH"})
    benchmark = [{"date": "2024-12-31", "close": 100.0, "normalized_return": 0.0}]
    benchmark.extend({"date": f"2025-{month:02d}-{monthrange(2025, month)[1]:02d}", "close": round(100 + month * 0.8 + ((-1) ** month) * 2.2, 3), "normalized_return": 0.0} for month in range(1, 13))
    title = "合成策略离线回测看板（示例数据）"
    return {
        "schema_version": "backtest_dashboard_data_v1",
        "presentation": {"title": title, "sample_disclosure": "示例数据，不代表真实策略表现"},
        "generated_at": "2026-09-20T00:00:00+08:00",
        "strategy": {"id": "synthetic_demo", "name": "合成策略", "version": "1.0"},
        "strategy_explanation": {
            "applies_to": {"run_id": "sample-run-001", "scenario_id": "synthetic", "scope_label": "示例数据，不代表真实策略表现", "strategy": "合成策略"},
            "strategy_idea": "用完全合成的交易展示通用看板能力，不表达任何投资观点。",
            "main_buy_conditions": ["合成条件 A", "合成条件 B"],
            "main_sell_conditions": ["合成退出条件", "合成风险边界"],
            "capital_execution": ["每笔名义本金 100,000 元", "价格与交易均为合成数据"],
            "evidence_sources": ["examples/generate_sample.py"],
            "details": ["包含盈利、亏损、持平、边界窗口与市场背景。"],
        },
        "run": {"run_id": "sample-run-001", "period_start": "2025-01-02", "period_end": "2025-12-31", "status": "COMPLETE", "execution_semantics": "合成信号与合成价格，仅供界面验证", "population": "120 笔合成完成交易"},
        "authoritative_metrics": metrics,
        "population_counts": {"signals": 124, "filled_entries": 121, "completed_trades_all": 120, "primary_economic_trades": 120, "corporate_action_crossing_trades": 0, "open_positions_end": 1},
        "trade_columns": COLUMNS,
        "trades": trades,
        "filters": {"entry_reason_available": False, "exit_reasons": reasons, "years": [2025]},
        "benchmark": {"status": "AVAILABLE_AS_MARKET_CONTEXT", "label": "合成 Benchmark 背景", "series_type": "daily_close_relative", "series": benchmark, "annual_reconciliation": [], "limitation": "合成序列，仅用于交互验证", "source_granularity": "月末合成点"},
        "audit_cards": [
            {"name": "示例性质", "status": "PASS", "meaning": "数据由本仓库脚本确定性生成。", "evidence_source": "examples/generate_sample.py", "scope": "本示例", "limitation": "不代表真实策略表现"},
            {"name": "空值边界", "status": "PARTIAL", "meaning": "协议允许可选说明字段为空。", "evidence_source": "sample_dashboard_data.json", "scope": "可选字段", "limitation": "核心数值不得为 NaN 或 Infinity"},
        ],
        "companion": {"daily_realized_pnl": [], "yearly_performance": [{"year": 2025, "period": 2025, "trade_count": 120, "capital_weighted_return": metrics["capital_weighted_return"], "completeness": "FULL_YEAR"}], "half_year_performance": [], "monthly_performance": monthly, "rolling_3m_performance": [], "rolling_6m_performance": [], "factor_coverage": [{"period": "2025-H1", "factor_eligibility_ratio": 0.82}, {"period": "2025-H2", "factor_eligibility_ratio": 0.88}]},
        "portfolio_risk": {"status": "UNAVAILABLE", "message": "当前产物不支持该指标", "reason": "示例不提供组合日频净值"},
        "run_catalog": [{"strategy_id": "synthetic_demo", "analysis_id": "sample", "run_id": "sample-run-001", "period_start": "2025-01-02", "period_end": "2025-12-31", "run_status": "COMPLETE", "trade_count": 120, "profit_factor": metrics["profit_factor"], "capital_weighted_return": metrics["capital_weighted_return"], "source_availability": "示例内嵌", "dashboard_availability": "当前页面", "comparison_note": "仅与相同协议和口径比较", "artifact_href": None}],
        "comparison_compatibility": {"status": "NO_COMPATIBLE_PEER", "compatible_run_count": 0, "key_fields": ["策略身份", "指标口径", "执行语义", "交易定义"], "primary_key": "synthetic_demo|sample", "message": "示例未提供第二个可比运行。"},
        "sources": [{"path": "examples/generate_sample.py", "role": "确定性合成数据生成器", "note": None}],
    }


def main() -> None:
    output = ROOT / "examples" / "sample_dashboard_data.json"
    output.write_text(json.dumps(build_sample(), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
