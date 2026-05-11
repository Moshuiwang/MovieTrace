# 2026-05-11 工作日报 — Claude Code (Opus 4.7)

## Agent 身份卡

- **工具：** Claude Code (VSCode Extension)
- **模型：** Opus 4.7 (`claude-opus-4-7`)
- **运行环境：** Linux 6.8.0 / Python 3.12 / `.venv/`
- **起 Commit：** `01add04`（Phase 1 V1 MVP 收尾后）
- **止 Commit：** 待本次会话结束后产生

---

## 今日工作主线

### 主线 1：产品定位翻转（ADR-0007 提出并 Accepted）

**触发原因：** 用户在 V1 MVP 全部交付后（Phase 1 收尾，284 测试通过）回顾产品边界，重新澄清了对系统职责的理解。

**核心澄清：**
- 系统是"全网内容更新追踪系统"，**不是推荐系统**。
- 飞书表是"中间表"（运营业务流过渡载体），**不是审核队列**。
- 人工审核发生在"中间表→供应商"，**不在系统侧**。
- "推荐"一词有歧义，改用"建议"。

**讨论过程（多轮）：**

1. 用户起手提出"重新理解"和"需要整体重构"。
2. Agent 提出三条路径（甲：仅语义重对齐 / 乙：完整实现 / 丙：分两批），用户选**路径乙**。
3. 用户进一步给出**三功能 + 四"不是"** 的正式表述。
4. 用户引入**A 库 / B 库 / 中间表**三层架构概念，明确"中间表未来可替换为 Notion/Excel/数据库"。
5. 用户暴露**业务库历史包袱**：A 库只有两层（节目+子节目，扁平），无父子关联。
6. Agent 提出 **`virtual_series` 表方案**（B 库内部聚合，以 TMDb tv_id 聚合），用户接受。
7. Agent 基于 TMDb API 事实（5000/天限额 + `status` 字段 + `number_of_seasons`）给出**智能轮询策略**和**配额估算（~125 次/天）**。
8. 决策：电影完全跳过功能 2；功能 2 不受 `hot_score` 阈值约束；保留"⚠️ 待人工确认"作为低置信度收纳类。

**结论：** ADR-0007 提出并 Accepted；6 个已有 ADR 中 5 个不受影响、ADR-0001 第三类输出语义微调、ADR-0004 文字微调。

**完成内容：**
- `docs/decisions/0007-repositioning-to-update-tracking.md` 新建（8 个决策章节）
- `docs/decisions/README.md` 索引追加 0007 行
- `docs/decisions/0001-feishu-baseline-as-marker-not-filter.md` 顶部加注 + 状态更新
- `docs/decisions/0004-phase0-medium-no-auto-promotion.md` 引用章节追加 + 第 56 行术语微调
- `STATE.md` 三处更新（Phase 1.5 阶段标记、待办依赖图、待用户决策项）

---

### 主线 2：P1.5-A 任务包起草并执行（文档翻转）

**触发原因：** 主线 1 决策需要把 V1 全部产品文档（requirements / SCOPE / product_roadmap）对齐到新定位。

**完成内容：**

1. **任务包起草：** `docs/tasks/p1.5_a_documentation_repositioning.md` 新建。任务包内含 21 处 requirements.md 修改 + 4 处 SCOPE.md + 5 处 product_roadmap.md + 2 处 ADR 微调，附 8 条验证命令。
2. **任务包执行：** 按任务包内容逐处修改。详见"数字总结"。

**关键改动摘要：**

- **§ 1 项目背景重写：** 从"是推荐系统"翻转为"主要有三个功能 + 四个'不是'"。
- **§ 6.1 业务流程图：** 从 2 条路径（A 全网 / B 基线标记）扩展为 3 条（新增 C：基线主动追踪）；输出分类两类 + 1 低置信度。
- **§ 6.2 关键变化对比表：** 从 2 列对比扩展为 3 列（旧版 / V1 / V1.5）。
- **§ 7.4 新增小节：** 检测与导出解耦（`daily-discover` + `export-recommendations`）。
- **§ 12 整体改写：** 飞书表语义从"协作视图"明确为"中间表"。
- **§ 12.2 字段大改：** 删除 6 字段（`audience_relevance` / `ai_reason` / `baseline_match_status` / `review_status` / `batch_id` / `discovery_run_type`），新增 `match_confidence_low`。
- **§ 12.5 整段删除（用注解保留）。**
- **§ 14 R7-R10 调整：** R7/R8 微调字段集，R9/R10 标记"V1.5 起移出系统职责范围"但章节保留作为历史。
- **§ 14 R13 新增：** 基线内容主动追踪需求（8 条验收标准）。
- **§ 17 参考资料：** 追加 TMDb TV Details API 链接。

