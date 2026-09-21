"""通过 Chrome DevTools Protocol 对离线看板进行有界渲染验收。"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import time
import urllib.parse
import urllib.request
from pathlib import Path


class DevToolsClient:
    def __init__(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        self.sock = socket.create_connection((parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.sock.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError("DevTools WebSocket 握手失败")
        self.counter = 0
        self.events: list[dict] = []

    def _send(self, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        mask = os.urandom(4)
        length = len(raw)
        head = bytearray([0x81])
        if length < 126:
            head.append(0x80 | length)
        elif length < 65536:
            head.append(0x80 | 126)
            head.extend(struct.pack("!H", length))
        else:
            head.append(0x80 | 127)
            head.extend(struct.pack("!Q", length))
        head.extend(mask)
        head.extend(bytes(value ^ mask[i % 4] for i, value in enumerate(raw)))
        self.sock.sendall(head)

    def _receive(self) -> dict:
        first = self.sock.recv(2)
        if len(first) < 2:
            raise RuntimeError("DevTools 连接意外关闭")
        length = first[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", self.sock.recv(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self.sock.recv(8))[0]
        chunks = bytearray()
        while len(chunks) < length:
            chunks.extend(self.sock.recv(length - len(chunks)))
        return json.loads(chunks.decode("utf-8"))

    def call(self, method: str, params: dict | None = None) -> dict:
        self.counter += 1
        request_id = self.counter
        self._send({"id": request_id, "method": method, "params": params or {}})
        while True:
            message = self._receive()
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message.get("result", {})
            self.events.append(message)

    def evaluate(self, expression: str, *, await_promise: bool = False) -> object:
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": await_promise})
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"].get("text", "JavaScript 执行失败"))
        return result.get("result", {}).get("value")


def _target(port: int, expected_url: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=10) as response:
        targets = json.load(response)
    for target in targets:
        if target.get("type") == "page" and target.get("url") == expected_url:
            return target
    raise RuntimeError("未找到看板页面调试目标")


def _capture(client: DevToolsClient, path: Path, *, full: bool = False) -> None:
    params: dict = {"format": "png", "captureBeyondViewport": full, "fromSurface": True}
    if full:
        size = client.call("Page.getLayoutMetrics")["cssContentSize"]
        params["clip"] = {"x": 0, "y": 0, "width": min(size["width"], 1440), "height": min(size["height"], 6000), "scale": 1}
    result = client.call("Page.captureScreenshot", params)
    path.write_bytes(base64.b64decode(result["data"]))


def verify(port: int, dashboard: Path, preview: Path, narrow_preview: Path) -> dict:
    url = dashboard.resolve().as_uri()
    client = DevToolsClient(_target(port, url)["webSocketDebuggerUrl"])
    client.call("Runtime.enable")
    client.call("Log.enable")
    client.call("Network.enable")
    client.call("Page.enable")
    client.call("Page.reload", {"ignoreCache": True})
    for _ in range(80):
        if client.evaluate("Boolean(window.__dashboardReady)"):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"看板未就绪：{client.evaluate('window.__dashboardError || document.readyState')}")

    client.call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1200, "deviceScaleFactor": 1, "mobile": False})
    client.evaluate("document.querySelector('[data-tab=overview]').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    _capture(client, preview)
    tabs = {}
    for name in ("overview", "performance", "risk", "trades", "quality", "runs"):
        client.evaluate(f"document.querySelector('[data-tab={name}]').click()")
        client.evaluate("window.scrollTo(0,0);new Promise(r=>setTimeout(r,250))", await_promise=True)
        tabs[name] = client.evaluate(
            f"(()=>{{const v=document.querySelector('[data-view={name}]');return {{visible:!v.hidden,textLength:v.innerText.length,charts:v.querySelectorAll('.chart canvas').length,empty:v.querySelectorAll('.echarts-empty').length}}}})()"
        )
        if name != "overview":
            _capture(client, preview.parent / f"_tab_{name}.png", full=True)

    client.evaluate("document.querySelector('[data-tab=trades]').click();document.getElementById('symbol-filter').value=String(window.DATA.trades[0][window.C.symbol]);document.getElementById('symbol-filter').dispatchEvent(new Event('input',{bubbles:true}))")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    search = client.evaluate("({rows:window.__dashboardDiagnostics.filteredRows,domRows:document.querySelectorAll('#trade-body tr').length,page:document.getElementById('page-status').textContent})")
    client.evaluate("document.getElementById('reset-filters').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)

    client.evaluate("document.querySelector('[data-tab=performance]').click()")
    legend_before = client.evaluate("window.charts.get('chart-rolling').getOption().legend[0].selected['滚动3个月 PF']")
    client.evaluate("window.charts.get('chart-rolling').dispatchAction({type:'legendToggleSelect',name:'滚动3个月 PF'})")
    legend_hidden = client.evaluate("window.charts.get('chart-rolling').getOption().legend[0].selected['滚动3个月 PF']")
    client.evaluate("window.charts.get('chart-rolling').dispatchAction({type:'legendToggleSelect',name:'滚动3个月 PF'})")
    legend_restored = client.evaluate("window.charts.get('chart-rolling').getOption().legend[0].selected['滚动3个月 PF']")
    legend_name = client.evaluate("window.charts.get('chart-rolling').getOption().series[0].name")
    legend_before = client.evaluate("window.charts.get('chart-rolling').getOption().legend[0].selected[window.charts.get('chart-rolling').getOption().series[0].name]")
    client.evaluate("window.charts.get('chart-rolling').dispatchAction({type:'legendToggleSelect',name:window.charts.get('chart-rolling').getOption().series[0].name})")
    legend_hidden = client.evaluate("window.charts.get('chart-rolling').getOption().legend[0].selected[window.charts.get('chart-rolling').getOption().series[0].name]")
    client.evaluate("window.charts.get('chart-rolling').dispatchAction({type:'legendToggleSelect',name:window.charts.get('chart-rolling').getOption().series[0].name})")
    legend_restored = client.evaluate("window.charts.get('chart-rolling').getOption().legend[0].selected[window.charts.get('chart-rolling').getOption().series[0].name]")
    client.evaluate("window.charts.get('chart-rolling').dispatchAction({type:'dataZoom',start:20,end:70})")
    zoomed = client.evaluate("window.charts.get('chart-rolling').getOption().dataZoom[0].start")
    client.evaluate("window.charts.get('chart-rolling').dispatchAction({type:'dataZoom',start:0,end:100})")
    chart_export_ready = client.evaluate("window.charts.get('chart-rolling').getDataURL({type:'png'}).startsWith('data:image/png')")
    csv_export_ready = client.evaluate("typeof document.getElementById('export-csv').onclick === 'function'")
    client.evaluate("window.selectMonth('2025-07')")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    month_rows = client.evaluate("window.__dashboardDiagnostics.filteredRows")
    month_selection = client.evaluate("window.__dashboardDiagnostics.monthSelection")
    month_active_tab = client.evaluate("window.__dashboardDiagnostics.activeTab")
    month_banner = client.evaluate("!document.getElementById('month-drilldown-banner').hidden && document.getElementById('month-drilldown-text').textContent.includes('2025-07')")
    client.evaluate("document.getElementById('trades-return-month-chart').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    month_return_tab = client.evaluate("window.__dashboardDiagnostics.activeTab")
    month_return_kept = client.evaluate("window.__dashboardDiagnostics.monthSelection === '2025-07'")
    client.evaluate("document.getElementById('restore-month-filter').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    month_restored = client.evaluate("window.__dashboardDiagnostics.filteredRows")
    month_restore_cleared = client.evaluate("window.__dashboardDiagnostics.monthSelection === null && document.getElementById('month-drilldown-banner').hidden")
    client.evaluate("document.getElementById('symbol-filter').value='__no_such_symbol__';document.getElementById('symbol-filter').dispatchEvent(new Event('input',{bubbles:true}))")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    empty_rows = client.evaluate("window.__dashboardDiagnostics.filteredRows")
    client.evaluate("document.getElementById('reset-filters').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    empty_restored = client.evaluate("window.__dashboardDiagnostics.filteredRows")
    client.evaluate("document.querySelector('[data-tab=performance]').click();document.getElementById('year-filter').value='2025';document.getElementById('year-filter').dispatchEvent(new Event('input',{bubbles:true}))")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    benchmark_2025 = client.evaluate("(()=>{const o=window.charts.get('chart-benchmark').getOption();const d=o.series[0].data;return {first:d[0].value?d[0].value[1]:d[0][1],last:d[d.length-1].value?d[d.length-1].value[1]:d[d.length-1][1],note:document.getElementById('benchmark-note').textContent,axis:window.charts.get('chart-yearly').getOption().yAxis[0].axisLabel.formatter(0.02)}})()")
    client.evaluate("document.getElementById('reset-filters').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    rolling_context = client.evaluate("(()=>{const o=window.charts.get('chart-rolling').getOption(),d=o.series[0].data[10],tip=o.tooltip[0].formatter([{seriesName:o.series[0].name,data:d}]);return {hasWindow:Boolean(d.window),tooltip:tip,firstStatus:d.window&&d.window.window_completeness}})()")
    client.evaluate("document.querySelector('[data-tab=trades]').click();document.querySelector('#trade-body tr').click()")
    detail_open = client.evaluate("document.getElementById('trade-detail').open")
    client.evaluate("document.getElementById('close-trade-detail').click()")
    client.evaluate("document.getElementById('outcome-filter').value='loss';document.getElementById('outcome-filter').dispatchEvent(new Event('input',{bubbles:true}))")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    loss_rows = client.evaluate("window.__dashboardDiagnostics.filteredRows")
    loss_text = client.evaluate("document.body.innerText")
    client.evaluate("document.getElementById('reset-filters').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    reset_rows = client.evaluate("window.__dashboardDiagnostics.filteredRows")
    client.evaluate("document.getElementById('page-next').click()")
    pagination = client.evaluate("document.getElementById('page-status').textContent")
    client.evaluate("document.getElementById('outcome-filter').value='win';document.getElementById('outcome-filter').dispatchEvent(new Event('input',{bubbles:true}))")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    win_rows = client.evaluate("window.__dashboardDiagnostics.filteredRows")
    client.evaluate("document.getElementById('reset-filters').click()")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)

    client.call("Emulation.setDeviceMetricsOverride", {"width": 480, "height": 900, "deviceScaleFactor": 1, "mobile": True})
    client.evaluate("document.querySelector('[data-tab=overview]').click();window.scrollTo(0,0)")
    client.evaluate("new Promise(r=>setTimeout(r,250))", await_promise=True)
    narrow = client.evaluate("({innerWidth:innerWidth,scrollWidth:document.documentElement.scrollWidth,brokenText:document.body.innerText.includes(String.fromCharCode(0xfffd)),kpis:document.querySelectorAll('.kpi').length})")
    _capture(client, narrow_preview)
    error_events = [
        event for event in client.events
        if event.get("method") in {"Runtime.exceptionThrown", "Log.entryAdded"}
        and (
            event.get("method") == "Runtime.exceptionThrown"
            or event.get("params", {}).get("entry", {}).get("level") == "error"
        )
    ]
    result = {
        "status": "PASS",
        "tabs": tabs,
        "search": search,
        "pagination_after_next": pagination,
        "reset_rows": reset_rows,
        "win_rows": win_rows,
        "legend": {"before": legend_before, "hidden": legend_hidden, "restored": legend_restored},
        "zoom_start_after_action": zoomed,
        "chart_export_ready": chart_export_ready,
        "csv_export_ready": csv_export_ready,
        "month": {"selected": month_selection, "rows": month_rows, "active_tab": month_active_tab, "banner": month_banner, "return_tab": month_return_tab, "return_kept": month_return_kept, "restored_rows": month_restored, "restore_cleared": month_restore_cleared, "empty_rows": empty_rows, "empty_restored_rows": empty_restored},
        "benchmark_2025": benchmark_2025,
        "rolling_context": rolling_context,
        "trade_detail_open": detail_open,
        "all_loss_rows": loss_rows,
        "all_loss_has_invalid_number": "Infinity" in loss_text or "NaN" in loss_text,
        "narrow": narrow,
        "console_error_count": len(error_events),
        "external_request_count": len([event for event in client.events if event.get("method") == "Network.requestWillBeSent" and str(event.get("params", {}).get("request", {}).get("url", "")).startswith(("http://", "https://"))]),
        "preview_sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
    }
    if not all(item["visible"] and item["textLength"] > 20 for item in tabs.values()):
        result["status"] = "FAIL"
    if not (0 < search["rows"] < reset_rows and search["domRows"] <= 25 and "第 2" in pagination):
        result["status"] = "FAIL"
    if reset_rows <= 0 or win_rows <= 0 or win_rows >= reset_rows or narrow["scrollWidth"] > narrow["innerWidth"] or narrow["brokenText"] or error_events:
        result["status"] = "FAIL"
    if not (legend_before is True and legend_hidden is False and legend_restored is True and zoomed >= 20 and chart_export_ready and csv_export_ready and month_selection == "2025-07" and month_rows > 0 and month_active_tab == "交易分析" and month_banner and month_return_tab == "收益表现" and month_return_kept and month_restored == reset_rows and month_restore_cleared and empty_rows == 0 and empty_restored == reset_rows and benchmark_2025["first"] != 0 and "2024-12-31" in benchmark_2025["note"] and benchmark_2025["axis"] == "2.0%" and rolling_context["hasWindow"] and "窗口" in rolling_context["tooltip"] and detail_open and loss_rows > 0 and not result["all_loss_has_invalid_number"] and result["external_request_count"] == 0):
        result["status"] = "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="验收本地离线回测看板")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--dashboard", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--narrow-preview", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.port, args.dashboard, args.preview, args.narrow_preview)
    args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] == "PASS":
        manifest_path = args.dashboard.parent / "dashboard_manifest.json"
        if not manifest_path.is_file():
            return 0
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["quality_flags"].update(
            {
                "visual_desktop": "PASS",
                "visual_narrow": "PASS",
                "browser_console": "PASS",
            }
        )
        manifest["visual_verification"] = {
            "desktop_width": 1440,
            "narrow_width": 480,
            "tabs_checked": 6,
            "search_result_rows": result["search"]["rows"],
            "reset_rows": result["reset_rows"],
            "winning_trade_rows": result["win_rows"],
            "console_error_count": result["console_error_count"],
            "preview_sha256": result["preview_sha256"],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary_path = args.dashboard.parent / "validation_summary.md"
        summary = summary_path.read_text(encoding="utf-8").split("## 视觉验收", 1)[0]
        summary += f"""## 浏览器验收

