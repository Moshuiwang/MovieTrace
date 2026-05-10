# ADR-0004: Phase 0 不自动升级 26 条电影误标 medium 记录

**状态：** ✅ Accepted  
**日期：** 2026-05-10  
**决策者：** 用户 + Claude Code (Haiku 4.5)  
**相关 Commit：** `896b188`

---

## 上下文

Phase 0 收尾时，855 条 `baseline_items` 中 73 条匹配置信度为 `medium`，需要人工决策是否升级到 `high` 并写入 `canonical_items`。

按问题类型分为 4 类：

| 类型 | 数量 | 问题描述 |
|------|------|---------|
| A | 26 | 飞书基线标题含"S01"但 TMDb 标注为 movie（电影误标为 TV 剧集）|
| B | 42 | TMDb / OMDb 版本冲突（同名不同年份的不同实体）|
| C | 5 | TV 季度匹配，季号信息一致 |
| D | 1 | 其他 |

**A 类典型示例：**
- `Anatomy Of A Fall S01` → TMDb 显示为 movie / 2023
- `Family Switch S01` → TMDb 显示为 movie / 2023
- `Sherlock The Abominable Bride S01` → TMDb 显示为 movie / 2009

A 类问题的根因是**飞书基线录入有偏差**——电影被人工误标为剧集（加了 S01 后缀）。

## 决策

**A 类（26 条电影误标）不自动升级为 `high`，不写入 canonical_items。**

具体处理：

1. 保留 `match_status='medium'`
2. 创建新表 `baseline_quality_issues` 追踪这些问题
3. 每条记录标注：
   - `issue_type='movie_mistaken_as_tv_series'`
   - `tmdb_correct_type='movie'`
   - `resolution_recommendation='建议人工修正基线：移除 S01 后缀或标注为电影'`
4. 在 Phase 0 完成报告中明确列出，建议运营在飞书中修正

**B 类（版本冲突）和 C 类（TV 季度）按规则自动升级为 `high`**（详见 commit `896b188`）。

## 后果

**正面：**
- 不掩盖飞书基线的录入问题（"先解决根因，不打补丁"）
- 保留人工修正空间（不让程序自动改写基线）
- `canonical_items` 数据保持高质量（不混入"电影被当 TV 推广"的错误数据）
- 26 条问题被显式记录，可追溯
- 支持 AGENTS.md 第 9 条："不隐藏失败或不确定点"

**负面 / 待解决：**
- 这 26 条暂时不能进入 V1 推荐流程（需先人工修正基线）
- 增加了 `baseline_quality_issues` 表的维护成本
- 如果运营不主动修正，问题会长期存在（需要建立"基线质量报告"作为运营提示）

## 备选方案

### 备选 A：自动升级所有 medium，让 movie 进入 canonical_items

**做法：** 把 A 类电影直接当作电影写入 canonical（忽略飞书的"S01"后缀）。

- 优点：处理最简单；canonical_items 数据完整
- 缺点：
  - 程序静默修改了基线的语义（"用户标的是 TV，我们当作 movie"）
  - 后续如果用户在飞书修复，会出现 canonical 与 baseline 不一致
  - 违反 AGENTS.md "不删除已有逻辑来掩盖问题"
- **拒绝原因：** 程序不应该擅自纠正人工录入语义；这是基线维护责任，不是匹配算法责任

### 备选 B：直接删除这 26 条 baseline_items

**做法：** 既然录入有问题，删了重来。

- 优点：眼不见心不烦
- 缺点：
  - 失去运营修正空间
  - 用户的基线数据被程序删除（严重违规）
  - 违反 AGENTS.md 第 7 条"不删除已有逻辑来掩盖问题"
- **拒绝原因：** Agent 不能擅自删除用户数据；这是绝对禁区

### 备选 C：本次决策（保留 medium + 质量问题追踪）✅

详见"决策"章节。

---

## 后续动作

**已完成：**
- ✅ 创建 `baseline_quality_issues` 表
- ✅ 写入 29 条质量问题（26 条 A 类 + 1 条 low + 2 条 no_match）
- ✅ 在 [`reports/phase0_completion_report.md`](../../reports/phase0_completion_report.md) 中明确列出

**待做：**
- ⏳ V1 上线前，向用户/运营提示基线修正建议（机制设计）
- ⏳ 在飞书侧建立"基线质量报告"视图（V1 阶段考虑）

---

## 引用

- 完成报告：[`reports/phase0_completion_report.md`](../../reports/phase0_completion_report.md) § 4.2
- Go/No-Go 决策：[`reports/go_no_go_decision.md`](../../reports/go_no_go_decision.md)
- AGENTS.md 第 7、9 条
- 数据库变更：commit `896b188` 中创建 `baseline_quality_issues` 表
