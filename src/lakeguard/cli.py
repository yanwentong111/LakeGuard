from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .config import load_config
from .exceptions import LakeGuardError
from .reports.output import json_text, write_html, write_json
from .rules.engine import run_checks
from .sources import DataSource

app = typer.Typer(no_args_is_help=True, help="Local-first data quality checks")


@app.command()
def profile(file: Path) -> None:
    try:
        with DataSource(file) as source:
            data = {"source": {"path": str(source.path), "format": source.format}, **source.profile()}
        typer.echo(json_text(data))
    except LakeGuardError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc


@app.command()
def check(
    config: Annotated[Path, typer.Option("-c", "--config")],
    report: Annotated[Path | None, typer.Option("--report")] = None,
) -> None:
    try:
        cfg, source_path = load_config(config)
        with DataSource(source_path) as source:
            profile_data = source.profile()
            checks = run_checks(source, cfg.rules)
            failed = sum(item["status"] == "failed" for item in checks)
            errors = sum(item["status"] == "error" for item in checks)
            result = {
                "schema_version": 1,
                "source": {"path": str(source.path), "format": source.format},
                "profile": profile_data,
                "checks": checks,
                "summary": {
                    "total": len(checks), "passed": len(checks) - failed - errors,
                    "failed": failed, "errors": errors,
                    "status": "error" if errors else "failed" if failed else "passed",
                },
            }
        typer.echo(json_text(result))
        write_json(result, cfg.output)
        if report is not None:
            write_html(result, report)
        raise typer.Exit(2 if errors else 1 if failed else 0)
    except typer.Exit:
        raise
    except LakeGuardError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc


if __name__ == "__main__":
    app()
