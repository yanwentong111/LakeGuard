"""DuckDB-backed quality rules."""
from __future__ import annotations

from typing import Any

import duckdb

from ..exceptions import ColumnNotFoundError, RuleExecutionError
from ..models import RuleConfig
from ..sources import DataSource


def run_rule(source: DataSource, rule: RuleConfig) -> dict[str, Any]:
    ident, _dtype = source.column(rule.column)
    relation = source.relation
    try:
        if rule.type == "not_null":
            invalid = source.con.execute(f"SELECT COUNT(*) FROM {relation} WHERE {ident} IS NULL").fetchone()[0]
        elif rule.type == "unique":
            invalid = source.con.execute(
                f"SELECT COALESCE(SUM(duplicate_count - 1), 0) FROM "
                f"(SELECT COUNT(*) AS duplicate_count FROM {relation} "
                f"WHERE {ident} IS NOT NULL GROUP BY {ident} HAVING COUNT(*) > 1) duplicates"
            ).fetchone()[0]
        elif rule.type in {"min", "max"}:
            operator = "<" if rule.type == "min" else ">"
            invalid = source.con.execute(
                f"SELECT COUNT(*) FROM {relation} WHERE {ident} IS NOT NULL AND {ident} {operator} ?",
                [rule.value],
            ).fetchone()[0]
        else:
            values = rule.values or []
            marks = ", ".join("?" for _ in values)
            invalid = source.con.execute(
                f"SELECT COUNT(*) FROM {relation} WHERE {ident} IS NOT NULL AND {ident} NOT IN ({marks})",
                values,
            ).fetchone()[0]
    except duckdb.Error as exc:
        raise RuleExecutionError(f"Rule {rule.type} on column {rule.column}: {exc}") from exc
    return {"rule_name": rule.type, "column": rule.column,
            "status": "failed" if invalid else "passed", "checked_rows": source.row_count,
            "invalid_rows": invalid, "message": f"{invalid} invalid row(s)"}


def run_checks(source: DataSource, rules: list[RuleConfig]) -> list[dict[str, Any]]:
    results = []
    for rule in rules:
        try:
            results.append(run_rule(source, rule))
        except (ColumnNotFoundError, RuleExecutionError) as exc:
            results.append({"rule_name": rule.type, "column": rule.column, "status": "error",
                            "checked_rows": source.row_count, "invalid_rows": 0, "message": str(exc)})
    return results