**验证结果：**

```
1. 旧词汇彻底清除验证（"推荐系统/推荐表/待人工审核"）
   docs/requirements.md: 1 行 → 检查后为"不是推荐系统"的否定语义，✅ 合法
   docs/product_roadmap.md: 1 行 → 同上 ✅
   SCOPE.md: 1 行 → 同上 ✅

2. 新词汇出现验证（"更新追踪/中间表/建议更新表/virtual_series/A 库/B 库"）
   docs/requirements.md: 81 处匹配 ✅

3. ADR-0007 引用验证
   5 个目标文件全部引用 ✅

4. R13 新需求验证：3 处提及 ✅

5. STATE.md Phase 1.5：3 处更新 ✅

6. 删除字段在文档中的位置：全部在合法上下文（V1.5 删除字段表格 / V1.5 移出注解 / 否定语义）✅

7. match_confidence_low 新字段：11 处出现，覆盖 § 6.1 / § 9 / § 12.2 / § 13 / R8 / R11 ✅
```

**意外波折：**
- 第一次 Edit `STATE.md` 失败 3 次，原因：会话开头快照中"全角圆括号 `（）`"被渲染为半角 `()`，实际文件是全角。用 `Bash head` 强制重读后修正。**教训：** 遇 Edit 失败首先用 Bash head 重读文件实际字符，不依赖会话快照。
- 一次 Edit `requirements.md § 12.3` 时,`new_string` 末尾意外粘贴 `</parameter></invoke>` 标签，立即检测到并清除。**教训：** 写复杂多段落 new_string 时，结尾要核查。

---

## 关键决策记录

### 决策 1：路径选择 — 路径乙（完整实现）

- **背景：** 用户重新理解产品定位，与现有文档有 21 处冲突。
- **判断：** 不能用文档变通绕过（违反 CLAUDE.md 第 9 条），也不应完全重做 V1（浪费 60-70% 可保留代码）。
- **取舍：** V1.5 是"翻新"，保留算法层和基础设施，重做语义层 + 新增功能 2。
- **落地：** ADR-0007 § 决策八明确范围限制。

### 决策 2：virtual_series 表方案（B 库内部聚合）

- **背景：** A 库只有两层（节目+子节目），无父子关联；行业网站三层（剧集→季→集）。
- **判断：** 不动 A 库（承袭 ADR-0004），在 B 库新增聚合层，复用 schema 已存在但未启用的 `parent_canonical_item_id` 字段，以 TMDb tv_id 为聚合判据。
- **取舍：** 不靠标题字符串聚合（避免拼写误伤）；电影完全跳过（无"季"概念）。
- **落地：** ADR-0007 § 决策三 + R13 新增。

### 决策 3：智能轮询策略（按 TMDb status 分层）

- **背景：** 用户担心 TMDb 配额不足；想要"2 周覆盖完"基线 TV 剧集。
- **判断：** TMDb 限额 50 次/秒，远超需求。按 `status` 分层后估算每日 ~24 次新增调用，加上功能 1 总计 ~125 次/天，配额充足。
- **取舍：** `Returning Series` 2 周；`Ended` 月度；`Canceled/Pilot` 跳过。
- **落地：** ADR-0007 § 决策四 + R13 验收标准 1。

---

## 当前项目状态快照

详见 [`STATE.md`](../STATE.md)。摘要：

- **当前阶段：** Phase 1.5（V1 定位翻转），ADR-0007 Accepted。
- **进行中：** P1.5-A 任务包**执行完成**（本次会话），待用户确认后进入 P1.5-B。
- **待用户决策：** 历史飞书表数据 migration 策略（保留/归档/删除），P1.5 整体派发顺序。

---

## 给下一个 AI Agent 的交接

### 可接任务

