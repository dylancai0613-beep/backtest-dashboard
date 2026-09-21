"""将协议数据渲染为单文件离线 HTML。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .schema import validate_dashboard_data


BASE = Path(__file__).resolve().parent


def asset_path(name: str) -> Path:
    path = BASE / "assets" / name
    if not path.is_file():
        raise FileNotFoundError(f"看板资源不存在：{name}")
    return path


def package_source_files() -> list[Path]:
    return [
        BASE / "builder.py",
        BASE / "schema.py",
        BASE / "validation.py",
        BASE / "templates" / "dashboard.html",
        BASE / "assets" / "dashboard.css",
        BASE / "assets" / "dashboard.js",
        BASE / "assets" / "echarts.min.js",
    ]


def render_dashboard(data: Mapping[str, Any]) -> str:
    validate_dashboard_data(data)
    template = (BASE / "templates" / "dashboard.html").read_text(encoding="utf-8")
    css = asset_path("dashboard.css").read_text(encoding="utf-8")
    javascript = asset_path("dashboard.js").read_text(encoding="utf-8")
    echarts = asset_path("echarts.min.js").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    return (
        template.replace("/*__DASHBOARD_CSS__*/", css)
        .replace("/*__ECHARTS_JS__*/", echarts)
        .replace("/*__DASHBOARD_JS__*/", javascript)
        .replace("__DASHBOARD_DATA__", payload)
    )


def write_dashboard(data: Mapping[str, Any], output: str | Path) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(data), encoding="utf-8")
    return target
