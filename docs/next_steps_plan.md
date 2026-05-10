# MovieTrace 下一步实施规划

**状态：** 实施规划版 V2（产品方向重新对齐）  
**日期：** 2026-05-10（V2 重新规划）  
**原始日期：** 2026-05-08  
**依据：** [requirements.md](requirements.md)、[product_roadmap.md](product_roadmap.md)、[feasibility.md](feasibility.md)、[operating_cost_estimate.md](operating_cost_estimate.md)

---

## 1. 关键决策（2026-05-10 产品方向重新对齐）

经过 Phase 0 完成后的产品讨论，做出以下关键决策：

### 1.1 产品定位调整

**从"新内容更新追踪"调整为"全网值得更新内容发现"。**

- 旧逻辑：飞书基线 + TMDb/Trakt → 推荐"基线没有的新更新"
- 新逻辑：FlixPatrol + TMDb + Trakt + OMDb 独立发现 → 与基线匹配标记 → 输出"新增 + 已有可补充"

详细见 [product_roadmap.md](product_roadmap.md) 第 1 节。

### 1.2 V1 / V2 划分

**V1（当前阶段）：**
- 用免费/低成本数据源
- 加入 FlixPatrol（合规公开页面）
- 不引入 LLM、付费 API、复杂爬虫

**V2（下一阶段，V1 上线 1-2 个月后）：**
- LLM 用户契合度判断
- 多 Agent 推理框架
- Rotten Tomatoes + Metacritic 评分聚合
- 其他付费 API（按需）

### 1.3 Phase 0 回溯调整

Phase 0 已完成的核心验证仍然有效（飞书读取、SQLite、实体匹配），但需要补充：
- FlixPatrol 可访问性和数据质量验证
- 详细见 [phase0_supplement.md](phase0_supplement.md)

---

## 2. V1 路线图

| 阶段 | 时间预估 | 目标 | 主要产物 | 进入下阶段条件 |
|------|---------|------|---------|---------------|
| ✅ Phase 0：开发前验证 | 已完成 | 证明数据、飞书、匹配可行 | 验证脚本、报告、Go结论 | ✅ 已通过 |
| ✅ Phase 0+：FlixPatrol 验证 | 已完成 | 验证 FlixPatrol 接入可行 | 接入测试、合规评估 | ✅ 通过，进入 Phase 1 |
| 🔄 Phase 1：V1 MVP 开发 | 2-3 周 | 多源发现 + 飞书写入闭环 | CLI、SQLite、日报、飞书写入 | 人工确认流程可用 |
| Phase 2：V1 冷启动追赶 | 1-2 周 | 追赶最近 180 天 + 已有内容评分补充 | bootstrap 模式、分批写入 | 候选规模可控 |
| Phase 3：V1 每日自动化 | 1 周 | 每日稳定运行 + 飞书日报 | daily 模式、定时任务 | 连续运行稳定 |
| Phase 4：V1 生产化加固 | 持续 | 监控、备份、限流、告警 | 部署文档、告警机制 | 长期运行条件 |
| **运营评估期** | **1-2 月** | **积累运营反馈，识别 V2 需求** | **运营反馈记录、需求清单** | **决策 V2 启动** |
| Phase 5：V2 方向规划 | 视反馈 | LLM、多 Agent、付费数据源等 | V2 详细需求和路线图 | V2 任务包就绪 |

---

## 3. Phase 0 当前进展记录（已完成）

**完成日期：** 2026-05-10  
**最终决策：** ✅ GO，进入 Phase 1

### 3.1 已完成

1. ✅ 飞书 App 权限、表读取、测试表写入和更新验证
2. ✅ 飞书 `节目` 表全量基线质量报告
3. ✅ 节目库导出 Schema v0.1，并同步到飞书 schema 子表
4. ✅ TMDb / Trakt / OMDb API 连通性验证
5. ✅ SQLite 初始 schema、测试和本地数据库初始化
6. ✅ 飞书 `节目` 表导入本地 `baseline_items`（855 条）
7. ✅ 全量实体匹配 dry run（826 条 high 置信度，96.6% 准确率）
8. ✅ canonical_items + external_ids 写入完成
9. ✅ Phase 0 收尾：73 条 medium、3 条 low/no_match 的人工决策
10. ✅ Phase 0 完成报告 + Go/No-Go 决策报告

### 3.2 已产出

