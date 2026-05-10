# Phase 0+ 补充验证：FlixPatrol 接入

**状态：** 待验证  
**日期：** 2026-05-10  
**前置：** [Phase 0 完成报告](../reports/phase0_completion_report.md)、[Go/No-Go 决策](../reports/go_no_go_decision.md)  
**目标：** 验证 FlixPatrol 作为 V1 关键数据源的可行性、合规性和数据质量

---

## 1. 为什么需要补充验证

### 1.1 背景

Phase 0 的原始规划基于"飞书基线对比新更新"逻辑，数据源限于 TMDb、Trakt、OMDb。

2026-05-10 产品方向重新对齐后，V1 的核心定位变为"全网热门好评内容发现"，这要求引入"真实平台热度信号"——FlixPatrol 是 V1 阶段唯一可行的免费方案。

### 1.2 为什么 FlixPatrol 必要

**TMDb / Trakt 是社区热度，不代表大众用户：**
- TMDb 用户偏向影视迷，对小众独立电影偏爱
- Trakt 是追剧社区，对动漫和深度影迷剧偏爱
- 都不能反映"Netflix Top 10 大众正在看什么"

**FlixPatrol 是事实标准的"流媒体平台 TOP 聚合源"：**
- 聚合了 Netflix、Prime Video、Disney+、Apple TV+、HBO Max、Hulu 等所有主流平台的官方排行榜
- 按地区（Global / US / 各国）和按平台细分
- 公开页面访问（不需要 API Key）

### 1.3 风险

- ⚠️ FlixPatrol 服务条款不明确，需评估爬取边界
- ⚠️ HTML 解析可能因页面结构变化而失败
- ⚠️ 高频访问可能触发反爬
- ⚠️ 与现有 TMDb/Trakt 候选的匹配率未知

---

## 2. 验证目标

### 2.1 核心问题

| 问题 | 重要性 | 通过标准 |
|------|--------|---------|
| FlixPatrol 公开页面是否可稳定访问 | 数据源基础可用性 | 至少 5 个目标 URL 在 1 周内访问成功率 ≥ 95% |
| HTML 解析逻辑是否稳定 | 数据提取可靠性 | 解析准确率 ≥ 95%，字段（标题、排名、平台、地区）完整 |
| 与 TMDb 候选的匹配率如何 | 评分融合可行性 | FlixPatrol 内容能匹配到 TMDb ID 的比例 ≥ 80% |
| 服务条款和合规边界是什么 | 商业生产风险 | 明确合规结论：可接入 / 限制接入 / 不可接入 |
| 礼貌访问频率是否够用 | 长期稳定运行 | 24 小时缓存 + 2 秒间隔下，1 周内不被封禁 |

### 2.2 数据源覆盖目标

需验证 FlixPatrol 能稳定提供：

| 平台 | 地区 | URL 模式 | 优先级 |
|------|------|---------|--------|
| Netflix | Global | `/top10/` | 必须 |
| Netflix | US | `/top10/?country=us` | 必须 |
| Prime Video | US | `/top10/amazon-prime/` | 高 |
| Disney+ | US | `/top10/disney+/` | 高 |
| Apple TV+ | US | `/top10/apple-tv/` | 中 |
| HBO Max | US | `/top10/hbo/` | 中 |
| Hulu | US | `/top10/hulu/` | 中 |

---

## 3. 验证任务清单

### 任务 SUP-A：FlixPatrol 可访问性测试

**时间：** 0.5 天

**步骤：**
1. 用 Python `requests` 库手工访问 5-10 个目标 URL
2. 记录响应时间、状态码、内容长度
3. 测试不同 User-Agent 的影响
4. 测试 IP 来源（本地 vs 服务器）

**输出：**
- 表格：URL × 访问状态 × 响应时间
- 发现的问题（如有）

**验收：**
- 至少 5 个 URL 能成功访问（HTTP 200，HTML 内容完整）

### 任务 SUP-B：HTML 解析稳定性

**时间：** 1 天

