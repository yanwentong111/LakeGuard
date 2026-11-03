# LakeGuard 開發約定

## 技術約束

- 支持 Python 3.11+；使用 `pyproject.toml` 和 `src/lakeguard` 標準 src 布局。
- MVP 依賴限定於 DuckDB、Typer、Pydantic、PyYAML、Jinja2；開發依賴 pytest、Ruff。不得引入 Spark、Kafka、Redis、PostgreSQL、Docker 服務依賴、前端框架或付費 API。
- Local-first、無服務器依賴。禁止為 profile/check 將整個文件載入 Pandas 或 Python 記憶體；優先在 DuckDB 執行 SQL 聚合。
- CLI 與核心邏輯分離；使用 Pydantic 結構化輸入/輸出模型及型別註解。
- 用戶路徑、字段名、配置值不可直接拼接進 SQL；字段先按 schema 驗證並安全引用，數據值使用參數化。禁止任意 SQL 配置入口。

## 測試規範

- 使用 pytest；新增規則須覆蓋通過、違規、NULL、空數據與邊界情況。
- 同時維護正常和異常 CSV/Parquet 測試夾具；測試缺文件、缺字段、非法 YAML/配置及不可寫報告路徑等錯誤。
- CLI 測試需驗證 stdout/stderr、退出碼和 JSON 結構；報告測試需驗證 HTML 轉義。
- 測試保持離線、確定性，不依賴時鐘精度、外部服務或脆弱耗時門檻。
- 提交前執行 `ruff check .` 和 `pytest`；修復所有新增失敗。

## 開發約定

- 規則結果穩定排序，狀態固定使用 `passed`、`failed`、`error`；空值語義遵守 `docs/architecture.md`。
- 將底層錯誤包裝為可定位的 LakeGuard 異常，保留異常鏈；一般 CLI 錯誤不顯示 traceback，診斷輸出到 stderr。
- 對用戶可見的行為、配置字段、JSON schema 或退出碼變更，須同步更新架構/使用文檔和測試。
- 模組保持單一職責；不在 CLI 中放檢測 SQL，不在規則中處理終端輸出。
- 新增依賴須說明必要性並確認不違反技術約束；保持依賴精簡。
