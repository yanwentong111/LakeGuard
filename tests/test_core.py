from pathlib import Path

import pytest

from lakeguard.config import load_config
from lakeguard.exceptions import ConfigError, SourceError
from lakeguard.models import RuleConfig
from lakeguard.rules.engine import run_checks
from lakeguard.sources import DataSource

ROOT = Path(__file__).parents[1]


def test_profile_and_rules():
    cfg, path = load_config(ROOT / "examples/orders_valid.yaml")
    source = DataSource(path)
    assert source.profile()["row_count"] == 3
    assert all(r["status"] == "passed" for r in run_checks(source, cfg.rules))
    source.close()


def test_invalid_orders():
    cfg, path = load_config(ROOT / "examples/orders_invalid.yaml")
    source = DataSource(path)
    results = run_checks(source, cfg.rules)
    assert [r["invalid_rows"] for r in results] == [1, 1, 1, 1]
    source.close()


def test_missing_column_is_error():
    _cfg, path = load_config(ROOT / "examples/orders_valid.yaml")
    source = DataSource(path)
    assert run_checks(source, [RuleConfig(type="unique", column="absent")])[0]["status"] == "error"
    source.close()


def test_missing_file():
    with pytest.raises(SourceError):
        DataSource(ROOT / "no-such.csv")


def test_empty_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("x\n", encoding="utf-8")
    assert DataSource(path).row_count == 0


def test_bad_yaml(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("source: [\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_identifier_with_quote(tmp_path):
    path = tmp_path / "quoted.csv"
    path.write_text('"odd""name",v\na,1\n', encoding="utf-8")
    source = DataSource(path)
    assert run_checks(source, [RuleConfig(type="not_null", column='odd"name')])[0]["status"] == "passed"
    source.close()




def test_duplicate_excess_rows_and_null_ignored(tmp_path):
    path = tmp_path / "duplicates.csv"
    path.write_text("id\n7\n7\n7\n\n", encoding="utf-8", newline="")
    with DataSource(path) as source:
        result = run_checks(source, [RuleConfig(type="unique", column="id")])[0]
    assert result["invalid_rows"] == 2


def test_csv_path_spaces_and_special_characters(tmp_path):
    path = tmp_path / "orders #1's.csv"
    path.write_text("id,value\n1,2\n", encoding="utf-8", newline="")
    with DataSource(path) as source:
        assert source.row_count == 1
        assert [item[0] for item in source.columns] == ["id", "value"]


def test_csv_type_inference_and_fields(tmp_path):
    path = tmp_path / "typed.csv"
    path.write_text("count,price,label\n2,1.25,x\n", encoding="utf-8", newline="")
    with DataSource(path) as source:
        profile = source.profile()
    assert [column["name"] for column in profile["columns"]] == ["count", "price", "label"]
    assert "INT" in profile["columns"][0]["type"]
    assert "DOUBLE" in profile["columns"][1]["type"]
    assert profile["columns"][2]["type"] == "VARCHAR"


def test_structurally_malformed_csv_fails(tmp_path):
    path = tmp_path / "malformed.csv"
    path.write_bytes(b'a,b\n1,2\n\xff,2\n')
    with pytest.raises(SourceError):
        DataSource(path)


def test_parquet_source(tmp_path):
    import duckdb

    csv_path = tmp_path / "input.csv"
    csv_path.write_text("id,value\n1,ok\n", encoding="utf-8", newline="")
    parquet_path = tmp_path / "input.parquet"
    duckdb.connect().execute(
        "COPY (SELECT * FROM read_csv_auto(?)) TO ? (FORMAT PARQUET)",
        [str(csv_path), str(parquet_path)],
    )
    with DataSource(parquet_path) as source:
        assert source.row_count == 1
        assert source.format == "parquet"
