# MovieTrace 日常运行手册

> **目的：** 让接手者能独立完成日常运行和排障。
> **最后更新：** 2026-05-23

---

## 1. 首次接手检查

```bash
# 确认 Python 环境和依赖
cd ~/MovieTrace
source .venv/bin/activate
pip install -r requirements.txt

# 确认数据库状态
sqlite3 data/movietrace.db "select max(version) from schema_migrations;"
# 预期输出：17

# 确认 secrets 可用（只检查字段，不打印密钥）
python -c "import json, pathlib; p=pathlib.Path.home()/'.config/movietrace/secrets.json'; s=json.loads(p.read_text()); req=[('tmdb','api_read_access_token'),('omdb','api_keys'),('trakt','client_id'),('flixpatrol','api_key'),('feishu','app_id'),('feishu','app_secret')]; missing=[f'{a}.{b}' for a,b in req if not (s.get(a) or {}).get(b)]; print('OK' if not missing else 'missing: '+', '.join(missing)); raise SystemExit(bool(missing))"

# 确认配置
cat config.yaml

# 跑全量测试（不触发外部 API）
PYTHONPATH=src python -m pytest tests/ -v
```

---

## 2. 数据库备份和 schema 检查

```bash
# 备份（含时间戳）
cp data/movietrace.db data/movietrace_backup_$(date +%Y%m%d_%H%M).db

# 检查 schema version
sqlite3 data/movietrace.db "select max(version) from schema_migrations;"

# 检查近期 content_updates
sqlite3 data/movietrace.db "select count(*) from content_updates where created_at > datetime('now', '-7 days');"
```

---

## 3. 每日运行命令

### 3.1 核心：每日发现

```bash
# dry-run 模式（不写入 B 库，推荐日常先用这个看结果）
PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run

# commit 模式（只写入热点发现 content_updates）
PYTHONPATH=src python -m movietrace.cli daily-discover
```

### 3.2 查阅结果

```bash
# 终端查看最近 7 天更新事件
PYTHONPATH=src python -m movietrace.cli inspect-updates --days 7

# 查看更久范围
PYTHONPATH=src python -m movietrace.cli inspect-updates --days 30
```

### 3.3 导出给运营

```bash
# 导出最近 7 天的热点 MD + JSON 报告
PYTHONPATH=src python -m movietrace.cli export-recommendations --days 7

# 指定输出目录
PYTHONPATH=src python -m movietrace.cli export-recommendations --days 7 --output-dir reports/
```

### 3.4 开发环境端到端验收

开发环境和生产环境不是同一目录，也不是同一个 SQLite 文件。开发环境完整验收默认跑真实 commit 链路，不用 `--dry-run`：

```bash
./scripts/local_e2e_run.sh
```

该脚本对齐生产 `scripts/daily_run.sh`：

```text
daily-discover → export-recommendations → sync-feishu-table → sync-feishu-doc → notify-feishu
```

开发验收关注：

- 脚本退出码为 0
- `reports/logs/local_e2e_*.log` 末尾显示 `状态: OK`
- `reports/logs/discover_stats_YYYYMMDD.json` 中 `written` 符合预期
- `reports/logs/sync_stats_YYYYMMDD.json` 中 `errors=0`
- `data/pipeline_heartbeat.json` 中 `status=done`

跑完后用 Feishu CLI 只读查多维表格：

```bash
source .venv/bin/activate
PYTHONPATH=src python - <<'PY' > /tmp/movietrace_feishu_cli_env.sh
from movietrace.config import load_secrets
f = (load_secrets().get("feishu") or {})
print("APP_TOKEN=" + f.get("base_app_token", ""))
print("TABLE_ID=" + f.get("discovery_table_id", ""))
PY
source /tmp/movietrace_feishu_cli_env.sh

RUN_DATE=$(date +%Y-%m-%d)
feishu bitable record list "$APP_TOKEN" "$TABLE_ID" \
  --page_size 5 \
  --filter "{\"conjunction\":\"and\",\"conditions\":[{\"field_name\":\"同步批次\",\"operator\":\"is\",\"value\":[\"$RUN_DATE\"]}]}"

rm -f /tmp/movietrace_feishu_cli_env.sh
```

注意：生产 cron 当前导出 `--days 1`，所以同一“同步批次”可能同时包含今日和昨日的 `content_update_id`。这属于生产口径，不是同步重复。

### 3.5 基线追踪（独立命令）

```bash
# 例行运行基线新季检测（按 TMDb 状态筛选仍可能更新的剧集）
PYTHONPATH=src python -m movietrace.cli baseline-track --mode routine

# 一次性追平全部非 skip 剧集
PYTHONPATH=src python -m movietrace.cli baseline-track --mode catch-up

# 导出最近 7 天的基线新季独立报告
PYTHONPATH=src python -m movietrace.cli export-baseline-updates --days 7

# 上层调度可每周调用
./scripts/baseline_run.sh
```