**步骤：**
1. 选取 3-5 个典型 URL，下载 HTML 源码
2. 用 BeautifulSoup 或 lxml 编写解析器
3. 提取字段：title、rank、platform、region、week_date、days_in_top10
4. 跨页面验证解析逻辑稳定性
5. 找出页面结构差异并处理

**输出：**
- `src/movietrace/sources/flixpatrol.py`（draft）
- 测试样本 HTML（保存到 `tests/fixtures/`）
- 解析准确率统计

**验收：**
- 至少 95% 的字段能正确提取
- 解析错误有明确的日志和回退策略

### 任务 SUP-C：与现有数据匹配率

**时间：** 0.5 天

**步骤：**
1. 从 FlixPatrol 提取 50-100 条 Top 10 内容
2. 与 TMDb 候选通过 title+year 匹配
3. 用 OMDb 补充匹配（如有 IMDb ID）
4. 统计匹配率和无法匹配的原因

**输出：**
- `reports/flixpatrol_matching_validation.md`
- 匹配率统计

**验收：**
- 至少 80% 的 FlixPatrol 内容能匹配到 TMDb ID

### 任务 SUP-D：服务条款和合规评估

**时间：** 0.5 天

**步骤：**
1. 阅读 FlixPatrol 的 robots.txt
2. 阅读其服务条款（Terms of Service）
3. 检查是否有 API 接口或合作渠道
4. 检查是否有禁止数据采集的明确条款
5. 评估"礼貌爬虫"是否在可接受范围

**输出：**
- `reports/flixpatrol_compliance_assessment.md`
- 决策：可接入 / 限制接入 / 不可接入

**验收：**
- 明确的合规结论（不留模糊地带）
- 如有限制，明确边界（频率、范围、用途）

### 任务 SUP-E：长期稳定性测试

**时间：** 3-7 天

**步骤：**
1. 部署最小化爬虫（24 小时缓存 + 2 秒间隔）
2. 每日运行一次，连续运行 1 周
3. 监控成功率、响应时间、IP 是否被封
4. 测试不同时段访问效果

**输出：**
- 1 周访问日志
- 稳定性报告

**验收：**
- 1 周内成功率 ≥ 95%
- 无 IP 封禁迹象
- 缓存策略有效，不重复抓取

### 任务 SUP-F：综合评估和决策

**时间：** 0.5 天

**步骤：**
1. 汇总 SUP-A 到 SUP-E 的结果
2. 评估接入风险和价值
3. 给出 Go/No-Go 决策

**输出：**
- `reports/flixpatrol_validation_report.md`
- 决策：✅ GO / ⚠️ Conditional GO / ❌ NO-GO

---

## 4. Phase 0+ 验证产出

完成 Phase 0+ 后应有以下产出：

| 文件 | 内容 |
|------|------|
| `src/movietrace/sources/flixpatrol.py` | FlixPatrol 客户端 draft 实现（待 Phase 1 完善） |
| `tests/fixtures/flixpatrol/*.html` | 测试用 HTML 样本 |
| `tests/test_flixpatrol_parser.py` | 解析器单元测试 |
| `reports/flixpatrol_validation_report.md` | 综合验证报告 |
| `reports/flixpatrol_compliance_assessment.md` | 合规评估 |
| `reports/flixpatrol_matching_validation.md` | 匹配率验证 |

---

## 5. Phase 0+ Go/No-Go 决策矩阵

| 验证项 | 通过 | 部分通过 | 不通过 |
|--------|------|---------|--------|
| 可访问性 | ✅ GO | ⚠️ 调整频率/UA重试 | ❌ 寻找替代方案 |
| 解析稳定性 | ✅ GO | ⚠️ 加强容错 | ❌ 解析方案需重做 |
| 匹配率 | ✅ GO | ⚠️ 加强匹配规则 | ❌ V1 不接入 FlixPatrol |
| 合规性 | ✅ GO | ⚠️ 限制使用范围 | ❌ V1 不接入 FlixPatrol |
| 长期稳定性 | ✅ GO | ⚠️ 加强监控 | ❌ V1 不接入 FlixPatrol |

