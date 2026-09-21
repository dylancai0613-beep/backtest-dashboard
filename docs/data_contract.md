# `dashboard_data.json` 数据协议

当前协议版本为 `backtest_dashboard_data_v1`。输入必须是 UTF-8 JSON，所有数值必须为有限值；不可用值使用 `null`，不得写入 `NaN` 或 `Infinity`。

## 顶层职责

| 字段 | 责任 |
|---|---|
| `strategy` / `strategy_explanation` | 策略身份、说明、规则摘要与证据 |
| `run` | 运行编号、期间、状态、执行口径与交易人口 |
| `authoritative_metrics` | 上游权威核心指标，供审计与对账 |
| `population_counts` | 信号、成交、完成交易、排除与未平仓数量 |
| `trade_columns` / `trades` | 列式交易账本；行顺序与字段顺序一一对应 |
| `filters` | 可选年份与退出原因 |
| `companion` | 年、半年、月、滚动窗口、累计已实现盈亏和覆盖率时间表 |
| `benchmark` | Benchmark 背景序列、粒度、来源状态与限制 |
| `audit_cards` | 数据可信度审计项及证据、范围、限制 |
| `run_catalog` | 可选运行目录；链接只能由输入提供相对地址 `artifact_href` |
| `comparison_compatibility` | 可比性键与限制说明 |
| `sources` | 相对来源与角色说明 |
| `presentation` | 可选页面标题与示例披露 |

`trade_columns` 至少包含：`trade_id`、`symbol`、`signal_date`、`entry_datetime`、`exit_datetime`、`entry_price`、`exit_price`、`return_pct`、`net_pnl`、`holding_days`、`exit_reason`。

## 边界

上游适配器负责策略专属读取、交易人口选择、权威指标对账、Benchmark 语义与审计项生成。本包只验证协议并渲染，不推断缺失业务口径。日期使用 ISO 8601；页面的日期筛选以 `signal_date` 为准，累计已实现盈亏以 `exit_datetime` 归集。