---

## 4. dry-run vs commit 模式

| 维度 | dry-run | commit |
|------|---------|--------|
| API 调用 | 完整执行 | 完整执行 |
| 评分计算 | 完整执行 | 完整执行 |
| content_updates 写入 | **不写入** | 写入 |
| canonical_items 注册 | **不注册** | 自动注册 |
| 导出 latest 报告 | 不覆盖 | 覆盖 `reports/latest.*` |
| 飞书多维表格同步 | 不同步 | 真实 upsert |
| 飞书通知 | 不发送 | 真实发送 |
| baseline local_max 回写 | 不适用于 `daily-discover` | 由独立 `baseline-track` 回写 |
| 终端输出 | 显示 "would be registered" | 显示 "auto_registered" |

**原则：**

- 开发环境完整验收：直接跑 `./scripts/local_e2e_run.sh` commit 模式，覆盖 DB 写入、导出、飞书 upsert、通知。
- 单点调试或不想写表时：才使用 `daily-discover --dry-run`。
- 生产环境人工补跑：仍按任务包或 runbook 明确步骤执行，不用开发环境的宽松标准替代生产门禁。

---

## 5. Secrets 路径与部署

**本地运行：** `~/.config/movietrace/secrets.json`（权限 0600，不进 git）

**CI/CD：** push main → GitHub Actions 自动跑测试 + SSH 部署 + 从 GitHub Secrets 重新生成 secrets.json。密钥变更只需在 GitHub → Settings → Secrets 里修改。

**secrets.json 必填字段：**
```json
{
  "feishu": {
    "app_id": "...", "app_secret": "...", "base_app_token": "...",
    "discovery_table_id": "...", "gap_table_id": "...",
    "doc_folder_token": "...", "notify_chat_id": "..."
  },
  "tmdb": { "api_read_access_token": "eyJ..." },
  "omdb": { "api_keys": ["key1", "key2"] },
  "trakt": { "client_id": "..." },
  "flixpatrol": { "api_key": "..." }
}
```

---

## 6. 常见失败与排障

### 6.1 FP 402 Payment Required

```
flixpatrol circuit breaker: HTTP 402 — stopping all FP requests
```

- **原因：** FlixPatrol 订阅到期
- **影响：** FP 数据 fallback 到最近一天有效 snapshot（30 天内）
- **处理：** 确认订阅状态；系统会自动熔断（仅 1 次请求），不影响 TMDb/Trakt 流程

### 6.2 OMDb key 失效

```
OMDb key <fingerprint> returned 401, rotating to next key
```

- **原因：** key 过期或限额用尽
- **影响：** 自动切换到下一个 key；所有 key 耗尽后熔断
- **处理：** 在 `secrets.json` 的 `omdb.api_keys` 中添加新 key

### 6.3 TMDb/Trakt 请求失败

```
Fetching TMDb trending... FAILED
```

- **原因：** 网络问题、API 限流、token 过期
- **影响：** 该源 fallback 到最近一天有效 snapshot（30 天内）
- **处理：** 检查网络和 token；fallback 数据会标记在终端和导出报告中

### 6.4 源数据状态查看

终端 `daily-discover` 输出底部会显示每个 source 的状态：

```
Source data:
  FlixPatrol: fallback from 2026-05-13
  TMDb: fresh 2026-05-14
  Trakt: fresh 2026-05-14
```

热点导出报告 MD 头部也包含"数据源状态"区块。baseline 独立报告不展示热点源状态。

---

## 7. API 用量检查

```bash
# 查看今日 API 用量
PYTHONPATH=src python -m movietrace.cli inspect-api-usage --date $(date +%Y-%m-%d)

# 查看最近 7 天
PYTHONPATH=src python -m movietrace.cli inspect-api-usage --days 7

# 只看 OMDb
PYTHONPATH=src python -m movietrace.cli inspect-api-usage --days 7 --service omdb
```

---

## 8. 故障恢复

### 数据库损坏

```bash
# 从最新备份恢复
cp data/movietrace_backup_YYYYMMDD_HHMM.db data/movietrace.db

# 重新执行 migration
PYTHONPATH=src python -c "from movietrace.db.schema import initialize_database; initialize_database('data/movietrace.db')"
```

### 重置为空库

```bash
# 先保留旧库，再初始化一个空库
mv data/movietrace.db data/movietrace_reset_backup_$(date +%Y%m%d_%H%M).db
PYTHONPATH=src python -c "from movietrace.db.schema import initialize_database; initialize_database('data/movietrace.db')"
```
