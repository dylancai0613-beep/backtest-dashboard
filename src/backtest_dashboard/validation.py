"""生成物的离线性、安全性与基本完整性检查。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REMOTE_ASSET_PATTERN = re.compile(r"<(?:script|link|img)[^>]+(?:src|href)=[\"']https?://", re.I)
ABSOLUTE_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\\\|[A-Za-z]:/[A-Za-z0-9_]|file://|/(?:home|Users)/)")
SECRET_PATTERNS = {
    "私钥": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "常见访问密钥": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "疑似令牌赋值": re.compile(r"(?i)(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}"),
}


def validate_html(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    findings: list[str] = []
    if REMOTE_ASSET_PATTERN.search(text):
        findings.append("包含远程页面资源")
    if ABSOLUTE_PATH_PATTERN.search(text):
        findings.append("包含绝对路径")
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"命中{name}")
    for label in ("总览", "收益表现", "风险与分布", "交易分析", "执行与数据可信度", "运行记录"):
        if label not in text:
            findings.append(f"缺少视图：{label}")
    payload_match = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', text, re.S)
    if payload_match:
        try:
            json.loads(payload_match.group(1), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (json.JSONDecodeError, ValueError):
            findings.append("数据载荷不是严格 JSON，可能包含 NaN 或 Infinity")
    return {"status": "PASS" if not findings else "FAIL", "path": str(target), "findings": findings}
