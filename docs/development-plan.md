# LakeGuard 開發計劃

本計劃限定 MVP 範圍：單文件 CSV/Parquet、DuckDB 聚合檢查、Typer CLI、YAML、JSON/HTML、pytest 和 GitHub Actions。每階段完成後再進下一階段；不在本計劃內直接開始實作。

## 階段 0：項目骨架與工具鏈

建立 `src` 包、`pyproject.toml`、Ruff、pytest 配置、CI 基礎工作流和 README 安裝說明。

**驗收標準**：Python 3.11+ 可安裝；`lakeguard --help` 可運行；`ruff check .`、`pytest` 在乾淨環境可運行；GitHub Actions 對 push/PR 執行相同檢查。

## 階段 1：來源讀取與 profile

實現本地 CSV/Parquet 識別、DuckDB 安全讀取、schema 探測及 profile 模型/JSON。

**驗收標準**：兩種格式均能回報行數、欄數、字段名/類型、空值數、唯一值數；大文件不經 Pandas/全量 Python 載入；空文件/零行文件、缺失文件、損壞文件、特殊字符路徑有確定且可理解的行為；`lakeguard profile <file>` 退出碼正確。

## 階段 2：配置與規則引擎

實現 YAML/Pydantic 配置校驗、not_null、unique、range、accepted_values，DuckDB SQL 聚合與一致的規則結果。

**驗收標準**：每項規則均有通過/違規/空數據測試；缺失字段、非法參數、錯誤 YAML 會在 SQL 執行前定位；NULL 策略符合架構文檔；引號/保留字字段安全；規則順序和計數確定；各規則錯誤不阻斷無關規則。

## 階段 3：check CLI 與 JSON

完成 `lakeguard check -c`、結果匯總、穩定 JSON 序列化和退出碼。

**驗收標準**：正常與異常配置夾具可端到端運行；JSON 符合 `schema_version: 1` 約定；全通過返回 0、數據違規返回 1、配置/來源/執行錯誤返回 2；stdout 僅放結果 JSON，診斷到 stderr。

## 階段 4：HTML 報告與使用文檔

以 Jinja2 渲染報告，完成示例配置、完整 README（安裝、命令、退出碼、空值語義、限制）。

**驗收標準**：`--report` 生成可直接打開的 HTML；用戶值 HTML escaping；寫入失敗清楚返回 3 且不留下不完整目標文件；README 命令在 CI/本地可照做；報告展示總結、規則結果及數據概要。

## 階段 5：發布前穩定化

審查依賴/許可、錯誤信息、包構建安裝、CI 矩陣和文檔的一致性。

**驗收標準**：乾淨環境安裝 wheel 後 CLI 正常；CI 覆蓋最低 Python 3.11 和當前支持版本；測試包含 valid/invalid 數據、缺文件、空數據、缺字段、非法 YAML、格式錯誤來源、報告寫入錯誤；Ruff 與全部測試通過；版本/JSON schema/README 命令一致。

## 測試策略

以小型 CSV 和 Parquet 夾具建立可預測結果，正常與異常資料分開存放。單元測試覆蓋配置、SQL 標識符/參數處理、規則邊界；整合測試覆蓋 CLI 完整流程和退出碼；HTML 測試檢查必要內容和轉義。避免測試依賴網絡、外部資料庫或系統服務。基準測試可延後，不應用脆弱的耗時門檻阻斷 CI。

## 主要技術風險

- **DuckDB CSV 語義及版本差異**：空字符串/NULL 推斷可能影響規則結果；固定受支持版本範圍並用夾具鎖定預期。
- **SQL 標識符與來源路徑安全**：用戶控制字段名和路徑，須分別安全引用/參數化；建立包含引號和特殊字符的測試。
- **大型文件資源使用**：聚合查詢避免全量載入 Python，但 distinct 統計和多次規則掃描仍可能昂貴；明確 MVP 資料規模預期，後續再評估合併掃描和近似統計。
- **Parquet/CSV schema 推斷不一致**：結果類型及 min/max JSON 表示需有穩定規則；未知或複合類型應安全降級。
- **HTML 注入/報告敏感信息**：模板自動轉義，避免嵌入不可信原始 HTML；文件路徑可能含私密信息，報告默認本地生成並提示用戶妥善保存。
- **退出碼契約**：數據違規和工具執行錯誤需區分，文檔、CI 和上層腳本測試保持一致。
