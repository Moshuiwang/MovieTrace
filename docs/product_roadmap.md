# MovieTrace 产品路线图

**状态：** 路线图 V1（含 V1.5 定位翻转，ADR-0007）
**日期：** 2026-05-10（最近更新 2026-05-11）
**适用范围：** 整个项目周期，作为长期产品决策的索引和未来工作的参考

---

## 1. 产品目标（重新确认）

### 1.1 核心目标

**每日检测全网热门英文影视内容的更新事件，以及 A 库（运营业务库）中已有 TV 剧集的新季/新集更新，写入中间表（当前为飞书）供运营从中挑选并提交供应商。** 详见 [ADR-0007](decisions/0007-repositioning-to-update-tracking.md)。

"值得追踪"= 同时满足：
- **热度高** — 当前正在流行（不只是社区热度，更要真实平台热度）
- **评分好** — 内容质量经过验证（多源交叉验证最可靠）
- **平台相关** — Netflix、Prime Video、Disney+、Apple TV+、HBO/Max、Hulu

**注：** "目标用户契合"（非洲英文用户口味判断）属 V2 LLM 范围，V1.5 不做主观契合度评估。

### 1.1.1 关键产品决策（2026-05-11，ADR-0007）

**系统定位翻转：从"推荐+人工审核"翻转为"更新追踪+中间表"。**

- 旧定位：系统输出"待审建议"，运营在飞书表中审核（采纳/忽略/补充）
- 新定位：系统输出"已检测的更新事件"（满足客观阈值），运营在中间表中挑选提交供应商

**核心定位的四个"不是"：**
- 不是视频资源获取系统
- 不是全网所有新内容追踪系统（仅追踪满足 `hot_score` 阈值的热门内容，以及 A 库已有剧集的更新）
- 不是推荐系统（不做主观质量判断）
- 不是人工审核工具（人工审核发生在中间表→供应商，在系统职责之外）

**架构概念：A 库（运营业务库）/ B 库（MovieTrace 自维护）/ 中间表（=当前飞书）。** 详见 ADR-0007 § 决策二。

### 1.2 关键产品决策（2026-05-10，ADR-0001）

**跳出"基线对比"的局限：**

之前的逻辑是：
```
TMDb/Trakt 候选 → 与飞书基线去重 → 建议"基线没有"的
```

**问题：** 陷入"先有鸡还是先有蛋"困境。如果飞书基线本身不完整，永远打不破"基线天花板"。

**新逻辑：**
```
独立发现"全网热门好评"内容（不依赖基线）
    ↓
与飞书基线匹配（仅用于标记是否已有，不用于过滤）
    ↓
输出：新增 + 已有可补充（V1.5 起改名，原称"新增推荐"）
```

**核心洞察：** 飞书基线是"已上架的事实"，不是"全网值得有的"。两者必须独立发现，再合并标记。

---

## 2. V1 路线（当前阶段）

**定位：** 用免费/低成本数据源，做出可用的"每日值得更新"追踪工具，将检测结果写入中间表供运营人工挑选。

**预算约束：** 不引入付费API、不做高复杂度爬虫、不引入LLM API。

**运行观察期补充（2026-05-14）：** V1 已完成后，运营消费侧出现新需求：将 `export-recommendations` 生成的 MD/JSON 结果自动同步到飞书多维表格，并在成功/失败时发送简要飞书通知。该需求定位为“飞书运营同步层”，不改变影视发现、评分、匹配或 B 库事实源。需求草案见 [`docs/notes/feishu_ops_sync_requirements.md`](notes/feishu_ops_sync_requirements.md)。

### 2.1 V1 信号源组合

```
信号1: 真实平台热度
└── FlixPatrol（合规公开页面） ⭐ 关键补充
    ├── 聚合 Netflix、Prime Video、Disney+、Apple TV+、HBO Max 的TOP 10
    ├── 按地区（Global/US）查询
    └── 解决"缺真实平台热度"的核心短板

信号2: 内容质量与社区热度
├── TMDb API（已有）
│   ├── trending/tv/day, trending/movie/day
│   ├── trending/tv/week, trending/movie/week
│   ├── vote_average, vote_count, popularity
│   └── watch providers（平台可用性）
├── Trakt API（已有）
│   ├── trending shows/movies
│   ├── popular shows/movies
│   └── 用户观看热度
└── OMDb API（已有）
    ├── IMDb 评分、投票数
    └── 跨源验证

信号3: 飞书基线
└── 仅用于"is_in_baseline"标记，不参与过滤
```

