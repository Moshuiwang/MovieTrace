# Agent 身份卡

- **工具：** Claude Code（VSCode 插件）
- **模型：** Sonnet 4.6(前半场调研) → Opus 4.7(后半场规划)
- **模型 ID：** `claude-sonnet-4-6` + `claude-opus-4-7`
- **运行环境：** Python 3.12 + `.venv/` + Linux 6.8.0
- **会话时间：** 2026-05-13 11:00 +08 ~ 12:41 +08(~1.7 小时)
- **起止 commit：** `248743c` → (本次提交后更新)

---

# 今日工作主线

## 1. 功能完成度核查(11:00-11:15)

用户提问"当前功能需求是否完成",对照 STATE.md + 需求文档 + 实际代码三方对账:

- **结论:** V1.5 MVP 架构层面全部完成,317 测试通过,但**核心功能 1(全网热门发现)从未真实跑出内容**。content_updates 表 6 条记录全部来自功能 2(基线新季追踪),功能 1 路径下 0 条。

## 2. 功能 1 实质性验证(11:15-11:35)

跑 `run_discovery(date_from='2026-05-11', dry_run=True)` 实地诊断:

```
89 个候选 → 全部 P3(最高 hot_score=49)
```

逐因子分解发现 **`ext_data` 永远为 None**:
- TMDb 社区热度(权重 15%):0 分
- Trakt 社区热度(权重 10%):0 分
- TMDb 评分(权重 10%):0 分
- IMDb 评分(权重 10%):0 分
- 新鲜度(权重 5%):0 分(release_date 缺失)

**根本原因:** `_enrich_candidate` 从不查询外部 API,55% 权重数据全部为零,即使 FlixPatrol 100 满分也只能堆到 49 分,永远无法越过 P0/P1/P2 阈值。

**关键事件时间:** 11:32 +08 拿到完整诊断结论,确认这不是权重设计问题而是数据管道断路。

## 3. 三源 API 可行性调研(11:35-12:10)

### TMDb
- `/trending/all/day` / `/tv/popular` / `/movie/popular` 全部可批量拉取
- 每次返回 20 条,可分页(trending 最多 500 页)
- 当天内容固定,适合每日定时拉一次
- **但与 FP 重叠度只有 33%**(老片榜单上 FP 但不在 TMDb popularity 前 200)

### Trakt
- 实测发现 **Cloudflare 1010 阻断默认 Python UA**,需 Firefox UA 才能通过
- `/shows/trending?limit=500` + `/movies/trending?limit=500` 一次拉全量(≈730 条)
- 每条带 `watchers` + `rating` + `votes` + `tmdb_id`
- 与 FP 重叠度 45%

### OMDb
- 无任何列表/榜单端点,**只能逐条按 imdb_id 查**
- FP 数据 97% 有 imdb_id(需补 `tt` 前缀+补零到 7 位)
- 配额 1000 次/天,FP 全量 90 条无压力,缓存 24h

**关键决策(12:08 +08):** TMDb/Trakt 热度榜单**不能作为 FP 富化索引**(重叠度低,热度标准不同)。三源应作为**独立候选来源**取并集,而非 FP 单入口+其他源补字段。

## 4. Phase 1.7 任务包生成(12:10-12:40)

用户决策的关键参数:
- TMDb 候选范围:trending/day + tv/popular + movie/popular 各 3 页(≈180 条/天)
- Trakt 候选范围:trending shows+movies 全量(≈730 条/天)
- 多源去重:按 tmdb_id 优先,imdb_id 次之
- 输出阈值:P2 及以上(hot_score ≥ 50)

生成 5 个原子任务包:

| 编号 | 范围 | 核心改动 |
|------|------|---------|
| P1.7-A | schema migration 007 | 新增 `tmdb_trending` + `trakt_trending` 表 |
| P1.7-B | TMDb 采集 | `TmdbTrendingClient` + `pipeline/tmdb_trending.py` |
| P1.7-C | Trakt 采集 + 修 UA | 修复 `http.py` 默认 UA(解决 Cloudflare) |
| P1.7-D | **核心改造** | `multi_source_merge.py` + `omdb_enrichment.py` + 改造 discovery |
| P1.7-E | 查阅 CLI + 验收 | `inspect-updates` 子命令 |

依赖关系:**A → (B ∥ C) → D → E**

---

# 关键决策记录

## 决策 1:三源做并集而非 FP 单入口

**背景:** PRD 第 6 节流程图写的是"FlixPatrol + TMDb + Trakt → 多源合并去重",但当前代码实际只用 FP 作候选来源,TMDb/Trakt 仅在 entity_matching 里被调用。

**判断:** TMDb trending 和 Trakt trending 里有大量未上 FP 的高分内容(刚上映、社区评价极高但未爆),如果继续 FP 单入口会漏掉这部分。

**取舍:** 三源做并集会增加合并复杂度和 API 调用,但与 PRD 一致,且数据丰富度显著提升。**采纳并集方案**。

## 决策 2:三源数据独立存表

**背景:** 用户明确要求"热门源数据每日更新,独立保存,互相不干扰"。

**判断:** 不能复用 `flixpatrol_top10` 表存 TMDb/Trakt(字段不同),也不能用一张大宽表(查询/调试痛苦)。

**取舍:** 三张独立表 `flixpatrol_top10` / `tmdb_trending` / `trakt_trending`,合并发生在内存里(`multi_source_merge.py`)。便于独立验证每个源的健康度,也便于未来增减源。

