# FlixPatrol 可访问性验证报告 (SUP-A)

> 验证目标：确认 FlixPatrol 公开页面是否可作为 V1 数据源  
> 验证日期：2026-05-10T13:43:03Z  
> 执行环境：本机 Python 3.12.3 / stdlib only（无外部依赖）  
> 任务包：[docs/tasks/sup_a_flixpatrol_accessibility.md](../docs/tasks/sup_a_flixpatrol_accessibility.md)  
> 生成脚本：`scripts/sup_a_flixpatrol_check.py`

---

## 1. 验证摘要

| 指标 | 结果 |
|------|------|
| 总目标 URL 数 | 7 |
| HTTP 200 成功 | **6** |
| 4xx 客户端错误 | 1（HBO 路径 404） |
| 5xx 服务端错误 | 0 |
| 网络错误 | 0 |
| robots.txt 禁止 | 0 |
| 初步结论 | **✅ 可访问**（6/7 成功，超过阈值 5） |

> 判断依据：成功 ≥ 5 → ✅ 可访问；成功 2-4 → ⚠️ 部分可访问；成功 ≤ 1 → ❌ 不可访问

---

## 2. robots.txt 分析

**获取状态：** ✅ 已获取（HTTP 200）  
**文件保存路径：** `data/flixpatrol_robots.txt`  
**Crawl-delay：** 未对我们的 User-Agent 设置（默认无限制）

### 目标路径权限

| 路径 | 状态 |
|------|------|
| `/top10/netflix/` | ✅ 允许 |
| `/top10/netflix/united-states/` | ✅ 允许 |
| `/top10/amazon-prime/world/` | ✅ 允许 |
| `/top10/disney/world/` | ✅ 允许 |
| `/top10/apple-tv/world/` | ✅ 允许 |
| `/top10/hbo/united-states/` | ✅ 允许 |
| `/top10/hulu/united-states/` | ✅ 允许 |

### 关键规则摘录

```
User-agent: GPTBot
User-agent: ClaudeBot
User-agent: Claude-Web
User-agent: meta-externalagent
...（AI 爬虫列表）
Disallow: /

User-agent: AhrefsBot
User-agent: PetalBot
...（SEO 爬虫）
Crawl-delay: 10

User-agent: *
Allow: /
```

**结论：** robots.txt 明确对 `User-agent: *`（包括我们的 `MovieTraceBot`）设置 `Allow: /`，允许访问所有路径；AI 专属爬虫（ClaudeBot、GPTBot 等）被单独禁止。

> ⚠️ **重要发现**：Python 标准库 `urllib.robotparser.RobotFileParser.read()` 方法会以 Python 默认 User-Agent 发起第二次请求，服务器对此返回 403，导致 `disallow_all=True` 误判。本脚本已修复为使用 `rp.parse(content.splitlines())`，直接解析已抓取内容，确保结果准确。

---

## 3. URL 访问详情

| 平台 | 路径 | 状态码 | 响应时间 | 内容大小 | HTML 已保存 |
|------|------|--------|----------|----------|------------|
| Netflix（全球） | `/top10/netflix/` | 200 | 582 ms | 227 KB | ✅ `netflix_global.html` |
| Netflix（美国） | `/top10/netflix/united-states/` | 200 | 617 ms | 84 KB | ✅ `netflix_us.html` |
| Amazon Prime（全球） | `/top10/amazon-prime/world/` | 200 | 1841 ms | 202 KB | ✅ `amazon_prime_world.html` |
| Disney+（全球） | `/top10/disney/world/` | 200 | 1846 ms | 228 KB | ✅ `disney_world.html` |
| Apple TV+（全球） | `/top10/apple-tv/world/` | 200 | 883 ms | 261 KB | ✅ `apple_tv_world.html` |
| HBO Max（美国） | `/top10/hbo/united-states/` | **404** | 2490 ms | — | ❌ 未保存 |
| Hulu（美国） | `/top10/hulu/united-states/` | 200 | 578 ms | 69 KB | ✅ `hulu_us.html` |

响应时间范围：578 ms – 1846 ms，中位数约 750 ms，P95 < 2500 ms，满足任务包期望（< 5 秒）。

---

## 4. 失败 URL 分析

### HBO Max: `https://flixpatrol.com/top10/hbo/united-states/`

- **错误类型：** HTTP 404 Not Found
- **可能原因：** URL 路径推测有误。HBO Max 已于 2023 年更名为"Max"，FlixPatrol 上的对应路径可能已变更（如 `/top10/max/united-states/`）。
- **影响：** 低。其余 6 个平台（含 Netflix、Prime Video、Disney+、Apple TV+、Hulu）均可访问，已覆盖 V1 核心需求。
- **建议：** 手动访问浏览器确认 HBO/Max 实际路径。可于 SUP-B 阶段同步修正，不影响总体可行性结论。

---

## 5. HTML 样本质量