### 2.2 V1 更新事件生成逻辑（V1.5 起：检测，不做"推荐"判断）

```python
# 伪代码：每日运行流程
def daily_discovery():
    # Step 1: 多源采集
    flixpatrol_top = fetch_flixpatrol_charts(regions=['Global', 'US'])
    tmdb_trending = tmdb.trending(timeframe='day') + tmdb.trending(timeframe='week')
    trakt_trending = trakt.trending() + trakt.popular()
    
    # Step 2: 合并去重（by external_id）
    candidates = merge_by_external_id(flixpatrol_top, tmdb_trending, trakt_trending)
    
    # Step 3: 评分补充
    for c in candidates:
        c.tmdb_rating = tmdb.get_details(c.tmdb_id).vote_average
        c.imdb_rating = omdb.get_rating(c.imdb_id)
        c.flixpatrol_rank = flixpatrol_lookup(c)
    
    # Step 4: 过滤
    candidates = filter(candidates, 
        rating_threshold=7.0,
        vote_count_min=100,
        platforms=['Netflix', 'Prime', 'Disney+', 'Apple TV+', 'HBO Max', 'Hulu'])
    
    # Step 5: 综合评分
    for c in candidates:
        c.hot_score = compute_hot_score(c)
        c.priority = map_priority(c.hot_score)
    
    # Step 6: 与飞书基线匹配（仅标记，不过滤）
    baseline_matches = match_against_baseline(candidates)
    for c in candidates:
        c.is_in_baseline = c.external_id in baseline_matches
        c.baseline_canonical_id = baseline_matches.get(c.external_id)
    
    # Step 7: 输出
    return sorted(candidates, key=lambda x: x.hot_score, reverse=True)[:50]
```

### 2.3 V1 综合评分公式

```
hot_score = 
    flixpatrol_signal_score * 0.30      # 真实平台热度（最重要）
  + tmdb_popularity_score * 0.20         # TMDb社区热度
  + trakt_signal_score * 0.15            # Trakt社区热度
  + tmdb_rating_score * 0.15             # TMDb评分
  + imdb_rating_score * 0.15             # IMDb评分（OMDb）
  + freshness_bonus * 0.05               # 新鲜度（90天内加分）
```

### 2.4 V1 输出格式（V1.5 起：定位为运行可观察性日报）

```
==========================================
MovieTrace 每日更新追踪日报 - 2026-05-11
==========================================

【🆕 新增】(A 库未有)
1. [P0] The Brutalist (2024) | TMDb 8.1 | IMDb 8.2 | 🔥 Netflix Global #3
2. [P0] Babygirl (2024) | TMDb 7.5 | IMDb 7.8 | 🔥 Apple TV+ Trending
3. [P1] Conclave (2024) | TMDb 7.4 | IMDb 7.5 | 🔥 院线热门
...

【♻️ 已有可补充】(A 库已有，可更新评分/热度/新季)
1. The Bear S03 | TMDb 8.5 | IMDb 8.6 | 🔥 Hulu Global #1
2. Shogun S01 | TMDb 8.7 | IMDb 8.7 | 🔥 Hulu Trending
3. (功能 2 检测) Severance S02 | A 库已有 S01，TMDb 显示新季已发布
...

【⚠️ 待人工确认】(实体匹配低置信度)
1. 某韩剧 | 高热度但 TMDb 映射置信度低，需运营在中间表中确认
...

==========================================
统计：检测到更新事件 73 条 | 新增 47 | 已有 22 | 待确认 4
数据源：FlixPatrol + TMDb + Trakt + OMDb
==========================================
```

**注：** V1.5 起，"推荐"改称"建议"或"更新事件"。详见 ADR-0007 § 决策五。

---

## 3. V2 路线（下一阶段，产品迭代时启动）

**定位：** 当V1完成产品上线、积累一段运营经验、识别出明确的产品迭代需求后，启动V2开发。

**触发条件：**
- V1已稳定运行至少1-2个月
- 运营反馈了明确的需求短板
- 有具体业务证据支撑V2的投入

### 3.1 V2 候选方向（按价值/成本评估）

