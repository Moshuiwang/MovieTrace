# V1 收口复盘

**日期：** 2026-05-14
**复盘人：** Claude Code（deepseek-v4-pro）+ moshuiwang
**范围：** Phase 1 全部 41 个任务包

---

## V1 最终目标

每日检测全网热门英文影视内容的更新事件，以及 A 库（运营业务库）中已有 TV 剧集的新季更新，写入可审核的推荐清单供运营从中挑选并提交供应商。

---

## 实际完成能力

### 能稳定做什么

| 能力 | 状态 | 说明 |
|------|------|------|
| 三源热度发现 | ✅ | FlixPatrol + TMDb + Trakt，含 fallback 兜底 |
| OMDb/TMDb 富化 | ✅ | IMDb 评分、TMDb 详情，含 TMDb fallback |
| 综合评分 | ✅ | hot_score 0-100，P0/P1/P2 三级，可解释 |
| 基线主动追踪 | ✅ | 300 virtual_series，智能轮询，新季检测 |
| A 库实体匹配 | ✅ | 100% TV 链接率，790/790 |
| MD+JSON 导出 | ✅ | `export-recommendations` |
| 终端查阅 | ✅ | `inspect-updates` / `inspect-api-usage` |
| API 用量日志 | ✅ | 指纹脱敏、按服务查询 |
| 熔断保护 | ✅ | 401/402/403 立即停止，OMDb 多 key 轮转 |
| dry-run | ✅ | 不写业务结果 |
| 测试体系 | ✅ | 495 passed，全 mock 无外部 API |
| CI | ✅ | GitHub Actions，PR + main push |

### 明确不能做什么

- 飞书写入（Phase 1.5 砍掉，改为本地 MD+JSON 导出）
- TV 新集追踪（episode-level，V2 backlog）
- 电影主动追踪（无"季"概念，由功能 1 兜底）
- LLM 契合度判断
- 付费数据源（FlixPatrol 除外）

---

## 与最初设想相比的关键方向变化

| 维度 | 最初设想 | 最终落地 | 决策依据 |
|------|---------|---------|---------|
| 定位 | 推荐系统 + 人工审核 | 更新事件追踪 + 中间表 | ADR-0007 |
| 输出渠道 | 飞书多维表格 | 本地 MD + JSON | 用户决策：飞书从链路移除 |
| 内容来源 | 飞书基线 | A 库（upstream_programs） | 2026-05-12 数据导入 |
| 数据模型 | 全局去重建议池 | 事件历史表 | ADR-0012 |
| FlixPatrol | 验证阶段 | 生产使用（402 阻塞中） | ADR-0003/0006 |
| 飞书基线 | 写入输出 | 仅保留历史表 | 决策 2 |

---

## 当前系统架构

```
A 库（upstream_programs, 只读）
        │
daily-discover ─── 三源抓取 (FP+TMDb+Trakt) ─── OMDb/TMDb 富化 ─── 评分 ─── content_updates (B 库)
        │
baseline-track ─── virtual_series 轮询 ─── 新季检测 ─── content_updates (B 库)
        │
export-recommendations ─── MD + JSON ─── reports/
```

---

## 已知阻塞和剩余风险

| 阻塞/风险 | 影响 | 状态 |
|-----------|------|------|
| FP API 402 | FlixPatrol 所有国家不可用，fallback 前一天数据 | 外部阻塞，无内部修复方案 |
| OMDb 日限额 1000 | 超限后无 fallback | 当前候选量可控 |
| TMDb API 无 SLA | 偶尔 404/5xx | fallback 到 fetch 缓存 |
| Secrets 旧路径 | 仍在用 `/tmp/movietrace_phase0_secrets.json` | deprecation warning 已加 |
| 跨天无新热度表现 | 候选量可能 < 10 | 正常现象，非 bug |

---

## 为什么暂不启动 V2

1. V1 尚未进入真实稳定运行观察期（FP 402 未恢复）
2. 运营尚未反馈具体需求短板
3. V2 LLM/付费 API 成本尚未达成业务共识
4. 当前 495 测试通过，无 pending 功能性修复

V2 启动条件见 [SCOPE.md](../../SCOPE.md) § V2 触发条件。

---

## V1 交付物清单

- `daily-discover` / `baseline-track` / `export-recommendations` / `inspect-updates` / `inspect-api-usage` / `fetch-tmdb-trending` / `fetch-trakt-trending` CLI
- 13 个 DB migrations（schema version 14）
- 7 个 pipeline 模块（discovery / multi_source_merge / omdb_enrichment / scoring / virtual_series / poll_scheduler / baseline_tracking）
- 6 个 source 模块（flixpatrol_api / tmdb / trakt / omdb / tmdb_trending / trakt_trending）
- 12 个 ADR
- 41 个任务包
- 495 自动化测试
- GitHub Actions CI

---

## V1 运行观察期建议

建议在以下条件满足后进入 3-7 天运行观察：
1. FP API 恢复或确认长期不可用后的降级策略
2. 至少连续 3 天执行 `daily-discover`
3. 运营对导出的 MD/JSON 至少反馈一轮

观察期内不做代码重构、不强制启动 V2。