| 文件 | 大小 | 含 Top-10 数据 | 反爬信号 | 解析可行性 |
|------|------|----------------|----------|-----------|
| `netflix_global.html` | 227 KB | ✅ 是 | ❌ 无 | ✅ 直接可解析 |
| `netflix_us.html` | 84 KB | ✅ 是 | ❌ 无 | ✅ 直接可解析 |
| `amazon_prime_world.html` | 202 KB | ✅ 是 | ❌ 无 | ✅ 直接可解析 |
| `disney_world.html` | 228 KB | ✅ 是 | ❌ 无 | ✅ 直接可解析 |
| `apple_tv_world.html` | 261 KB | ✅ 是 | ❌ 无 | ✅ 直接可解析 |
| `hulu_us.html` | 69 KB | ✅ 是 | ❌ 无 | ✅ 直接可解析 |

**是否疑似 JavaScript 渲染：** ❌ 否。所有 6 个 HTML 均包含服务端渲染的 Top-10 数据，内容丰富（69 KB – 261 KB），无需 headless browser。

**初步解析可行性：** ✅ HTML 直接可解析（推测为服务端渲染页面，BeautifulSoup 等标准 HTML 解析器即可处理）。

---

## 6. 初步合规观察

> ⚠️ 本节不替代 SUP-D 正式合规评估。仅记录第一手可见事实。

- **robots.txt 第一手结论：** ✅ 允许（`User-agent: *; Allow: /`）
- **Crawl-delay 要求：** 无（对我们的 User-Agent 未设置 Crawl-delay）
- **我们的访问行为（本次验证）：** 8 次请求（含 robots.txt + 基础 URL + 7 个目标 URL），间隔 3 秒，礼貌 User-Agent，单次验证，总耗时约 30 秒
- **注意点：** AI 专属爬虫（ClaudeBot、GPTBot 等）被明确禁止。我们的 `MovieTraceBot` User-Agent 不在禁止列表，属于 `*` 允许范围。
- **重定向发现：** Amazon Prime 和 Disney+ 页面经过重定向，最终仍返回 200。
- **待 SUP-D 评估：** 服务条款（ToS）文本解读、商业用途边界、合规使用频率上限

---

## 7. 给 SUP-B 的输入

**可用 HTML 样本清单：**

| 文件路径 | 大小 | 优先级 | 建议 |
|----------|------|--------|------|
| `tests/fixtures/flixpatrol/netflix_global.html` | 227 KB | 🔴 必须 | 内容最丰富，首选解析目标 |
| `tests/fixtures/flixpatrol/disney_world.html` | 228 KB | 🟠 高 | 内容量大，可验证解析一致性 |
| `tests/fixtures/flixpatrol/amazon_prime_world.html` | 202 KB | 🟠 高 | 含重定向，测试 URL 稳定性 |
| `tests/fixtures/flixpatrol/netflix_us.html` | 84 KB | 🟠 高 | 与 global 同平台，可对比解析结构 |
| `tests/fixtures/flixpatrol/apple_tv_world.html` | 261 KB | 🟡 中 | 最大文件，测试解析性能边界 |
| `tests/fixtures/flixpatrol/hulu_us.html` | 69 KB | 🟡 中 | 最小文件，可作为快速冒烟测试 |

**对 SUP-B 的建议：**
1. 优先解析 `netflix_global.html`，提取标题、排名、平台名，验证数据结构
2. 验证 Top-10 排名条目是否包含：标题、排名数字、内容类型（电影/剧集）
3. 注意 Amazon Prime 和 Disney+ 页面经过服务端重定向，路径可能与请求 URL 不同
4. HBO Max 路径需要修正（建议尝试 `/top10/max/united-states/`），可在 SUP-B 期间补充

---

## 8. 决策建议

**建议：** ✅ **进入 SUP-B（HTML 解析稳定性测试）**

**理由：** 7 个目标 URL 中 6 个返回 HTTP 200，响应时间合理（P95 < 2.5 秒），HTML 内容丰富（服务端渲染，直接可解析，无反爬信号），robots.txt 明确允许 `*` User-Agent 访问所有路径。唯一失败的 HBO Max URL 属于路径推测错误（品牌更名），不影响核心结论。从可访问性角度看，FlixPatrol 作为 V1 数据源具备充分技术可行性。

**前提条件：**
- SUP-B 需验证 HTML 结构解析稳定性（Top-10 排名数据提取准确率）
- SUP-D 合规评估可与 SUP-B 并行启动，结果不影响 SUP-B 进行

**下一步：**
- [ ] **SUP-B**：HTML 解析稳定性测试（使用本报告 §7 的 6 个 HTML 样本）
- [ ] **SUP-D**：FlixPatrol 服务条款合规评估（并行，不阻塞 SUP-B）
- [ ] 修正 HBO/Max 路径（建议 `/top10/max/united-states/`，可在 SUP-B 阶段验证）

---

*生成脚本：`scripts/sup_a_flixpatrol_check.py`*  
*原始 JSON 数据：`/tmp/sup_a_result.json`（临时文件，不入版本库）*  
*robots.txt 副本：`data/flixpatrol_robots.txt`（已入版本库，作为合规依据）*
