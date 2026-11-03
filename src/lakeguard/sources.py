from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import duckdb

from .exceptions import SourceError


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _json_value(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


class DataSource:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise SourceError(f"Source file does not exist or is not a file: {self.path}")
        self.format = self.path.suffix.lower().lstrip(".")
        if self.format not in {"csv", "parquet"}:
            raise SourceError(f"Unsupported source format: {self.path.suffix}")
        self.con = duckdb.connect(":memory:")
        self.relation = "_lakeguard_source"
        try:
            if self.format == "csv":
                self.con.read_csv(str(self.path)).create_view(self.relation)
            else:
                self.con.read_parquet(str(self.path)).create_view(self.relation)
            self.columns = self.con.execute(f"DESCRIBE {self.relation}").fetchall()
            self.row_count = self.con.execute(f"SELECT COUNT(*) FROM {self.relation}").fetchone()[0]
        except duckdb.Error as exc:
            self.con.close()
            raise SourceError(f"Could not read {self.format.upper()} source {self.path}: {exc}") from exc

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def column(self, name: str) -> tuple[str, str]:
        for column, dtype, *_ in self.columns:
            if column == name:
                return quote_identifier(column), dtype
        from .exceptions import ColumnNotFoundError

        raise ColumnNotFoundError(f"Column not found: {name}")

    def profile(self) -> dict[str, Any]:
        results = []
        for name, dtype, *_ in self.columns:
            ident = quote_identifier(name)
            nulls, distinct = self.con.execute(
                f"SELECT COUNT(*) FILTER (WHERE {ident} IS NULL), COUNT(DISTINCT {ident}) FROM {self.relation}"
            ).fetchone()
            minimum = maximum = None
            if any(token in dtype.upper() for token in ("INT", "FLOAT", "DOUBLE", "DECIMAL", "DATE", "TIME")):
                minimum, maximum = self.con.execute(
                    f"SELECT MIN({ident}), MAX({ident}) FROM {self.relation}"
                ).fetchone()
            results.append({"name": name, "type": dtype, "null_count": nulls,
                            "distinct_count": distinct, "min": _json_value(minimum), "max": _json_value(maximum)})
        return {"row_count": self.row_count, "column_count": len(self.columns), "columns": results}

    def close(self) -> None:
        self.con.close()





