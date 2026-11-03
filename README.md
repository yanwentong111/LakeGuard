# LakeGuard

[![CI](https://github.com/<owner>/LakeGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/LakeGuard/actions/workflows/ci.yml)

**在本地快速检查 CSV 和 Parquet 数据质量。** LakeGuard 使用 DuckDB 在进程内读取文件并执行 SQL 检查，通过命令行和 YAML 配置输出 JSON 结果或静态 HTML 报告。无需启动数据库服务器，无需上传数据。

> 将徽章链接中的 `<owner>` 替换为 GitHub 用户名或组织名后再发布。

## 解决什么问题

数据文件经常在进入分析、报表或后续处理前就带有空值、重复键、越界数值或未预期的枚举值。人工抽查难以持续，也容易漏掉问题；为了只检查本地文件而部署一套数据库服务又显得过重。

LakeGuard 面向数据工程师、数据分析师和 Python 开发者，提供一套可重复、可脚本化的本地检查流程：选择 CSV/Parquet 文件，在 YAML 写出检查规则，执行命令并查看结果。数据保留在本机。

## 主要功能

- 使用 DuckDB 直接读取 CSV 和 Parquet，不把整份数据加载到 Pandas。
- 查看行数、列数、字段名、推断类型、NULL 数、distinct 数，以及适用类型的最小值和最大值。
- 执行 `not_null`、`unique`、`min`、`max`、`accepted_values` 检查。
- 输出结构化 JSON，并可生成静态 HTML 报告。
- 适合本地运行和 CI：通过进程退出码区分检查通过、数据失败和执行错误。

## 安装

要求 Python 3.11 或更新版本。建议在项目虚拟环境中安装：

```bash
git clone https://github.com/<owner>/LakeGuard.git
cd LakeGuard
python -m venv .venv
```

激活环境：

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

安装可运行版本：

```bash
python -m pip install -e .
```

开发时安装测试和 lint 工具：

```bash
python -m pip install -e ".[dev]"
```

## 快速开始

在仓库根目录运行：

```bash
lakeguard profile examples/data/orders_valid.csv
lakeguard check -c examples/orders_valid.yaml
lakeguard check -c examples/orders_invalid.yaml --report report.html
```

第三条命令会识别示例数据中的质量问题，返回退出码 `1` 是预期结果，同时生成 `report.html`。检查详情以 JSON 写到终端；配置中如设置了 `output`，也会写入 JSON 文件。

## 使用配置

```yaml
dataset: orders
source: data/orders_valid.csv
output: results.json
rules:
  - type: not_null
    column: order_id
  - type: unique
    column: order_id
  - type: min
    column: amount
    value: 0
  - type: max
    column: amount
    value: 1000
  - type: accepted_values
    column: status
    values: [new, paid, cancelled]
```

`source` 相对路径以 YAML 文件所在目录为基准。`output` 是 JSON 输出路径，以运行命令时的当前工作目录为基准。

支持的规则：

| 规则 | 检查内容 | 配置示例 |
|---|---|---|
| `not_null` | 字段没有 NULL | `- type: not_null` |
| `unique` | 非 NULL 值不重复 | `- type: unique` |
| `min` | 非 NULL 数值不小于下限 | `- type: min` 并设置 `value` |
| `max` | 非 NULL 数值不大于上限 | `- type: max` 并设置 `value` |
| `accepted_values` | 非 NULL 值属于允许列表 | `- type: accepted_values` 并设置 `values` |

规则都需要 `column` 字段。`unique` 忽略 NULL；某个非 NULL 值出现 N 次时，超过首次出现的 N−1 行计为无效。除 `not_null` 外，其余规则也忽略 NULL。CSV 表头、分隔符、类型和空值解释使用 DuckDB 的 CSV 自动识别行为。

## 命令

### 查看数据概况

```bash
lakeguard profile <file>
```

输出 JSON，包含来源格式和概览字段。支持 `.csv` 和 `.parquet` 文件。

### 执行 YAML 检查

```bash
lakeguard check -c <config.yaml>
```

### 同时生成 HTML 报告

```bash
lakeguard check -c <config.yaml> --report <output.html>
```

### 退出码

| 退出码 | 含义 |
|---:|---|
| `0` | 所有质量规则通过 |
| `1` | 至少一条质量规则失败（数据不符合规则） |
| `2` | 配置、来源文件或执行错误 |

## 输入与输出示例

输入文件 `examples/data/orders_invalid.csv`：

```csv
order_id,amount,status
1,10.5,new
1,-5,unknown
3,,paid
```

对应 YAML `examples/orders_invalid.yaml` 的规则会检查 `amount` 非空且不小于 `0`、`order_id` 唯一，以及 `status` 属于允许值集合。

执行：

```bash
lakeguard check -c examples/orders_invalid.yaml --report report.html
```

终端输出 JSON（绝对路径因运行位置而异）：

```json
{
  "schema_version": 1,
  "source": {"path": ".../orders_invalid.csv", "format": "csv"},
  "profile": {"row_count": 3, "column_count": 3, "columns": []},
  "checks": [
    {"rule_name": "not_null", "column": "amount", "status": "failed", "checked_rows": 3, "invalid_rows": 1, "message": "1 invalid row(s)"},
    {"rule_name": "unique", "column": "order_id", "status": "failed", "checked_rows": 3, "invalid_rows": 1, "message": "1 invalid row(s)"},
    {"rule_name": "min", "column": "amount", "status": "failed", "checked_rows": 3, "invalid_rows": 1, "message": "1 invalid row(s)"},
    {"rule_name": "accepted_values", "column": "status", "status": "failed", "checked_rows": 3, "invalid_rows": 1, "message": "1 invalid row(s)"}
  ],
  "summary": {"total": 4, "passed": 0, "failed": 4, "errors": 0, "status": "failed"}
}
```

完整输出会在 `profile.columns` 中包含每个字段的类型、NULL 数、distinct 数及可用的 min/max。HTML 报告显示总行列数、失败检查数量和逐规则状态。该示例检查失败，所以命令退出码为 `1`，不是 CLI 执行错误。

## 开发与测试

```bash
python -m pytest -v
ruff check .
```

GitHub Actions 会在 Python 3.11、3.12 和 3.13 上运行 lint、测试和 CLI 帮助命令。

## 文档

- [系统架构](docs/architecture.md)
- [开发计划](docs/development-plan.md)
- [CSV 故障修复与验证记录](docs/bugfix-report.md)

## 许可证

[MIT](LICENSE)