| 方向 | 价值 | 成本 | 难度 | 优先级 |
|------|------|------|------|--------|
| **LLM用户契合度判断** | 极高（差异化） | 中（API token） | 中 | ⭐⭐⭐ |
| **Rotten Tomatoes + Metacritic** | 高（评分多源验证） | 中（爬虫/付费） | 中 | ⭐⭐ |
| **多Agent推理框架** | 极高（编辑级推荐） | 中-高（LLM token） | 高 | ⭐⭐ |
| **Watchmode API** | 高（episode级精确） | $99-499/月 | 低 | ⭐ |
| **IMDb Pro Datasets** | 高（商业级数据） | $50+/月 | 低 | ⭐ |
| **时序预测（即将爆款）** | 高（主动发现） | 中 | 高 | ⭐ |
| **Reddit / Twitter 信号** | 中（社交热度） | 中 | 高 | ⭐ |
| **YouTube 预告片数据** | 中（预热信号） | 低（API配额） | 中 | ⭐ |
| **JustWatch Partner API** | 高（流媒体覆盖） | 需企业合作 | 高 | ⭐ |
| **Letterboxd 影迷信号** | 中（深度评价） | 中（爬虫） | 中 | ⭐ |

### 3.2 V2 重点方向详解

#### 方向1: LLM 用户契合度判断 ⭐⭐⭐

**问题：** "非洲英文用户喜欢什么"无法从任何API直接得到。

**LLM能做：**
```
输入：候选内容（剧情/类型/演员/制作国/语言/主题）

LLM分析：
- 主题是否对非洲用户有共鸣？（家庭、移民、奋斗、宗教等）
- 历史上类似内容在非洲市场的反响？
- 文化适配度（避免有强烈本地化壁垒的内容）
- 推荐理由（运营汇报用，自然语言）

输出：
- audience_relevance_score（0-100）
- 推荐文案
- 风险提示（如内容敏感、版权复杂）
```

**实现方案：**
- 用 Claude API（按token付费，约$3/1M tokens）
- 对每条候选调用一次（约500 tokens输入 + 200 tokens输出）
- 每日50条候选 ≈ $0.10/天 ≈ $3/月

**这是 V2 最值得做的方向**，因为：
1. 现有API给不了"用户契合度"
2. 成本可控（$3/月）
3. 是真正的产品差异化

#### 方向2: 多Agent推理框架 ⭐⭐

**问题：** 单一公式打分无法处理复杂判断。

**方案：** 模拟"内容评审委员会"
```
对每个候选内容，并行调用：
- Agent A: 内容质量评估师（基于评分+影评）
- Agent B: 市场热度分析师（基于多平台热度）
- Agent C: 用户契合度评估师（基于目标用户特征）
- Agent D: 业务价值评估师（基于平台已有内容、版权等）

最终输出：
- 综合评分 + 各维度详细理由
- 推荐/不推荐 + 推荐文案
- 风险提示
```

#### 方向3: Rotten Tomatoes + Metacritic 三角验证 ⭐⭐

**问题：** 单一评分容易被刷分或偏向某类观众。

**方案：**
```
高质量 = IMDb≥7.5 AND RT_Tomatometer≥75% AND Metacritic≥70
中等质量 = 三者中至少2个达标
争议内容 = 三者评分差距大（值得人工关注）
```

**实现方式：**
- 选项A：合规爬虫（公开页面）
- 选项B：付费API（如RapidAPI上的RT API，$10/月）

#### 方向4: 时序预测（即将爆款）

**问题：** 反应式发现"现在热"，永远比同行慢一步。

**方案：**
```
即将上线日历（TMDb release dates）
+ 预告片观看数（YouTube）
+ 行业报道频次（新闻聚合）
+ 续作/前作热度
↓
预测未来30天可能爆款的内容
```

#### 方向5: Watchmode / JustWatch / IMDb Pro

**只在V1验证后，确实有特定不足时引入：**
- Watchmode：episode级流媒体追踪准确度
- JustWatch：跨平台可用性
- IMDb Pro：商业级popularity meter

---

## 4. 决策原则（贯穿所有阶段）

### 4.1 信号源选择原则

1. **优先免费API**：能用免费API解决的，不引入付费
2. **优先合规公开**：能用公开页面/聚合服务的，不做敏感爬虫
3. **多源交叉验证**：单一信号源不够，至少2-3个验证
4. **可解释优先**：所有推荐必须有明确依据，避免黑盒
5. **可降级**：单一数据源失败不影响整体运行