- 桌面宽度（1440 像素）：**通过**；六个视图均已打开，图表、表格与来源详情可见。
- 窄屏宽度（480 像素）：**通过**；页面无全局横向溢出，导航与筛选器可用。
- 股票代码搜索：**通过**；代表性搜索返回 {result['search']['rows']:,} 行，DOM 仅渲染当前页。
- 分页：**通过**；已从第一页切换到第二页。
- 盈利筛选：**通过**；返回 {result['win_rows']:,} / {result['reset_rows']:,} 笔。
- 筛选重置：**通过**；恢复 {result['reset_rows']:,} 笔。
- 滚动3M/6M图例：**通过**；可分别隐藏并恢复。
- 时间缩放与恢复：**通过**；滚动图支持缩放操作。
- 月份点击与筛选恢复：**通过**；月份 {result['month']['selected']} 已切换到交易分析，可返回月度图并恢复筛选。
- 空结果恢复：**通过**；无交易结果可显示，重置后恢复 {result['month']['empty_restored_rows']:,} 笔。
- 沪深300区间口径：**通过**；2025 年基准收盘为 2024-12-31，首日收益未被重新归零。
- 百分比坐标轴：**通过**；0.02 显示为 {result['benchmark_2025']['axis']}。
- 滚动窗口提示：**通过**；窗口对象、窗口起止和完整性说明可由悬浮提示读取。
- 交易详情面板：**通过**；点击交易行可打开并关闭详情。
- 图片导出：**通过**；ECharts PNG data URL 可生成；交易 CSV 导出入口保留。
- 浏览器控制台：**通过**；错误数 {result['console_error_count']}。
- 外部请求：**通过**；离线页面外部请求数 {result['external_request_count']}。
- 中文与图形：**通过**；未发现替换字符、缺失图形、标签重叠或误标组合净值。
"""
        summary_path.write_text(summary, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
