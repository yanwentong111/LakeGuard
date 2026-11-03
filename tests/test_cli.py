from pathlib import Path

from typer.testing import CliRunner

from lakeguard.cli import app

ROOT = Path(__file__).parents[1]
runner = CliRunner()

def test_cli_exit_codes():
    good = runner.invoke(app, ["check", "-c", str(ROOT / "examples/orders_valid.yaml")])
    bad = runner.invoke(app, ["check", "-c", str(ROOT / "examples/orders_invalid.yaml")])
    assert good.exit_code == 0
    assert bad.exit_code == 1

def test_html_report(tmp_path):
    out = tmp_path / "report.html"
    result = runner.invoke(
        app,
        ["check", "-c", str(ROOT / "examples/orders_invalid.yaml"), "--report", str(out)],
    )
    assert result.exit_code == 1
    html = out.read_text(encoding="utf-8")
    assert "LakeGuard quality report" in html
    assert "Failed checks: 4" in html
    assert "unknown" not in html
    assert "not_null" in html
    assert "accepted_values" in html


def test_missing_config_returns_execution_error():
    result = runner.invoke(app, ["check", "-c", str(ROOT / "missing.yaml")])
    assert result.exit_code == 2
    assert "Invalid config" in result.stderr
