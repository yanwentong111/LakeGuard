# LakeGuard CSV bugfix report

Date: 2026-11-03
Environment: Windows, Python 3.13.15 (`.venv`), DuckDB 2.0.0, pytest 9.2.0.

## Root cause

Both order CSVs existed, decoded as UTF-8 without BOM, had comma-separated three-column headers, consistent row widths, and no structurally invalid business values. Their line endings were inconsistent: LF between rows and CRLF at the final row. Python's standard `csv` module accepted them, while DuckDB 2.0.0 CSV dialect auto-detection failed. This common source-read failure caused the profile/rules tests and CLI tests to fail. The configured business anomalies (blank amount, duplicate order ID, negative amount, unknown status) are preserved.

The original first pytest command using system `python` could not run because that Python 3.8 installation has no pytest. All project verification therefore uses the installed Python 3.13 virtual environment.

## Changes

- `examples/data/orders_valid.csv`, `examples/data/orders_invalid.csv`: normalized line endings to LF; no data rows removed or changed.
- `src/lakeguard/sources.py`: use DuckDB's `read_csv` / `read_parquet` Relation API, then create the internal view. The connection still closes on source parse errors and reports a source-specific error.
- `src/lakeguard/rules/engine.py`: unique ignores NULL and reports excess duplicate rows (`N - 1`) rather than duplicate groups.
- `tests/test_core.py`: added regression coverage for Windows paths containing spaces/apostrophe/special chars, headers and inferred column types, malformed encoded CSV, Parquet reading, and duplicate excess-row/NULL semantics.

## Verification

- `.venv\Scripts\python.exe -m pytest -v --tb=long`: initial full diagnostic; 5 failed, 4 passed before the CSV fix.
- `.venv\Scripts\python.exe -m pytest -x -vv -s`: reproduced first CLI failure before fix.
- Direct DuckDB checks: on original mixed-newline files default, header-only, delimiter, and sample-size options failed; after line-ending normalization those four reads succeeded and inferred `order_id BIGINT`, `amount DOUBLE`, `status VARCHAR`.
- `.venv\Scripts\ruff.exe check .`: passed (`All checks passed!`).
- `.venv\Scripts\python.exe -m pytest -v`: passed, **14 passed**.
- `lakeguard --help`: exit 0.
- `lakeguard profile examples/data/orders_valid.csv`: exit 0; 3 rows, 3 columns.
- `lakeguard check -c examples/orders_valid.yaml`: exit 0; all 5 checks passed.
- `lakeguard check -c examples/orders_invalid.yaml --report report.html`: exit 1 as expected; 4 failing checks, JSON emitted, HTML created and includes failed-check count and per-rule results.

## Remaining issues / acceptance

No known CSV read failures remain in the tested cases. The existing CLI output and HTML behavior were verified. The default system `python` is still Python 3.8 and cannot run pytest; invoke project commands from `.venv` (or activate it) to use Python 3.13. The MVP CSV reader currently relies on DuckDB's default CSV inference; configurable CSV parsing options remain outside this focused fix.

MVP acceptance for this CSV bugfix: met. Existing tests and new regression tests pass; Ruff is clean; valid and invalid examples produce the expected data-quality outcomes and exit codes.