- `docs/feishu_api_validation_notes.md`
- `docs/baseline_export_schema.md`
- `docs/local_database_architecture.md`
- `reports/baseline_quality_report.md`
- `reports/entity_matching_report.md`
- `reports/baseline_import_report.md`
- `reports/full_entity_matching_report.md`
- `reports/manual_entity_matching_review.md`
- `reports/phase0_day1_summary.md`
- `reports/phase0_day2_summary.md`
- `reports/phase0_completion_report.md` ⭐
- `reports/go_no_go_decision.md` ⭐

### 3.3 当前数据库状态

```
baseline_items:           855 条
canonical_items:          826 条 (96.6%)
external_ids:             826 条
match_candidates:         855 条
baseline_quality_issues:  29 条 (待人工修正)
```

---

## 4. Phase 0+ 补充验证（FlixPatrol 接入）

**时间预估：** 3-5 天  
**任务文档：** [phase0_supplement.md](phase0_supplement.md)

### 4.1 验证目标

1. FlixPatrol 公开页面是否可稳定访问？
2. 解析逻辑是否稳定？（HTML 结构、字段提取）
3. 与现有 TMDb/Trakt 候选的匹配率如何？
4. 服务条款和合规边界是什么？
5. 缓存策略是否合理？

### 4.2 验证产出

- `reports/flixpatrol_validation_report.md`
- `reports/flixpatrol_compliance_assessment.md`
- 决策：✅ GO / ⚠️ Conditional GO / ❌ NO-GO 接入 FlixPatrol

详见 [phase0_supplement.md](phase0_supplement.md)。

---

## 5. Phase 1：V1 MVP 开发

**时间预估：** 2-3 周  
**前置条件：** Phase 0+ FlixPatrol 验证通过

### 5.1 Phase 1 目标

实现"全网热门好评内容发现"的最小闭环：

```
FlixPatrol + TMDb + Trakt + OMDb
    ↓
合并去重 + 综合评分
    ↓
与飞书基线匹配（is_in_baseline）
    ↓
生成每日推荐列表
    ↓
写入飞书推荐表
    ↓
人工审核 + 批次管理
```

### 5.2 Phase 1 任务拆分

#### 任务 P1-A：实体匹配算法改进（1-2 天）

**目标：** 把 Phase 0 人工复核的 4 个 case 转成回归测试 + 修复算法。

**范围：**
- `src/movietrace/pipeline/entity_matching.py`
- `tests/test_entity_matching.py`

**4 个 case：**
1. Jack Ryan（品牌前缀）
2. La casa de papel（original_name）
3. O Rio do DESEJO（original_title）
4. Wedding Plan interview（标题污染清洗 + 人工预警）

**验收：**
- 4 个 case 的回归测试通过
- 既有实体匹配测试不退化
- 重跑 855 条 baseline 全量匹配，high 准确率仍 ≥ 95%

#### 任务 P1-B：FlixPatrol 接入（2-3 天）

**目标：** 实现 FlixPatrol 平台 Top 10 数据采集和缓存。

**范围：**
- `src/movietrace/sources/flixpatrol.py`（新建）
- `src/movietrace/db/schema.py`（新增 `flixpatrol_charts` 表）
- `tests/test_flixpatrol.py`（新建）

**实现要点：**
- 礼貌访问频率（>= 2 秒间隔）
- 24 小时缓存
- 重试 + 指数退避
- 与 TMDb/Trakt 候选通过 title+year 匹配

**验收：**
- 能稳定获取 Netflix Global/US Top 10
- 能获取至少 3 个其他平台的 Top 列表
- 缓存策略生效，重复运行不重复抓取
- 单次失败有重试和日志

#### 任务 P1-C：多源候选合并和综合评分（2-3 天）

**目标：** 实现 V1 的 hot_score 计算逻辑。

**范围：**
- `src/movietrace/pipeline/discovery.py`（新建）
- `src/movietrace/pipeline/scoring.py`（新建）
- `tests/test_discovery.py`（新建）
- `tests/test_scoring.py`（新建）

**实现要点：**
- 按 external_id 合并去重（tmdb_id 优先）
- 综合评分公式（详见 requirements.md § 10.2）
- priority 映射（P0/P1/P2/P3）
- discovery_source 标记（new_release / global_hot / both）

**验收：**
- 单元测试覆盖评分公式各因素
- 集成测试覆盖端到端发现流程
- 候选去重正确（同一内容不重复）

#### 任务 P1-D：飞书基线匹配标记（1 天）

**目标：** 把候选与本地 baseline_items / canonical_items 匹配，标记 is_in_baseline。

