# 离线回测看板

这是一个私人仓库中的通用回测看板包。它接收稳定的 `dashboard_data.json` 协议，生成内嵌数据、CSS、JavaScript 与 Apache ECharts 的单文件 HTML；页面可直接通过本地文件打开，不依赖 CDN、远程字体、数据库或网络请求。

本仓库未附加开源许可证。私人仓库，未授权转载或分发。Apache ECharts 仍按其 Apache License 2.0 授权，详见 `THIRD_PARTY_NOTICES.md`；打包文件保留上游许可证头。

## 安装与使用

```powershell
python -m pip install -e .[dev]
python examples/generate_sample.py
python -m backtest_dashboard.cli build --input examples/sample_dashboard_data.json --output examples/sample_dashboard.html
python -m backtest_dashboard.cli validate --html examples/sample_dashboard.html
python -m pytest -q
```

也可在 Python 中调用：

```python
from backtest_dashboard import write_dashboard

write_dashboard(dashboard_data, "dashboard.html")
```

输入应由上游项目适配器构造。本包不会读取某个固定策略、固定运行目录或某台电脑的绝对路径，也不会执行回测。协议字段、空值约束与来源说明见 `docs/data_contract.md`。

## 示例边界

`examples/sample_dashboard_data.json` 由 `examples/generate_sample.py` 确定性生成，包含 120 笔完全合成交易、正负与持平结果、滚动窗口边界、合成 Benchmark 及可选空值。示例数据不代表真实策略表现，不包含真实交易、账户信息、行情、凭证或本机路径。

## 仓库边界

允许提交生成器源码、模板、本地 ECharts、测试、文档与小型合成示例。不得提交真实运行目录、完整报告、原始行情、私有凭证或大型交易账本。换电脑后，克隆本仓库只能恢复通用看板工具；真实研究数据必须由其所属项目的独立备份恢复。