按依赖链顺序：

1. **P1.5-B（B库 schema 扩展 + 飞书表 migration）** — 起草任务包。需要先与用户确认"历史飞书表数据"是保留/归档/删除（见 STATE.md § 待用户决策第 3 项）。
2. **P1.5-C（virtual_series 表 + 一次性回填脚本）** — 起草任务包。依赖 B 完成。
3. **P1.5-D（功能 2 基线主动追踪模块）** — 起草任务包。依赖 C 完成。
4. **P1.5-E/F/G** — 起草任务包。E 依赖 B；G 依赖 E；F 依赖 B。

### 不要重做的事

- **不要重新讨论 ADR-0007 的核心决策。** 用户已审定 16 项决策（详见 ADR-0007 § 决策 + 本日报"今日工作主线"）。
- **不要重做 § 12.2 字段集精简。** 已经确定删除 6 字段、新增 `match_confidence_low`。如有疑问优先读 ADR-0007 § 决策六。
- **不要重写 ADR-0001 / ADR-0004。** 已经做了微调（顶部加注 / 引用追加 / 一处术语替换），无需进一步改动。

### 容易被忽略的知识

1. **A 库只读约束：** 系统对 A 库（飞书"线上内容基线表"）**绝不写入**，承袭 ADR-0004 精神。`virtual_series` 表的聚合完全在 B 库内部完成。
2. **功能 2 不受 hot_score 阈值约束：** 这是与功能 1 的重要区别。基线已有剧集的新季无论热不热都写入中间表。
3. **价值字段在不同位置的语义微妙差异：**
   - `priority` 字段：V1.5 起从"人工审核优先级"调整为"下游挑选优先级提示"。
   - 三类输出：V1.5 起"⚠️ 待人工确认"的含义从"系统建议人工审核"变为"实体匹配低置信度，需运营在中间表中判断对应关系"。
4. **§ 12.3 / § 12.4 / R9 / R10 / § 12.5 的章节保留方式：** 不删除原内容，但在顶部加"V1.5 起移出系统职责范围"注解；正文用删除线（`~~...~~`）标记历史内容。这种处理方式承袭 ADR 文档"不删除已废止决策，标记 superseded"精神。
5. **Edit 工具的 old_string 全角/半角陷阱：** 中文文档中"圆括号"可能是全角 `（）`，与会话开头快照渲染的半角 `()` 不一致。遇 Edit 失败先用 `Bash head` 重读。

### 后续派发顺序建议

```
P1.5-A（已完成）
    ↓
P1.5-B（schema + migration）← 用户先确认历史数据处理策略
    ↓
P1.5-C（virtual_series 回填）
    ↓
P1.5-D（功能 2 主动追踪）

并行（B 完成后可起）：
    P1.5-E（飞书写入翻新）→ P1.5-G（检测导出解耦）
    P1.5-F（日报 + CLI 调整）
```

---

## 数字总结

| 项 | 数量 |
|---|---:|
| 新建文件 | 3（ADR-0007、P1.5-A 任务包、本日报） |
| 修改文件 | 7（README.md / STATE.md / SCOPE.md / requirements.md / product_roadmap.md / ADR-0001 / ADR-0004） |
| ADR 新增 | 1（ADR-0007） |
| ADR 微调 | 2（0001 顶部加注、0004 引用追加+L56 术语） |
| `requirements.md` 修改点 | 21 处（按任务包清单完成全部） |
| `SCOPE.md` 修改点 | 4 处 |
| `product_roadmap.md` 修改点 | 6 处（含追加 V1.5 交付物清单） |
| 新增需求条目 | 1（R13 基线内容主动追踪） |
| 删除字段（中间表 schema 文档定义） | 6（audience_relevance / ai_reason / baseline_match_status / review_status / batch_id / discovery_run_type） |
| 新增字段（中间表 schema 文档定义） | 1（match_confidence_low） |
| 整段标记移出（保留作为历史） | 4（§ 12.3 / § 12.4 / § 12.5 / R9 / R10） |
| 验证命令通过 | 8/8 ✅ |
| 代码改动 | 0（按 P1.5-A 非目标约束，不动 src/ 和 tests/）|
| 测试改动 | 0（284 测试维持现状） |

---

## 会话收尾（2026-05-12 凌晨，跨日）

