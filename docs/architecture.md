# LakeGuard 架构设计

## 1. 目标与边界

LakeGuard 是 Python 3.11+ 的本地数据质量工具。用户用 CLI 和 YAML 操作 CSV/Parquet 文件；DuckDB 在进程内执行 SQL，不启动数据库服务、不要求 Pandas，也不上传数据。核心执行路径应采用投影/聚合查询，避免将完整数据集读入 Python 内存。

MVP 提供数据概览、空值、唯一性、数值范围和枚举规则，并输出机器可读 JSON 与可选 HTML 报告。项目不在此阶段实现服务端、调度器或 Web UI。

## 2. 分层与执行流程

```text
Typer CLI -> 配置加载/校验 -> 用例编排 -> DuckDB 数据访问与 SQL 检查
                                  |-> 结构化结果模型 -> JSON 输出
                                                        -> Jinja2 HTML 报告
```

- **CLI 层**：参数解析、输出呈现、退出码；不包含检测 SQL 或业务判断。
- **配置层**：读取 YAML、校验版本/字段/规则；将解析错误转成带文件和位置的信息。
- **用例层**：profile/check 的流程编排、规则调度、结果汇总。
- **数据访问层**：识别 CSV/Parquet、建立 DuckDB 只读查询上下文、探测 schema、执行聚合 SQL。
- **规则层**：规则输入语义和 SQL 表达；规则结果归一化。每项规则具有稳定 ID 与确定性状态。
- **模型层**：Pydantic 配置和输出模型，隔离 CLI、引擎和序列化。
- **报告层**：JSON 序列化和 Jinja2 HTML 渲染；模板对用户数据转义。

## 3. 建议目录结构

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── docs/
│   ├── architecture.md
│   └── development-plan.md
├── src/lakeguard/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── exceptions.py
│   ├── models.py
│   ├── profile.py
│   ├── runner.py
│   ├── sources.py
│   ├── sql.py
│   ├── rules/
│   │   ├── __init__.py
│   │   └── ...
│   └── reports/
│       ├── __init__.py
│       ├── json.py
│       ├── html.py
│       └── templates/report.html.j2
└── tests/
    ├── fixtures/{valid,invalid}/
    ├── test_config.py
    ├── test_profile.py
    ├── test_rules.py
    └── test_cli.py
```

## 4. 配置格式

建議採用明確版本字段，規則列表便於擴展。`source.path` 相對路徑以配置文件所在目錄解析；命令列顯式指定的路徑則按當前工作目錄解析。

```yaml
version: 1
source:
  path: data/orders.parquet
  # format: parquet # 可選；省略時由副檔名判斷
checks:
  - type: not_null
    column: order_id
  - type: unique
    column: order_id
  - type: range
    column: amount
    min: 0
    max: 100000
  - type: accepted_values
    column: status
    values: [new, paid, cancelled]
```

驗證要求：未知版本、未知規則類型、重複/空規則 ID（若引入 ID）、缺少必需參數、錯誤型別及反向範圍均在執行 SQL 前拒絕。第一版自動給規則穩定序號/ID，如 `check_001`；若使用者規則有 `name`，可用作顯示名稱但不能影響 SQL 安全性。

空值策略：`not_null` 將 SQL NULL 計為空；CSV 空字符串由 DuckDB CSV reader 的預設解析語義處理，MVP 文件須明示此行為，不暗中把空白字符串、`NA` 等任意字串都視作 NULL。`unique` 忽略 NULL，重複只在非 NULL 值間計數；需在報告中揭示此策略。空資料集的 `not_null`、`unique` 視為通過，`range`/`accepted_values` 也因沒有違規列而通過，profile 行數為 0；全部行數/欄位數仍需明確回報。

## 5. 結果模型與 JSON

頂層包含 schema 版本、來源摘要、概覽、規則結果和總結。時間使用 ISO 8601 UTC；不輸出本機絕對路徑之外不必要的敏感資訊（預設保留配置中的路徑以利定位，報告使用者可自行保護）。計數為整數，測試結果不依賴時間字段。

```json
{
  "schema_version": 1,
  "source": {"path": "data/orders.parquet", "format": "parquet"},
  "profile": {"row_count": 3, "column_count": 2,
    "columns": [{"name": "order_id", "type": "BIGINT", "null_count": 0,
      "distinct_count": 3, "min": 1, "max": 3}]},
  "checks": [{"id": "check_001", "type": "not_null", "column": "order_id",
    "status": "passed", "checked_rows": 3, "failed_rows": 0,
    "message": "No NULL values found."}],
  "summary": {"total": 1, "passed": 1, "failed": 0, "errors": 0,
    "status": "passed"}
}
```

狀態集合：check `passed|failed|error`；總結 `passed|failed|error`，優先級為 error、failed、passed。`failed` 表示規則有效但數據違規；`error` 表示該規則無法執行。JSON 使用 UTF-8、穩定字段與規則順序，數值不可表示時轉成 `null` 或明確字符串策略並測試。

## 6. CLI 契約

- `lakeguard profile <file>`：概覽資料；默認輸出 JSON，支持 `--format json|table`（若 MVP 時間允許，否則只提供 JSON）。不存在/不可讀/格式錯誤來源輸出 stderr 並返回錯誤碼。
- `lakeguard check -c <config.yaml>`：執行所有規則，stdout 輸出 JSON。檢查完成即使有數據違規仍輸出完整結果。
- `lakeguard check -c <config.yaml> --report <output.html>`：同時產生 HTML 報告；報告路徑父目錄不存在或不可寫時清楚報錯。
- 建議退出碼：`0` 全部通過；`1` 至少一項規則 failed；`2` 配置/輸入/執行錯誤；`3` 報告輸出錯誤。CLI help/version 成功返回 0。測試固定驗證退出碼與 stdout/stderr 分流。

## 7. SQL 與輸入安全

路徑不可直接拼接成 SQL 字串。來源路徑使用 DuckDB 支持的參數化 table function/安全註冊方式，並限制來源為普通本地文件及 CSV/Parquet。欄位名不能當 SQL 值參數：從 DuckDB schema 取得欄位並用 DuckDB identifier quoting 函數安全引用，拒絕不存在欄位；不可自行以字符串替換逃逸。規則值一律參數化。SQL 中只使用內部生成的臨時關係名，不接受用戶表名；禁止任意 SQL 配置入口。限制擴展自動安裝/加載，避免網絡或服務依賴。若 DuckDB 特定版本無法安全參數化來源路徑，使用嚴格引用函數並針對引號、反斜線和特殊路徑測試。

## 8. 錯誤處理

定義 `LakeGuardError` 基類及可定位子類：`ConfigError`、`SourceError`、`ColumnNotFoundError`、`RuleExecutionError`、`ReportError`。底層 DuckDB/Pydantic/YAML 異常在邊界包裝，保留原因鏈；面向使用者信息帶配置路徑/規則 ID/字段名及修復提示，不打印 traceback。`--verbose` 可輸出診斷細節。單項規則錯誤時應記錄為 error 並繼續其他獨立規則；來源無法讀取或 schema 探測失敗則整次執行中止。報告寫入使用明確編碼並避免留下半成品（臨時文件後原子替換）。

## 9. 未來方向

MVP 後可評估：可選閾值/容忍比例、自定義 SQL（需安全設計）、多文件/目錄、CSV 解析選項、趨勢與基線、分區/大文件性能優化、Python API、插件規則、CI 友好摘要、更多報告格式。任何增加都需保持本地優先與無服務依賴原則；不承諾未評估的向後兼容。
