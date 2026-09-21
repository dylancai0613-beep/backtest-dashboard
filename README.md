# Backtest Dashboard

一个通用的离线回测看板生成器。

项目接收稳定的 `dashboard_data.json` 数据协议，生成内嵌数据、CSS、JavaScript 与 Apache ECharts 的单文件 HTML。生成后的页面可直接在浏览器中打开，不依赖 CDN、远程字体、数据库或外部网络请求。

**在线演示：**  
https://dylancai0613-beep.github.io/backtest-dashboard/

> 在线 Demo 使用完全合成的数据，仅用于展示看板 UI 与交互能力，不代表任何真实策略、账户或投资表现。

## 功能特点

- **单文件 HTML**：数据、样式、脚本和 ECharts 均打包到一个 HTML 文件中
- **离线可用**：生成后的看板可直接通过本地浏览器打开
- **交互式图表**：支持回测结果、时间序列、Benchmark、滚动指标等交互展示
- **交易明细展示**：可查看交易记录及相关明细信息
- **月份下钻与恢复**：支持按月份查看并返回完整时间范围
- **图表缩放与悬停提示**：便于检查不同时间区间的表现
- **导出能力**：支持页面内提供的 CSV / PNG 等导出交互
- **响应式布局**：兼容桌面端和较窄浏览器窗口
- **稳定数据协议**：上游项目只需要生成符合约定的 `dashboard_data.json`
- **与策略解耦**：本项目不执行回测，也不绑定某个固定策略、运行目录或本机路径

## 在线 Demo

GitHub Pages：

https://dylancai0613-beep.github.io/backtest-dashboard/

Demo 页面对应仓库中的：

```text
docs/index.html
```

示例数据由：

```text
examples/generate_sample.py
```

确定性生成。

当前示例包含 120 笔完全合成交易，并覆盖正收益、负收益、持平结果、滚动窗口边界、合成 Benchmark 以及可选空值等情况。

示例数据不包含：

- 真实策略表现
- 真实交易记录
- 账户信息
- 原始行情数据
- API Key / Token / 凭证
- 本机绝对路径

## 安装与使用

### 1. 安装

```bash
python -m pip install -e .[dev]
```

### 2. 生成示例数据

```bash
python examples/generate_sample.py
```

### 3. 生成 Dashboard

```bash
python -m backtest_dashboard.cli build \
  --input examples/sample_dashboard_data.json \
  --output examples/sample_dashboard.html
```

### 4. 验证生成结果

```bash
python -m backtest_dashboard.cli validate \
  --html examples/sample_dashboard.html
```

### 5. 运行测试

```bash
python -m pytest -q
```

生成完成后，可以直接用浏览器打开：

```text
examples/sample_dashboard.html
```

不需要启动 Web Server。

## Python 调用

也可以直接在 Python 中调用：

```python
from backtest_dashboard import write_dashboard

write_dashboard(dashboard_data, "dashboard.html")
```

其中 `dashboard_data` 应由上游项目适配器负责构造。

本包本身不会：

- 执行策略回测
- 读取固定策略目录
- 绑定固定的 `runs/` 或 `reports/` 路径
- 读取某台电脑的绝对路径
- 获取外部行情数据
- 依赖数据库或在线服务

## 数据协议

Dashboard 使用统一的数据协议作为回测系统与展示层之间的接口。

协议字段、空值约束、字段含义及来源说明见：

[`docs/data_contract.md`](docs/data_contract.md)

典型使用方式：

```text
Backtest / Research Project
        │
        │  构造 dashboard_data
        ▼
dashboard_data.json
        │
        ▼
backtest-dashboard
        │
        ▼
single-file dashboard.html
```

因此，策略研究项目可以保留自己的回测逻辑、指标口径和数据处理方式，只需要在展示前转换成统一 Dashboard 数据结构。

## 项目结构

```text
backtest-dashboard/
├─ docs/
│  ├─ data_contract.md
│  ├─ extraction_report.md
│  └─ index.html
├─ examples/
│  ├─ generate_sample.py
│  ├─ sample_dashboard_data.json
│  └─ sample_dashboard.html
├─ src/
│  └─ backtest_dashboard/
│     ├─ assets/
│     ├─ templates/
│     ├─ builder.py
│     ├─ cli.py
│     ├─ metrics.py
│     ├─ schema.py
│     └─ validation.py
├─ tests/
│  ├─ browser_acceptance.py
│  └─ test_dashboard.py
├─ THIRD_PARTY_NOTICES.md
├─ pyproject.toml
└─ README.md
```

## 设计边界

本仓库只负责**通用回测结果展示层**。

允许进入本仓库的内容包括：

- Dashboard 生成器源码
- HTML 模板
- CSS / JavaScript
- 本地 Apache ECharts 文件
- 数据协议
- 自动化测试
- 文档
- 小型合成示例

不应进入本仓库的内容包括：

- 真实策略运行目录
- 大型回测产物
- 完整研究报告
- 原始行情数据
- 私有交易账本
- API Key、Token 或其他凭证
- 与单个研究项目绑定的私有配置

因此，克隆本仓库可以恢复通用 Dashboard 工具，但不能恢复任何真实研究数据或私有策略结果。

## 第三方组件

本项目内置 Apache ECharts，用于离线图表渲染。

Apache ECharts 按 Apache License 2.0 授权。相关第三方版权和许可证信息见：

[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

打包的第三方文件保留其原始许可证声明。

## License

本仓库目前公开用于项目展示、技术交流与代码审阅，但**尚未为本项目代码附加开源许可证**。

除 `THIRD_PARTY_NOTICES.md` 中明确列出的第三方组件外，公开可见不代表自动授予复制、修改或再分发本项目代码的权利。

如果未来决定正式开源，可以再单独添加 MIT、Apache-2.0 或其他适合的许可证。

---

**Repository:** https://github.com/dylancai0613-beep/backtest-dashboard  
**Live Demo:** https://dylancai0613-beep.github.io/backtest-dashboard/