**范围：**
- `src/movietrace/pipeline/baseline_matching.py`（扩展）
- `src/movietrace/db/schema.py`（在 match_candidates 加 is_in_baseline 字段）

**验收：**
- 候选匹配到 baseline 时正确标记
- 未匹配的候选标记为新增
- 低置信度匹配标记为待人工确认

#### 任务 P1-E：每日 Markdown 日报（1 天）

**目标：** 生成每日推荐日报，按"新增/已有可补充/待确认"分类。

**范围：**
- `src/movietrace/reports/daily_writer.py`（新建）
- 输出到 `reports/daily/YYYY-MM-DD.md`

**输出格式：** 见 product_roadmap.md § 2.4

#### 任务 P1-F：飞书推荐表写入（2-3 天）

**目标：** 把候选写入飞书多维表格的推荐更新表。

**范围：**
- `src/movietrace/feishu/recommendation_writer.py`（新建）
- `src/movietrace/pipeline/discovery.py`（增加 dry_run 和 commit 模式）

**实现要点：**
- 按 content_update_id 去重
- 不覆盖人工字段（review_status、batch_id、fulfillment_status）
- dry-run 模式不写飞书
- 错误重试 + 失败日志

**验收：**
- 重复运行不重复写入
- 不覆盖人工修改的状态字段
- dry-run 输出与实际写入数据一致

#### 任务 P1-G：CLI 命令和配置（1 天）

**目标：** 实现 `movietrace daily-discover` 等 CLI 命令。

**范围：**
- `src/movietrace/cli.py`（扩展）
- `config/config.example.yaml`（更新示例）

**命令：**
```
movietrace validate-feishu
movietrace daily-discover [--date YYYY-MM-DD] [--dry-run]
movietrace inspect-baseline
movietrace check-feishu-schema
```

#### 任务 P1-H：集成测试和首次运行（1-2 天）

**目标：** 端到端测试 + 首次实际运行 dry-run。

**验收：**
- 端到端 pytest 通过
- 实际运行能输出完整日报
- 候选数量和质量符合预期（人工抽查 50 条认可率 ≥ 60%）

### 5.3 Phase 1 验收标准

整体 Phase 1 验收：

1. ✅ 手动运行一次能生成"全网热门好评"推荐候选
2. ✅ 推荐列表分为"新增/已有可补充/待确认"三类
3. ✅ 至少使用 4 个数据源（FlixPatrol + TMDb + Trakt + OMDb）
4. ✅ 重复运行不重复写入同一 content_update_id
5. ✅ 不覆盖人工修改的 review_status、batch_id、fulfillment_status
6. ✅ 所有 API Key 不进入 GitHub
7. ✅ 出错时能看到具体数据源、请求和错误原因
8. ✅ 人工抽查 50 条候选认可率 ≥ 60%
9. ✅ Phase 0 实体匹配 case 的回归测试通过

### 5.4 Phase 1 验证命令

```bash
# 单元测试
python3 -m pytest tests/ -v

# 集成测试
python3 -m pytest tests/integration/ -v

# Dry-run（不写飞书）
python3 -m movietrace daily-discover --date 2026-05-10 --dry-run

# 实际运行（写飞书）
python3 -m movietrace daily-discover --date 2026-05-10
```

---

## 6. Phase 2：V1 冷启动追赶

**时间预估：** 1-2 周  
**前置条件：** Phase 1 完成且日报质量验证通过

### 6.1 Phase 2 目标

实现 bootstrap 模式：追赶最近 180 天的高价值更新。

### 6.2 工作内容

1. 实现 `bootstrap` 模式
2. 默认回看最近 180 天
3. 用线上内容基线和历史业务状态过滤（注意：这里仍是"过滤"，因为是补全历史，不是发现新内容）
4. P0/P1 控制在 200 条左右
5. 按周或按优先级分批写入飞书
6. 生成 bootstrap 汇总报告

### 6.3 验收标准

1. bootstrap dry run 能先输出统计，不强制写飞书
2. 用户确认后再写入推荐表
3. 可按批次逐步追赶
4. 已上架内容不会重复推荐
5. 新季和新集不会被旧季、旧集误过滤

---

## 7. Phase 3：V1 每日自动化

**时间预估：** 1 周  
**前置条件：** Phase 2 完成

### 7.1 工作内容

1. 实现 `daily` 模式（基于 Phase 1 的 daily-discover）
2. 配置服务器 cron 或 systemd timer
3. 每日生成飞书日报
4. 失败时发送飞书消息或邮件告警

### 7.2 验收标准