## 决策 3:OMDb 逐条查询 + 缓存,不强求批量

**背景:** OMDb 物理上没有列表端点。

**判断:** FP 90 条全部逐条查 OMDb,加 24h 缓存,实际每天调用次数会随天数衰减(7 天后大多数热门内容已缓存)。免费配额 1000 次/天完全够用。

**取舍:** 接受每日 ~90 次 API 调用,但缓存命中率高。**不引入额外的 IMDb 数据集下载方案**(规避合规复杂度,详见 PRD § 4.4)。

---

# 当前项目状态快照

```
代码改动:    无(本会话纯调研 + 规划)
测试状态:    317 passed(未变动)
新增文档:    5 个任务包(docs/tasks/p1.7_*.md)
STATE.md:    更新到 Phase 1.7 启动态
功能 1:      ❌ 仍 broken(P1.7-D 完成前)
功能 2:      ✅ 正常(6 条 new_season)
content_updates: 6(全部 new_season,来自功能 2)
```

阻塞项:无
待用户决策:Phase 1.7 任务包审阅(每个任务包顶部 checkbox)

---

# 给下一个 AI Agent 的交接

## 可接任务

- 任何一个 P1.7-* 任务包(按依赖顺序)
- 用户勾选任务包 checkbox 后才能进入编码

## 不要重做的事

- 不要再次调研 TMDb / Trakt / OMDb API 端点能力(本会话已完整调研)
- 不要争论"是否要 Trakt"或"是否要 OMDb",已纳入 1.7 范围
- 不要重新设计三源去重策略(已定 tmdb_id > imdb_id > title_norm)

## 容易被忽略的知识

1. **Trakt API 必须带 Firefox UA**,否则 Cloudflare 1010 (403)。P1.7-C 任务包要求修 `src/movietrace/sources/http.py` 的默认 UA,**这会影响所有源**,要确保 FlixPatrol 调用方已显式覆盖自己的 UA(`MovieTraceBot/0.1`)
2. **TMDb popular vs trending 与 FP 重叠度只有 33%**:不要以为拉 TMDb 200 条就能覆盖 FP,这两类榜单热度标准不同(老片 FP 热但 TMDb 沉底)
3. **FP 数据 `imdb_id` 字段是纯数字**(如 `1190634`),OMDb 调用需要补 `tt` 前缀并补零到 7 位 → `tt1190634`
4. **FP `tmdb_id` 97% 填充率**,但 2 条没有 tmdb_id 的需要兜底逻辑(用 imdb_id 或 title_norm)

## P1.7-D 是大头

5 个任务包里 P1.7-D 工作量最大(~600 行 + 测试),它一个人改的文件最多。其他四个都是辅助。**建议在 D 开工前先完成 A/B/C,数据准备好再做合并打分,避免边采集边改逻辑**。

---

# 数字总结

- commits:0(本会话末尾即将创建 1 个)
- 修改文件:1(STATE.md)
- 新增文件:5(P1.7 任务包)+ 1(本日报)
- 测试用例变化:无(本会话纯文档)
- API 调用统计:
  - TMDb:~30 次(调研中)
  - Trakt:~15 次
  - OMDb:1 次
- 关键调研产出:三源能拉到多少 / 多久查一次 / 覆盖率 / 字段映射

---

# 成本统计

- **会话耗时:** ~1.8 小时(墙钟,11:00 ~ 12:50 +08)
- **Token 消耗(从会话 jsonl 聚合,精确值,写完日报后二次读取):**
  - Assistant 消息数:174(Sonnet 4.6: 100 / Opus 4.7: 74)
  - 输入(非缓存):**1,074**
  - 缓存创建:**1,231,830**
  - 缓存读取:**19,635,485**
  - 输出:**115,147**
  - **总计:20,983,536 tokens**(其中缓存读占 94%,实际计费新增约 1.35M)
- **代理指标(辅助参考):**
  - 用户消息:13 轮
  - 模型切换:1 次(Sonnet 4.6 → Opus 4.7,在任务包生成阶段)
- **外部 API 调用消耗:** 调研阶段 < 50 次 TMDb/Trakt/OMDb,均在免费配额内

## 关于 token 记录的可行性结论(2026-05-13 +08,已修订)

**Agent 可以读取精确 token 消耗** —— 数据源是 `~/.claude/projects/<project>/<session-uuid>.jsonl`,每条 assistant 消息含完整 `usage` 字段。

**标准做法:**

1. 写日报"成本统计"段时,直接 `python3` 读取本会话 jsonl 聚合
2. **写完日报后再读一次**(覆盖前一次未计入的写入消耗),如已 commit 则 amend
3. 路径定位方式:`ls -t ~/.claude/projects/$(pwd | sed 's|/|-|g')/*.jsonl | head -1` 取最新
4. **不再使用估算或"未记录"占位符** —— 精确值始终可获取

---

# 失败 / 未尽事项

- **未运行任何代码改动**——纯调研 + 规划会话,代码缺口(ext_data=None)仍存在,功能 1 仍不可用
- **未生成 ADR**——三源并集策略是个架构级决策,建议 P1.7 开工前补 ADR-0008
- **任务包总工作量估算偏乐观**——5 个任务包合计 5 个工作日,P1.7-D 实际可能 2-3 天
