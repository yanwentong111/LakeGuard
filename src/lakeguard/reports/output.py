from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from ..exceptions import ReportError


def json_text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def write_json(data: dict, path: str | Path | None) -> None:
    if path is None:
        return
    try:
        Path(path).write_text(json_text(data) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ReportError(f"Cannot write JSON output {path}: {exc}") from exc


def write_html(data: dict, path: str | Path) -> None:
    try:
        env = Environment(
            loader=PackageLoader("lakeguard", "reports/templates"),
            autoescape=select_autoescape(["html", "j2"]),
        )
        rendered = env.get_template("report.html.j2").render(
            profile=data["profile"], checks=data["checks"],
            failed_count=data["summary"]["failed"],
        )
        Path(path).write_text(rendered, encoding="utf-8")
    except (OSError, KeyError, ValueError) as exc:
        raise ReportError(f"Cannot write HTML report {path}: {exc}") from exc
