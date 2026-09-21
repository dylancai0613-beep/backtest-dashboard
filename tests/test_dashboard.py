from __future__ import annotations

import json
from pathlib import Path

import pytest

from backtest_dashboard import DashboardDataError, render_dashboard, validate_dashboard_data, write_dashboard
from backtest_dashboard.cli import main
from backtest_dashboard.metrics import summarize_trade_results
from backtest_dashboard.validation import validate_html
from examples.generate_sample import build_sample


def test_sample_contract_and_offline_html(tmp_path: Path) -> None:
    data = build_sample()
    validate_dashboard_data(data)
    target = write_dashboard(data, tmp_path / "sample.html")
    html = target.read_text(encoding="utf-8")
    assert "示例数据，不代表真实策略表现" in html
    assert len(data["trades"]) == 120
    assert validate_html(target)["status"] == "PASS"


def test_cli_build_and_validate(tmp_path: Path) -> None:
    source = tmp_path / "data.json"
    source.write_text(json.dumps(build_sample(), ensure_ascii=False), encoding="utf-8")
    target = tmp_path / "dashboard.html"
    assert main(["build", "--input", str(source), "--output", str(target)]) == 0
    assert main(["validate", "--html", str(target)]) == 0


def test_empty_and_zero_denominator_metrics() -> None:
    empty = summarize_trade_results([], [])
    assert empty["profit_factor"] is None
    all_win = summarize_trade_results([0.01, 0.02], [100.0, 200.0])
    assert all_win["profit_factor"] is None
    all_loss = summarize_trade_results([-0.01, -0.02], [-100.0, -200.0])
    assert all_loss["profit_factor"] == 0.0


def test_nan_and_bad_rows_are_rejected() -> None:
    data = build_sample()
    data["authoritative_metrics"]["win_rate"] = float("nan")
    with pytest.raises(DashboardDataError, match="NaN"):
        render_dashboard(data)
    data = build_sample()
    data["trades"][0].pop()
    with pytest.raises(DashboardDataError, match="长度不一致"):
        validate_dashboard_data(data)
