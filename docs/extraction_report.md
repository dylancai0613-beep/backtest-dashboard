# 看板独立拆分报告

## 通用模块来源

通用模板、样式、交互脚本、Apache ECharts 5.6.0 与单文件渲染器源自 `strategy-backtest-lab` 原 `infrastructure/reporting/backtest_dashboard/`。迁移后由 `src/backtest_dashboard/` 独立维护；标题和运行链接改为数据驱动，不包含固定策略、运行编号或本机绝对路径。

## 项目专属逻辑隔离

主项目继续维护 `services/reporting/dashboard_data_builder.py`，负责读取权威运行、选择 Primary 经济交易、构造冻结策略说明、核对七项核心指标、生成 Benchmark 年度口径、滚动窗口对账和项目审计项。独立包不读取主项目目录，也不复制这些口径。

## 数据协议与示例

双方通过 `backtest_dashboard_data_v1` 连接，详见 `docs/data_contract.md`。示例由确定性脚本生成，共 120 笔合成交易；示例数据不代表真实策略表现，未复制真实交易、行情或完整看板。

## 验证结果

正式目录验证结果：包导入通过；CLI 帮助、生成与验证命令通过；单元测试 `4 passed`。120 笔合成示例可生成完全离线 HTML。无头 Chrome 验收通过六个视图、图例切换、时间缩放、2025-07 月份下钻与恢复、交易分页与详情、PNG/CSV 导出、1440 像素桌面与 480 像素窄屏、空筛选恢复和全亏损状态；控制台错误 0，外部请求 0。协议验证拒绝 NaN、Infinity 和交易列长度不一致，指标测试覆盖空集、全赢零亏损分母与全亏损。

## 本地发布前收尾

在不重跑浏览器大验收的前提下，按主项目最终源码完成收尾复核：主项目 `264 passed, 24 skipped, 0 failed`；本包 `4 passed`；两个仓库工作树与暂存区 `git diff --check` 均通过。两个仓库保持 fresh `main`、0 commit、0 remote；Git identity 与 `gh` 仍未配置/安装，因此未创建提交或远端。

## 已知限制

本包不执行策略回测，不定义上游经济交易人口，不从原始行情重建 Benchmark，也不计算缺失的组合日频风险指标。浏览器验收依赖本机 Chrome 或 Chromium；真实运行的业务对账必须由上游项目完成。