1. 连续运行 7 天无重复写入
2. 单一数据源失败不影响其他
3. 每日运行有日志和运行摘要
4. 可按日期范围补采

---

## 8. Phase 4：V1 生产化加固

**时间预估：** 持续  
**前置条件：** Phase 3 完成

### 8.1 必做项

| 项目 | 说明 |
|------|------|
| 配置校验 | 启动前检查 API Key、表 ID、字段映射 |
| 限流队列 | TMDb、Trakt、FlixPatrol、飞书分别限流 |
| 本地缓存 | 外部 API 响应缓存 7-30 天 |
| 数据库备份 | SQLite 每日压缩备份 |
| 错误重试 | 处理 429、网络错误、飞书临时失败 |
| 断点续跑 | bootstrap 中断后可继续 |
| 日志脱敏 | 不输出完整 token 和 secret |
| 部署文档 | 服务器、环境变量、定时任务、恢复方法 |

### 8.2 验收标准

1. 服务器重启后任务能恢复
2. API 临时失败可重试
3. SQLite 备份可恢复
4. 日志可定位问题但不泄露密钥
5. 有一份 `docs/deployment.md`

---

## 9. 运营评估期（V1 → V2 决策）

**时间预估：** 1-2 个月（V1 上线后）  
**目标：** 积累运营反馈，识别明确的 V2 需求

### 9.1 运营反馈维度

1. **推荐质量**
   - P0/P1 的人工认可率
   - 漏报（应推荐但没推荐的内容）
   - 误报（推荐但人工拒绝的内容）

2. **运营效率**
   - 每日推荐数量是否合适
   - 人工审核耗时
   - 批次创建和提交流程是否顺畅

3. **业务价值**
   - 推荐内容上架后的播放数据（如有反馈）
   - 用户对推荐内容的满意度
   - 与同行竞品的对比

### 9.2 V2 启动决策标准

V2 启动需满足以下条件：

- ✅ V1 已稳定运行至少 1-2 个月
- ✅ 运营反馈明确指出 V1 的具体短板
- ✅ V2 投入产出比清晰（如 LLM 月成本 vs 推荐质量提升）
- ✅ 业务方愿意承担 V2 的额外成本

---

## 10. Phase 5：V2 方向规划（视反馈而定）

**优先级 V2 方向（详见 product_roadmap.md § 3）：**

1. **LLM 用户契合度判断** ⭐⭐⭐
   - 解决"非洲英文用户喜欢什么"
   - 月成本 ≈ $3-10
   
2. **多 Agent 推理框架** ⭐⭐
   - 把推荐变成"评审委员会"决策
   
3. **Rotten Tomatoes + Metacritic 评分聚合** ⭐⭐
   - 多源评分交叉验证
   - 通过爬虫或付费 API
   
4. **付费 API（视需要）**
   - Watchmode：$99-499/月
   - IMDb Pro：$50+/月

---

## 11. Go / No-Go 决策点

### 11.1 已完成的决策

| 决策点 | 时间 | 结论 | 文档 |
|--------|------|------|------|
| Phase 0 → Phase 1 | 2026-05-10 | ✅ GO | `reports/go_no_go_decision.md` |

### 11.2 即将到来的决策

| 决策点 | 预计时间 | 触发条件 |
|--------|---------|---------|
| Phase 0+ → Phase 1 | Phase 0+ 完成后 | FlixPatrol 验证通过 |
| Phase 1 → Phase 2 | Phase 1 完成后 | 日报质量验证通过 |
| Phase 4 → 运营评估期 | Phase 4 完成后 | V1 进入稳定运行 |
| V1 → V2 | 运营评估期结束 | 明确的 V2 需求和预算 |

---

## 12. 当前优先级结论

**当前最优先级：**

1. ✅ Phase 0 收尾完成（已完成）
2. 🔄 创建 `phase0_supplement.md` 验证 FlixPatrol（**下一步**）
3. ⏳ 准备 Phase 1 任务包
4. ⏳ Phase 0+ 验证完成后进入 Phase 1

这条路线确保产品方向清晰，每个阶段都有明确的 Go/No-Go 决策点。

---

## 13. 文档更新记录

| 日期 | 更新内容 | 作者 |
|------|---------|------|
| 2026-05-08 | 初始版本（基线对比逻辑） | 项目启动 |
| 2026-05-10 | V2 重新规划：产品方向调整为"全网值得更新发现"，加入 FlixPatrol，明确 V1/V2 划分 | 产品方向对齐讨论 |