**决策原则：**
- **5 项全部通过 → ✅ GO，进入 Phase 1**
- **任何一项不通过 → ❌ NO-GO，V1 暂不接入 FlixPatrol，回到只用 TMDb/Trakt/OMDb 的方案**
- **2-4 项部分通过 → ⚠️ Conditional GO，加强监控和缓存后进入 Phase 1**

---

## 6. 备选方案（如果 FlixPatrol 不可用）

如果 Phase 0+ 验证 FlixPatrol 不可接入，V1 的备选数据源方案：

### 6.1 备选方案 A：仅用 TMDb + Trakt + OMDb

**调整：**
- hot_score 公式去掉 FlixPatrol 因素，重新分配权重
- 用 TMDb watch_providers + popularity 间接推断平台热度
- 接受"缺真实平台热度"的局限

**优点：** 无新增风险  
**缺点：** 失去最关键的"大众真实热度"信号，V1 价值大幅降低

### 6.2 备选方案 B：Netflix Tudum + 平台官方页面

**调整：**
- 直接爬 Netflix Tudum Top 10 页面
- 其他平台逐一评估爬取可行性

**优点：** 接近真实热度  
**缺点：** 多平台维护成本高、合规风险更大

### 6.3 备选方案 C：推迟"全网热门发现"到 V2

**调整：**
- V1 回到原始规划（基线对比新更新）
- V2 引入付费 API（Watchmode 等）

**优点：** 风险最低  
**缺点：** V1 无法解决"先有鸡还是先有蛋"问题，产品价值受限

---

## 7. 时间预估

| 任务 | 时间 |
|------|------|
| SUP-A 可访问性 | 0.5 天 |
| SUP-B 解析稳定性 | 1 天 |
| SUP-C 匹配率 | 0.5 天 |
| SUP-D 合规评估 | 0.5 天 |
| SUP-E 长期稳定性 | 3-7 天（被动等待） |
| SUP-F 综合评估 | 0.5 天 |
| **总计** | **约 1 周（含被动观察）** |

---

## 8. 验收标准（汇总）

Phase 0+ 整体验收：

1. ✅ 完成 SUP-A 到 SUP-F 全部任务
2. ✅ 输出 3 份验证报告
3. ✅ 给出明确的 Go/No-Go 决策
4. ✅ 如 GO：完成 FlixPatrol 客户端 draft 实现
5. ✅ 如 NO-GO：明确 V1 备选方案

---

## 9. 验证命令

```bash
# 单元测试
python3 -m pytest tests/test_flixpatrol_parser.py -v

# 手工访问测试
python3 -c "from movietrace.sources.flixpatrol import FlixPatrolClient; \
            client = FlixPatrolClient(); \
            print(client.get_netflix_global_top10())"

# 解析稳定性测试
python3 -m pytest tests/test_flixpatrol_parser.py::test_parse_netflix_top10 -v
```

---

## 10. 风险提示

1. **服务条款风险：** FlixPatrol 可能不允许大规模数据采集，需法律评估
2. **页面结构变化：** HTML 解析可能因 FlixPatrol 改版而失败，需监控告警
3. **IP 封禁风险：** 高频访问可能被反爬，需礼貌频率 + 缓存
4. **数据时效性：** FlixPatrol 数据更新可能有 1-2 天延迟
5. **匹配模糊性：** 标题在 FlixPatrol 和 TMDb 可能不一致（如 "The Bear" vs "The Bear (TV Series)"）

---

## 11. 后续行动

完成 Phase 0+ 后，根据决策：

- **✅ GO：** 进入 Phase 1，按 [next_steps_plan.md § 5](next_steps_plan.md) 执行
- **⚠️ Conditional GO：** 加强监控和缓存后进入 Phase 1
- **❌ NO-GO：** 评估备选方案 A/B/C，必要时调整 V1 范围

---

**文档创建：** 2026-05-10  
**预计完成：** Phase 0+ 启动后 1 周内  
**决策点：** Phase 0+ → Phase 1