### 4.2 LLM 使用原则（V2开始）

1. **用LLM做"难以规则化"的判断**（如用户契合度）
2. **不用LLM做"可以规则化"的事**（如评分排序、过滤）
3. **LLM输出必须可追溯**（保留prompt和response）
4. **成本可控**（缓存、批量、模型选择）
5. **LLM不替代人工审核**（只是辅助）

### 4.3 产品演进原则

1. **每个阶段必须有明确成功标准**
2. **每个阶段完成后必须有Go/No-Go决策**
3. **不为"未来需求"提前优化**（YAGNI）
4. **优先解决"已验证的痛点"**

---

## 5. 阶段交付物清单

### V1 交付物（已全部完成 2026-05-11，284 测试通过）

- [x] `movietrace daily-discover` 命令
- [x] FlixPatrol 接入和数据缓存
- [x] 多源候选合并和综合评分
- [x] 飞书基线匹配（is_in_baseline 标记）
- [x] 每日 Markdown 日报（新增/已有/待确认）
- [x] 飞书"建议更新表"写入（V1 时称"推荐更新表"，V1.5 改名）
- [x] 配置化阈值和数据源开关

收尾报告：[`reports/phase1_completion_report.md`](../reports/phase1_completion_report.md)

### V1.5 交付物（当前阶段目标，ADR-0007）

- [ ] **P1.5-A** 文档翻转（requirements / SCOPE / product_roadmap / ADR-0001 / ADR-0004）
- [ ] **P1.5-B** B 库 schema 扩展（virtual_series 字段）+ 飞书表 migration（删 6 冗余字段，加 `match_confidence_low`）
- [ ] **P1.5-C** `virtual_series` 表 + 一次性回填脚本（TV only，电影跳过）
- [ ] **P1.5-D** 功能 2：基线主动追踪模块（TMDb 智能轮询 + 新季检测）
- [ ] **P1.5-E** 飞书写入逻辑翻新（删审核字段写入，低置信度归入第三类输出）
- [ ] **P1.5-F** 日报模板调整 + CLI 语义调整（"推荐"→"建议"）
- [ ] **P1.5-G** 检测与导出解耦（新增 `export-recommendations` 命令）

### V2 交付物（下阶段目标）

- [ ] LLM用户契合度评估模块
- [ ] 多Agent推理框架
- [ ] RT/Metacritic评分聚合
- [ ] 推荐文案自动生成
- [ ] 风险提示生成
- [ ] 时序预测模块
- [ ] V2-Adaptive评分公式（基于运营反馈学习）

---

## 6. 重要洞察记录（避免遗忘）

### 6.1 "先有鸡还是先有蛋"问题

**问题描述：** 如果只用飞书基线做去重，推荐就被基线本身的完整性限制。

**解决方案：** 独立发现 → 标记是否已有，而不是先过滤再推荐。

### 6.2 信号源的"维度差异"

不同信号源代表不同维度的"热度"：
- TMDb/Trakt = 社区热度（影迷为主）
- FlixPatrol = 真实平台热度（大众为主）
- IMDb评分 = 长期质量（不是热度）
- Rotten Tomatoes = 专业评分（不是热度）

**核心洞察：** 多维度信号交叉验证 > 单一来源排序。

### 6.3 LLM 的独特价值

LLM在以下场景产生现有API给不了的价值：
1. 用户契合度判断（"非洲英文用户喜欢吗"）
2. 推荐文案生成（运营汇报用）
3. 内容理解（主题、tone、target audience）
4. 多源数据冲突解决

### 6.4 产品差异化路径

```
通用影视推荐工具 → 针对非洲英文用户的精准推荐 → 行业级运营工具
     (V1)                    (V2)                      (V3+)
```

V2 是关键——把产品从"通用"变成"差异化"。

---

## 7. 文档关系图

```
product_roadmap.md (本文件，长期参考)
    │
    ├── requirements.md (产品需求)
    ├── feasibility.md (可行性)
    ├── next_steps_plan.md (执行计划)
    └── operating_cost_estimate.md (成本估算)

reports/
    ├── phase0_completion_report.md
    ├── go_no_go_decision.md
    └── ... (各阶段验证报告)
```

---

**最后更新：** 2026-05-10  
**下次评审时间：** V1上线后1-2个月  
**评审内容：** 是否启动V2、V2优先级排序、V2投入预算
