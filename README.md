# MovieTrace

> 每日发现英语影视在 6 个主流流媒体平台（Netflix · Prime Video · Disney+ · Apple TV+ · HBO/Max · Hulu）的热度变化与剧集更新，对照内部 A 库（运营业务库）标记缺口，把可审核的推荐清单同步到飞书表格，供运营挑选并提交内容供应商。

适合接手者、运营、新加入的开发者快速理解项目要做什么、当前在哪儿、怎么用。AI 协作和详细规则见 [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md)。

---

## 项目要解决什么问题

视频网站的内容运营每天面对两类决策：

1. **新热点要不要采购？** —— 哪些新上线 / 新季 / 新爆款值得引进；哪些是噪音。
2. **已采购的剧集有没有掉队？** —— A 库已收录的剧已经播到第几季，TMDb 上更新了多少季，差距在哪。

人工盯榜单 + 翻 TMDb 既慢又漏。MovieTrace 每天自动跑一遍：

- 从公开数据源（TMDb / Trakt / OMDb / FlixPatrol）抓 trending
- 计算可解释的 `hot_score`（0–100，权重可调）
- 与 A 库对照，标记 _新热点未采购_ 和 _已采购但缺最新季_
- 推到飞书三张子表 + Markdown 周报，让运营在熟悉的界面里挑选 / 备注 / 反馈
- 运营每周一次手动拉一次飞书回填到本地，做"V1 → V2"决策证据沉淀

**核心定位**：是"更新追踪 + 中间表" 系统，**不是**推荐系统（不替运营做主观判断），**不是**资源获取系统（不下载），**不是**全网新内容扫描器（只跟踪 hot_score 阈值之上 + A 库已有剧集）。

---

## 当前能做什么（V1 已上线）

| 能力 | 命令 | 频率 |
|------|------|------|
| 全网热点发现（4 源合并 + 评分 + A 库匹配） | `daily-discover` | 每日 cron |
| A 库已收录剧的新季追踪 | `baseline-track` | 每周 |
| Markdown + JSON 导出 | `export-recommendations` / `export-baseline-updates` | 跟着上面 |
| 飞书三张子表同步 | `sync-feishu-table` / `sync-feishu-gap-table` / `sync-feishu-doc` | 跟着导出 |
| 运营反馈回流 + 周报 | `pull-feishu-feedback` / `export-feedback-report` | 每周日手动 |
| 失败告警 | `notify-feishu` | 异常时自动 |

所有命令在 [`docs/context_map.md`](docs/context_map.md) § 3 有完整索引。

**V1 不做**（详见 [`.claude/rules/10-scope-guardrails.md`](.claude/rules/10-scope-guardrails.md)）：用户画像、目标用户契合度评估（V2 LLM 范围）；新集级别（episode）更新追踪（V2 backlog）；自动给供应商发起采购单。

---

## 快速开始

```bash
# 1. 环境
cd MovieTrace
source .venv/bin/activate
pip install -r requirements.txt

# 2. 凭据（放到 ~/.config/movietrace/secrets.json，权限 0600）
#    需要：tmdb.api_read_access_token / omdb.api_keys / trakt.client_id /
#         flixpatrol.api_key / feishu.app_id / feishu.app_secret / feishu.base_app_token /
#         feishu.discovery_table_id / feishu.gap_table_id

# 3. 初始化或检查数据库
sqlite3 data/movietrace.db "select max(version) from schema_migrations;"
# 预期：17

# 4. 跑测试（不消耗 API）
PYTHONPATH=src python -m pytest tests/ -v
# 预期：623 passed

# 5. 跑一次 dry-run 看输出
PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run
PYTHONPATH=src python -m movietrace.cli inspect-baseline
```

日常运行细节（cron / 备份 / 排障）见 [`docs/operations/runbook.md`](docs/operations/runbook.md)。

---

## 数据流速览

```
TMDb / Trakt / OMDb / FlixPatrol
        │ 每日抓
        ▼
  source 快照表（tmdb_trending / trakt_trending / flixpatrol_top10）
        │ 合并 + hot_score
        ▼
  content_updates（事件历史表，B 库主出口）
   │                              │
   │ export                       │ feishu sync
   ▼                              ▼
reports/latest.md+.json    飞书"热点发现"子表
                                  │
                                  ▼
                          运营挑选 / 备注
                                  │ 每周日 pull
                                  ▼
                          reports/feedback/feedback_log_YYYY-Www.md

A 库（upstream_programs/episodes，每次手动 import 刷新）
        │ entity_matching
        ▼
  canonical_items + external_ids → virtual_series
        │ baseline-track 检测新季
        ▼
  content_updates（new_season）+ 飞书"A库缺口"子表
```

完整表结构、字段含义、索引、migrations：[`docs/context_map.md`](docs/context_map.md) § 5。

---

## 文档导航（按读者角色）

| 你是 | 先读 | 然后看 |
|------|------|--------|
| 第一次接手 | 本文件 → [`docs/context_map.md`](docs/context_map.md) | [`docs/operations/runbook.md`](docs/operations/runbook.md) |
| 运营 / 使用者 | 本文件 | [`docs/operations/feishu_feedback_spec.md`](docs/operations/feishu_feedback_spec.md)（飞书字段怎么填）|
| 开发者改代码 | [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) → [`STATE.md`](STATE.md) → [`docs/context_map.md`](docs/context_map.md) | [`docs/tasks/TEMPLATE.md`](docs/tasks/TEMPLATE.md) + [`docs/decisions/`](docs/decisions/) |
| AI 协作 | [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md)（**强制 12 条规则**）| [`STATE.md`](STATE.md) → 任务包 |
| 项目状态 | [`STATE.md`](STATE.md) | [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)（先 `rg`）|
| 决策背景 | [`docs/decisions/README.md`](docs/decisions/README.md) | ADR-0007（系统翻转）/ 0012（事件历史化）/ 0014（schema 清理）/ 0015（飞书文档导入）|

---

## 技术栈

Python 3.12 · SQLite · 仅 stdlib + `requests` 类小依赖（具体见 `requirements.txt`）· 无 web 框架 · 无 ORM。

完整约束（不引入新依赖、不动数据库设计、安全规则等）见 [`CLAUDE.md`](CLAUDE.md) "项目约束" 段。

---

## 项目状态

V1 全部任务包已完成；当前处于 **V1 观察期**，等运营连续用 1–2 个月后用周报数据评估 V2 启动条件。详见 [`STATE.md`](STATE.md) 头部和 [`docs/product_roadmap.md`](docs/product_roadmap.md)。
