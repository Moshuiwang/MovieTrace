# 任务包：SUP-G FlixPatrol 付费 API 功能验证

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** 2026-05-11（0.5 - 1 天）

---

## 任务名称

SUP-G：FlixPatrol 付费 API（$9.99/月）连通性、6 平台覆盖、字段完整度验证

## 任务类型

`verify` — 验证任务（脚本 + 报告，不改产品代码）

## 当前阶段

Phase 1（V1 MVP 开发）— 路径决策前置验证

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`
- **commit 策略：** 完成后准备 commit，但**不要 push**；由用户审阅后决定是否推送
- **与并行 Agent 的隔离：** 本任务文件改动范围（见"允许修改范围"）与其他任务不重叠，可安全直接执行

## 来源任务

- 用户决策（2026-05-11）：考虑用 FlixPatrol 付费 API 替代 HTML 爬虫，决定 P1-B 实现路径
- 关联 ADR：[`docs/decisions/0003-flixpatrol-as-v1-data-source.md`](../decisions/0003-flixpatrol-as-v1-data-source.md)（Accepted，HTML 路径）
- 关联备选评估：[`reports/flixpatrol_compliance_report.md`](../../reports/flixpatrol_compliance_report.md) § 付费 API 部分

## 目标

**回答一个问题：** FlixPatrol $9.99 月度 API plan 能否替代 HTML 爬虫，作为 P1-B 的数据来源？

具体验证三项（用户 2026-05-11 选定）：

1. **连通性与鉴权** — API key 能调通、返回 200、错误响应格式清楚
2. **6 平台覆盖完整性** — Netflix / Prime Video / Disney+ / Apple TV+ / HBO Max / Hulu 全部可拿 Top 10
3. **字段完整度对齐需求** — API 字段能覆盖 P1-C `hot_score` 评分所需（title、content_type、ranking、days_in_top10、platform ID、可适配 TMDb ID）

## 非目标

- ❌ 不验证 rate limit / 配额 / 定价细节（用户口径：购买后再看官网）
- ❌ 不评估付费 API 服务条款合规（API 是付费产品，合规由订阅关系覆盖，不需要重做 SUP-D）
- ❌ 不实现 P1-B HTTP 客户端、缓存、DB schema —— SUP-G 通过后再写
- ❌ 不修改任何 `src/movietrace/` 产品代码
- ❌ 不引入新的 Python 依赖（沿用 SUP-A 的 stdlib 风格，最多加 `requests` 如项目已有）

## 允许修改范围

**新增文件：**

- `scripts/sup_g_flixpatrol_api_check.py` — 验证脚本
- `tests/test_sup_g_flixpatrol_api.py` — 解析/分类逻辑的单元测试
- `data/sup_g_api_responses/*.json` — 每个 endpoint 的原始响应（`data/` 在 `.gitignore`，不进 git）
- `reports/sup_g_flixpatrol_api_validation.md` — 验证报告

**修改文件：**

- 无（本任务不动产品代码）

## 禁止修改范围

- 🚫 `src/movietrace/` 下任何文件
- 🚫 `src/movietrace/sources/flixpatrol.py`（SUP-B 已通过的 HTML 解析器，路径分流后再决定保留还是废弃）
- 🚫 `docs/decisions/0003-flixpatrol-as-v1-data-source.md`（ADR 修订留给路径决策时的 ADR-0006，非本任务）
- 🚫 `data/movietrace.db`
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`

## 相关上下文

**为什么做 SUP-G：**

- SUP-B 已实现 HTML 解析器（48 测试全过），SUP-D 给出 HTML 路径"条件接入"约束（24h 缓存 + 2s 间隔 + UA）
- 用户考虑购买 FlixPatrol $9.99 月度 API：若 API 覆盖 6 平台 + 字段齐全，HTML 路径整套合规约束可作废，P1-B 工作量大幅下降，且不再受 HTML 改版风险
- SUP-G 通过 → P1-B 走 API 路径，新增 ADR-0006 覆盖 ADR-0003 的实施方式；SUP-G 不通过 → P1-B 按原 HTML 路径推进

**API 信息（待执行 Agent 在购买后从用户处获取）：**

- 入口：https://flixpatrol.com/about/api/
- Plan：$9.99/月（最低档）
- API key 存放位置：参照项目惯例 `/tmp/movietrace_phase0_secrets.json`，新增字段 `flixpatrol.api_key`（用户在购买后追加）

**P1-C `hot_score` 评分对字段的依赖（来源 [`docs/requirements.md`](../requirements.md) § 10.2）：**

| 需求字段 | 用途 | 必须 / 期望 |
|---------|------|------------|
| title | 与 TMDb / Trakt / OMDb 匹配 | 必须 |
| content_type（movie / show） | 分类、去重 | 必须 |
| ranking（榜单名次 1-10） | 评分权重 | 必须 |
| days_in_top10 | 持续热度信号 | 期望 |
| platform 标识 | 区分 6 平台 | 必须 |
| region（global / us / ...） | 区分榜单 | 必须 |
| week_date / snapshot_date | 时间维度 | 必须 |
| 可适配 TMDb ID（直接给 ID 或通过 title + year 检索） | 与 canonical_items 链接 | 必须 |

## 输入

### API key

- 用户购买 $9.99 plan 后，把 API key 追加到 `/tmp/movietrace_phase0_secrets.json` 的 `flixpatrol.api_key`
- 脚本启动时优先从该文件读取，缺失时报错退出（不要 fallback 到环境变量，避免误用）

### 目标 endpoint 清单（参考 https://flixpatrol.com/about/api/ 实际文档）

最低验证集（6 平台 × Global 或 US 任一地区即可）：

| # | 平台 | 地区 | 必须 / 期望 |
|---|------|------|------------|
| 1 | Netflix | global / united-states | 必须 |
| 2 | Prime Video | global / united-states | 必须 |
| 3 | Disney+ | global / united-states | 必须 |
| 4 | Apple TV+ | global / united-states | 必须 |
| 5 | HBO Max | united-states | 必须 |
| 6 | Hulu | united-states | 必须 |

**实际 endpoint 路径由 API 文档决定。** 脚本应能配置 endpoint 列表，逐个调用，失败的单独记录。

## 输出

### 1. 验证脚本：`scripts/sup_g_flixpatrol_api_check.py`

**功能：**

- 从 `/tmp/movietrace_phase0_secrets.json` 读取 `flixpatrol.api_key`
- 顺序调用 6 个平台的 endpoint，间隔 ≥ 1 秒（保守）
- 每个 endpoint 的原始响应保存到 `data/sup_g_api_responses/<safe_name>.json`
- 输出汇总 JSON 到 stdout，含每个 endpoint 的：HTTP 状态、响应时间、条目数、字段集合、错误信息
- 输出可读汇总到 stderr

**JSON 汇总格式：**

```json
{
  "run_at": "2026-05-11T...Z",
  "auth": {
    "key_loaded_from": "/tmp/movietrace_phase0_secrets.json",
    "key_present": true
  },
  "endpoints": [
    {
      "platform": "netflix",
      "region": "global",
      "url": "https://flixpatrol.com/api/...",
      "status_code": 200,
      "response_time_ms": 532,
      "item_count": 10,
      "fields_present": ["title", "content_type", "ranking", "days_in_top10", "tmdb_id", ...],
      "fields_missing_vs_required": [],
      "saved_to": "data/sup_g_api_responses/netflix_global.json",
      "error": null
    }
  ],
  "summary": {
    "total_endpoints": 6,
    "success": 6,
    "platform_coverage_ok": true,
    "required_fields_all_present": true,
    "tmdb_id_strategy": "direct | title_year_lookup | both"
  }
}
```

### 2. 单元测试：`tests/test_sup_g_flixpatrol_api.py`

- 字段映射逻辑（API JSON → 评分需求字段）的纯函数测试
- 缺字段时的判定逻辑
- 不强制网络测试（用 fixture JSON 而非真请求）

### 3. 验证报告：`reports/sup_g_flixpatrol_api_validation.md`

**报告结构：**

```markdown
# SUP-G FlixPatrol 付费 API 功能验证报告

## 1. 摘要
- 验证日期、订阅 plan、调用 endpoint 数
- 三项验证结论（连通性 / 平台覆盖 / 字段完整度），各自 ✅ / ⚠️ / ❌

## 2. 连通性与鉴权
- API key 是否通过认证
- 错误响应格式（401 / 403 / 429 等）观察
- 响应时间 P50 / P95

## 3. 6 平台覆盖完整性
- 每平台返回条目数、是否符合 Top 10 预期
- 缺失或异常的平台、原因

## 4. 字段完整度对齐需求
- 对照 P1-C `hot_score` 字段清单逐项检查
- TMDb ID 可获取性（直接给 / title+year 检索 / 不可得）
- 缺字段对评分的影响

## 5. 与 HTML 路径的对比表
- API 路径 vs HTML 路径在数据获取、合规、成本、改版风险上的对比

## 6. 路径决策建议
- 推荐：API 路径 / HTML 路径 / 混合
- 后续动作清单（明天起的 P1-B 设计调整 + 是否需要 ADR-0006）
```

## 具体要求

### R1: 安全访问

- API key 不进 git（脚本仅从 secrets 文件读，不打印到 stdout 完整 key）
- 日志中 key 必须脱敏（保留前 4 后 4，中间打码）

### R2: 错误处理

- 401 / 403 → 立即停止，提示 API key 配置问题
- 429 → 退避 5 秒重试 1 次，仍 429 则放弃该 endpoint 并记录
- 5xx → 记录后继续下一 endpoint
- 网络错误 → 记录后继续

### R3: 不污染产品代码

- 脚本独立放 `scripts/`，不进 `src/movietrace/`
- 不写入 `data/movietrace.db`
- 不调用 `src/movietrace/sources/flixpatrol.py`（HTML 解析器）

### R4: 中文输出

- 报告 `reports/sup_g_flixpatrol_api_validation.md` 用中文
- 脚本注释和日志可英文

## 验收标准

### 必须达成（否则 NO-GO）

1. ✅ 脚本能正常运行，无 Python 异常崩溃
2. ✅ API key 从 secrets 文件读取成功
3. ✅ 至少调用了 6 个平台的 endpoint（即使部分失败）
4. ✅ 每个 endpoint 的原始响应保存到 `data/sup_g_api_responses/`
5. ✅ 单元测试 `pytest tests/test_sup_g_flixpatrol_api.py -v` 全部通过
6. ✅ 验证报告生成且包含 6 个章节
7. ✅ 给出明确的"P1-B 走 API / HTML / 混合"决策建议

### 期望达成

8. 6 平台全部返回 200，条目数符合预期（Top 10）
9. P1-C 需求字段（必须档）全部在 API 响应中出现
10. TMDb ID 可直接从 API 拿到，或通过 title+year 检索能与 SUP-C 100% 匹配率延续

### 不算失败但需记录

11. 部分字段缺失但可通过其他字段推导
12. 某个平台返回数据结构异常但其他 5 个正常

## 验证命令

```bash
# 用户购买 API 并把 key 追加到 secrets 文件后执行：
# /tmp/movietrace_phase0_secrets.json 加入：
# {"flixpatrol": {"api_key": "<key>"}}

# 1. 干跑（不真发请求，只检查 secrets 加载）
PYTHONPATH=src python scripts/sup_g_flixpatrol_api_check.py --dry-run

# 2. 完整运行
PYTHONPATH=src python scripts/sup_g_flixpatrol_api_check.py > /tmp/sup_g_result.json

# 3. 单元测试
PYTHONPATH=src python -m pytest tests/test_sup_g_flixpatrol_api.py -v

# 4. 人工审阅报告
cat reports/sup_g_flixpatrol_api_validation.md
```

## 风险点

### 已识别风险

1. **$9.99 plan 不含 API 访问，或访问受限**
   - 概率：中（部分服务的最低档只给文档预览）
   - 影响：SUP-G 退化为"plan 可用性核查"
   - 缓解：报告中明确写出"哪些功能受限"，给用户决策升级 plan 或回到 HTML 路径

2. **API 文档不公开，需登录后查看**
   - 概率：中
   - 影响：脚本无法预先写好 endpoint 列表
   - 缓解：分两步——先用户登录拿文档，再 Agent 按文档实现脚本

3. **TMDb ID 不直接返回**
   - 概率：中
   - 影响：仍需要 title+year 二次检索 TMDb，但 SUP-C 已证明匹配率 100%
   - 缓解：报告中标注；不视为 SUP-G 失败

4. **API 返回数据粒度与 HTML 不一致**（例如只给月榜不给周榜）
   - 概率：低
   - 影响：评分公式中"持续热度"信号要调整
   - 缓解：报告中对比 HTML 与 API 数据粒度

5. **付费 API 后续涨价或停服**
   - 概率：未知
   - 影响：V1 上线后被动观察
   - 缓解：不在 SUP-G 范围；ADR-0006 中作为后果记录

### 未识别风险

执行中如发现新风险，必须记录到报告 § 6，不要静默处理（CLAUDE.md 规则 9）。

## 路径决策矩阵（SUP-G 完成后由用户拍板，本任务只给建议）

| SUP-G 结果 | 推荐路径 | 后续动作 |
|-----------|---------|---------|
| ✅ 三项全通过 | API 路径 | 写 ADR-0006 切换 P1-B 实现，废弃 HTML 客户端设计 |
| ⚠️ 字段不全但平台齐 | 混合路径 | P1-B 主走 API，缺字段从 HTML 补，复杂度增加 |
| ❌ API 不可用 / 平台缺失 | HTML 路径 | ADR-0003 不动，按原计划写 P1-B HTML 客户端任务包 |

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 格式汇报，重点说明：

- 三项验证各自结论
- 推荐路径（API / HTML / 混合）
- 给后续 P1-B 任务包的输入（字段映射 / endpoint 清单 / 错误码处理）
