"""独立看板命令行。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .builder import write_dashboard
from .schema import DashboardDataError
from .validation import validate_html


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="生成或验证完全离线的回测看板")
    commands = root.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="从 dashboard_data.json 生成 HTML")
    build.add_argument("--input", required=True, help="看板数据 JSON")
    build.add_argument("--output", required=True, help="输出 HTML")
    check = commands.add_parser("validate", help="检查生成 HTML 的离线性与完整性")
    check.add_argument("--html", required=True, help="待检查 HTML")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build":
            source = Path(args.input)
            data = json.loads(source.read_text(encoding="utf-8"))
            target = write_dashboard(data, args.output)
            result = validate_html(target)
            print(f"看板已生成：{target}")
        else:
            result = validate_html(args.html)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, json.JSONDecodeError, DashboardDataError) as exc:
        print(f"看板处理失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