### 主线 3：P1.5-B/C/D 任务包起草

**触发原因：** 用户审定 P1.5-A 通过后，要求"多起草几个任务包，全部串行"。

**完成内容：**
- [docs/tasks/p1.5_b_schema_extension_and_migration.md](../docs/tasks/p1.5_b_schema_extension_and_migration.md) — B 库 schema v4→v5（virtual_series 表 + canonical_items.virtual_series_id + content_updates.match_confidence_low）+ 飞书 schema 操作指导文档
- [docs/tasks/p1.5_c_virtual_series_backfill.md](../docs/tasks/p1.5_c_virtual_series_backfill.md) — virtual_series 一次性回填脚本（TV only，~500 条 TMDb tv details API 调用）
- [docs/tasks/p1.5_d_baseline_active_tracking.md](../docs/tasks/p1.5_d_baseline_active_tracking.md) — 功能 2 主追踪模块 + 智能轮询调度器 + `baseline-track` CLI 子命令

**P1.5-E/F/G 决策：** 推迟到 D 完成后再起草，理由是 E/F/G 依赖 D 的实际产出和真实数据反馈，提前起草易失效。

**STATE.md 同步更新：**
- Phase 1.5 待办依赖图（全部串行 A→B→C→D→E→F→G）
- 新增 Phase 1.6（首次真实运行 + 1-2 周观察）、Phase 1.7（条件性调优）
- 4 项待用户决策（包括各任务包内置的 Q1-Q8）
- Housekeeping 待办：docs/tasks/ 子目录治理（本会话评估后决定推迟）

### 主线 4：用户决策回填

**P1.5-B Q1 / Q2 已决策：**
- Q1（历史飞书表数据）= **直接删除**（飞书表清空重建）
- Q2（B 库 content_updates 旧字段）= **drop 旧字段或重建表**

P1.5-B 任务包正文已记录（待执行时按此决策实施 migration SQL）。

### 主线 5：会话收尾清理

- **`.gitignore`** 新增 `source_records/`（V1 P1-F dry-run 审计日志，运行产物）
- **`.claude/settings.json`** 还原本地改动（用户授权 `git checkout`）
- **STATE.md** 加入 Housekeeping 待办（docs/tasks 子目录治理推迟到 P1.5 完成后）
- 评估"文档治理"后建议跳过（35 处交叉引用修复成本/收益不对等），用户同意

### 关键决策记录（2026-05-12 凌晨追加）

#### 决策 4：E/F/G 任务包推迟起草

- **背景：** 用户要求"多起草几个"。Agent 评估后认为 B/C/D 是基础设施 + 核心新功能，E/F/G 是应用层翻新依赖 D 实际产出。
- **判断：** 任务包是"开工前合同"，长期不动易失效。
- **取舍：** 本次只起 B/C/D，E/F/G 等 D 完成后照"设计预研笔记"起草。
- **落地：** STATE.md 标记 E/F/G "待 D 完成后起草任务包"。

#### 决策 5：文档治理推迟

- **背景：** 17 个任务包散在 `docs/tasks/` 顶层，有美观治理需求。
- **判断：** 移动 + 35 处交叉引用修复，风险高于收益，且不阻塞 P1.5-B 执行。
- **取舍：** 本会话不做，STATE.md Housekeeping 加待办。
- **落地：** STATE.md § Housekeeping 节。

### 数字总结（本次会话累计，含跨日）

| 项 | 数量 |
|---|---:|
| Git commit | 2（Commit A：V1 归档清理 / Commit B：P1.5 产出） |
| 新建 P1.5 任务包 | 4（A/B/C/D） |
| 新建 ADR | 1（0007） |
| ADR 微调 | 2（0001 / 0004） |
| `requirements.md` 修改点 | 21 |
| `SCOPE.md` 修改点 | 4 |
| `product_roadmap.md` 修改点 | 6 |
| `STATE.md` 累计修改 | 5（三个阶段：P1.5 启动 / Housekeeping 待办 / 会话收尾） |
| 跨日会话日报追加段 | 1 |
| 代码改动 | 0（P1.5-A 严格约束） |
| 测试改动 | 0 |
| 待执行 P1.5 任务包（B/C/D） | 3 个，已起草待审定 |
