# 任务包：SUP-A FlixPatrol 可访问性测试

**任务包版本：** v1  
**创建日期：** 2026-05-10  
**预计完成：** 2026-05-11（0.5 天）

---

## 任务名称

SUP-A：FlixPatrol 公开页面可访问性手工验证

## 任务类型

`verify` — 验证任务（不修改产品代码，只生成验证脚本和报告）

## 当前阶段

Phase 0+（FlixPatrol 接入验证补充阶段）

## 来源任务

- [docs/phase0_supplement.md](../phase0_supplement.md) § 3 任务 SUP-A
- [docs/next_steps_plan.md](../next_steps_plan.md) § 4 Phase 0+ 补充验证
- [docs/product_roadmap.md](../product_roadmap.md) § 2.1 V1 信号源组合

## 目标

**回答一个问题：** FlixPatrol 公开页面是否可以稳定访问，是否值得作为 V1 数据源？

具体来说：
1. 用 Python stdlib 访问 FlixPatrol 5-7 个目标 URL
2. 记录每个 URL 的 HTTP 状态码、响应时间、内容长度
3. 检查 `robots.txt` 是否禁止采集
4. 把每个 URL 的 HTML 保存为本地文件（供 SUP-B 解析使用）
5. 输出验证报告，给出"可访问 / 部分可访问 / 不可访问"的初步结论

## 非目标

- ❌ **不**实现完整的 FlixPatrol 客户端（那是 Phase 1 的 P1-B）
- ❌ **不**做 HTML 解析（那是 SUP-B）
- ❌ **不**做大规模批量访问（只验证 5-7 个 URL）
- ❌ **不**评估服务条款合规性（那是 SUP-D）
- ❌ **不**修改任何产品代码（`src/movietrace/` 下不动）
- ❌ **不**引入新的 Python 依赖（只用 stdlib）
- ❌ **不**做长期稳定性测试（那是 SUP-E）

## 允许修改范围

**新增文件：**
- `scripts/sup_a_flixpatrol_check.py` — 验证脚本（新建 scripts/ 目录）
- `scripts/__init__.py` — 空文件，使 scripts 成为包（如有必要）
- `tests/fixtures/flixpatrol/*.html` — 保存的 HTML 样本（新建目录）
- `reports/flixpatrol_accessibility_report.md` — 验证报告
- `data/flixpatrol_robots.txt` — 保存的 robots.txt 副本

**新增依赖：**
- ❌ 禁止。仅使用 Python 3.12 stdlib（`urllib.request`、`urllib.robotparser`、`time`、`json`、`pathlib`）

## 禁止修改范围

- 🚫 `src/movietrace/` 下任何文件
- 🚫 `data/movietrace.db`（生产数据库）
- 🚫 `tests/` 下已有的测试文件
- 🚫 `docs/` 下任何已有文档
- 🚫 `config/` 下任何配置
- 🚫 `AGENTS.md`、`CLAUDE.md`

## 相关上下文

**项目现状：**
- Phase 0 已完成（826/855 实体匹配，96.6% 准确率）
- 飞书基线、SQLite、TMDb/Trakt/OMDb 已就绪
- 当前 Git commit：`b584e94`（V2 产品方向对齐）

**为什么需要 FlixPatrol：**
- TMDb / Trakt 是社区热度，不代表大众用户
- FlixPatrol 是事实标准的"流媒体平台 TOP 聚合源"
- V1 缺少"真实平台热度"信号，FlixPatrol 是唯一可行的免费方案

**当前项目 HTTP 工具：**
- `src/movietrace/sources/http.py` 用 `urllib.request`（stdlib）
- 只支持 JSON 响应
- 本任务的 HTML 访问应单独写在 `scripts/`，不混入产品代码

## 输入

### 目标 URL 清单

| 序号 | 平台 | 地区 | URL | 优先级 |
|------|------|------|-----|--------|
| 1 | Netflix | Global | `https://flixpatrol.com/top10/netflix/` | 必须 |
| 2 | Netflix | US | `https://flixpatrol.com/top10/netflix/united-states/` | 必须 |
| 3 | Prime Video | World | `https://flixpatrol.com/top10/amazon-prime/world/` | 高 |
| 4 | Disney+ | World | `https://flixpatrol.com/top10/disney/world/` | 高 |
| 5 | Apple TV+ | World | `https://flixpatrol.com/top10/apple-tv/world/` | 中 |
| 6 | HBO Max | US | `https://flixpatrol.com/top10/hbo/united-states/` | 中 |
| 7 | Hulu | US | `https://flixpatrol.com/top10/hulu/united-states/` | 中 |

**重要：** URL 路径是推测，可能与实际不符。脚本应能**自动重试不同 URL 模式**，并报告哪些 404、哪些 200。

### 必须先访问

- `https://flixpatrol.com/robots.txt` — 检查爬虫规则
- `https://flixpatrol.com/` — 验证基础访问

### 访问参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| User-Agent | `Mozilla/5.0 (compatible; MovieTraceBot/0.1; +验证用)` | 礼貌标识 |
| Timeout | 20 秒 | 与现有 `http.py` 一致 |
| 请求间隔 | 3 秒 | 比 SUP-E 的 2 秒更礼貌 |
| 重试次数 | 1 | 验证任务不做激进重试 |

## 输出

### 1. 验证脚本：`scripts/sup_a_flixpatrol_check.py`

**功能：**
- 接受 URL 清单（硬编码或命令行参数）
- 顺序访问每个 URL（带 3 秒间隔）
- 记录：HTTP 状态码、响应时间、Content-Length、Content-Type、最终重定向 URL
- 把成功响应的 HTML 保存到 `tests/fixtures/flixpatrol/<safe_name>.html`
- 把 robots.txt 保存到 `data/flixpatrol_robots.txt`
- 用 `urllib.robotparser` 解析 robots.txt，检查目标 URL 是否被允许
- 输出 JSON 格式的结构化结果到 stdout
- 输出汇总到 stderr（人可读）

**示例运行：**
```bash
python3 scripts/sup_a_flixpatrol_check.py > reports/sup_a_raw_result.json
```

**JSON 输出格式：**
```json
{
  "run_at": "2026-05-11T10:00:00Z",
  "robots_txt": {
    "fetched": true,
    "status_code": 200,
    "rules_for_user_agent": "...",
    "allows_target_paths": [
      {"path": "/top10/netflix/", "allowed": true}
    ]
  },
  "url_checks": [
    {
      "url": "https://flixpatrol.com/top10/netflix/",
      "status_code": 200,
      "response_time_ms": 1245,
      "content_length": 87432,
      "content_type": "text/html; charset=UTF-8",
      "final_url": "https://flixpatrol.com/top10/netflix/",
      "html_saved_to": "tests/fixtures/flixpatrol/netflix_global.html",
      "error": null
    }
  ],
  "summary": {
    "total_urls": 7,
    "success": 6,
    "client_error_4xx": 1,
    "server_error_5xx": 0,
    "network_error": 0,
    "robots_disallowed": 0
  }
}
```

### 2. HTML 样本：`tests/fixtures/flixpatrol/`

每个成功访问的 URL 保存一份 HTML，命名规则：
- `netflix_global.html`
- `netflix_us.html`
- `amazon_prime_world.html`
- `disney_world.html`
- ...

### 3. robots.txt 副本：`data/flixpatrol_robots.txt`

原样保存，作为合规依据。

### 4. 验证报告：`reports/flixpatrol_accessibility_report.md`

**报告结构：**

```markdown
# FlixPatrol 可访问性验证报告 (SUP-A)

## 1. 验证摘要
- 验证日期、运行环境（本机/服务器）
- 总 URL 数、成功数、失败数
- 初步结论：✅ 可访问 / ⚠️ 部分可访问 / ❌ 不可访问

## 2. robots.txt 分析
- 是否允许爬虫
- 关键规则（Crawl-delay、Disallow 路径）
- 我们的 User-Agent 是否被特别处理

## 3. URL 访问详情
- 表格：URL × 状态码 × 响应时间 × Content-Length

## 4. 失败 URL 分析
- 哪些 404（路径错误）、哪些被禁、哪些超时

## 5. HTML 样本质量
- 每个保存的 HTML 大致内容（标题、是否包含 Top 10 数据）
- 是否有反爬迹象（验证码、JavaScript 渲染、登录墙）

## 6. 初步合规观察
- 不替代 SUP-D 的正式合规评估
- 但记录 robots.txt 第一手发现

## 7. 给 SUP-B 的输入
- HTML 样本路径清单
- 可解析性的初步判断

## 8. 决策建议
- 是否进入 SUP-B（解析稳定性测试）
- 如有阻塞，需先解决什么
```

## 具体要求

### R1: 礼貌访问

1. 每次请求间隔 ≥ 3 秒（用 `time.sleep(3)`）
2. User-Agent 必须包含 `MovieTraceBot` 和联系方式或验证目的
3. 访问前先读 robots.txt
4. 如 robots.txt 禁止某路径，跳过该 URL 并记录

### R2: 错误处理

1. 网络错误（`URLError`、`HTTPError`）必须被捕获，不能让脚本崩溃
2. 每个 URL 独立处理，单个失败不影响其他
3. 错误必须记录到 JSON 输出
4. 不做激进重试（最多 1 次重试）

### R3: 数据持久化

1. 成功的 HTML 必须保存到 `tests/fixtures/flixpatrol/`
2. 失败的 URL 不保存 HTML，但保留错误响应（如有）
3. JSON 输出包含 `html_saved_to` 字段，方便 SUP-B 引用

### R4: 不污染产品代码

1. 脚本独立放在 `scripts/`，不进 `src/movietrace/`
2. 不修改任何产品代码
3. 不写入 `data/movietrace.db`
4. 不调用 Phase 0 已实现的任何模块

### R5: 中文输出

1. 报告 `reports/flixpatrol_accessibility_report.md` 用中文撰写
2. 脚本注释和日志可用英文（与现有代码风格一致）
3. 关键决策和结论必须中文表达

## 验收标准

### 必须达成（否则 NO-GO）

1. ✅ 脚本能成功运行，无 Python 异常崩溃
2. ✅ robots.txt 已获取、解析、保存
3. ✅ 至少访问了 7 个目标 URL（即使部分失败）
4. ✅ JSON 输出格式正确，可被其他脚本解析
5. ✅ 验证报告生成且包含全部 8 个章节
6. ✅ 给出明确的"是否进入 SUP-B"决策

### 期望达成

7. 至少 5 个 URL 返回 HTTP 200 且 HTML 长度 > 10KB
8. robots.txt 不禁止 `/top10/` 路径
9. 没有验证码或登录墙阻塞
10. 响应时间 P95 < 5 秒

### 不算失败但需记录

11. 部分 URL 路径 404 → 记录正确路径，留给 SUP-B 修正
12. 部分平台不在 FlixPatrol 覆盖范围 → 记录并评估替代

## 测试要求

**这是验证任务，不强制要求 pytest。但脚本应自带最小化自检：**

1. 启动时检查 Python 版本（>= 3.10）
2. 启动时检查输出目录可写
3. 退出码：0 成功 / 1 部分失败 / 2 全部失败
4. 干跑模式（`--dry-run`）：只检查 robots.txt，不抓取 HTML

## 验证命令

```bash
# 1. 干跑模式（先看 robots.txt）
python3 scripts/sup_a_flixpatrol_check.py --dry-run

# 2. 完整运行
python3 scripts/sup_a_flixpatrol_check.py > /tmp/sup_a_result.json

# 3. 检查输出文件
ls -la tests/fixtures/flixpatrol/
ls -la data/flixpatrol_robots.txt
ls -la reports/flixpatrol_accessibility_report.md

# 4. 检查 JSON 格式
python3 -c "import json; d=json.load(open('/tmp/sup_a_result.json')); print(d['summary'])"

# 5. 人工审阅报告
cat reports/flixpatrol_accessibility_report.md
```

## 风险点

### 已识别风险

1. **URL 路径推测错误**
   - 概率：高（FlixPatrol URL 结构未确认）
   - 影响：部分 URL 404
   - 缓解：脚本继续访问其他 URL，报告中列出 404 路径以便人工修正

2. **IP 被封禁**
   - 概率：低（只访问 7 个 URL + 3 秒间隔）
   - 影响：后续访问全部失败
   - 缓解：礼貌频率 + User-Agent 标识；若发生立即停止并报告

3. **HTML 由 JavaScript 渲染**
   - 概率：中（现代网站常见）
   - 影响：HTML 不含真实数据，需要 headless browser
   - 缓解：在报告中标注，决策是否引入新方案

4. **服务条款不允许**
   - 概率：未知
   - 影响：V1 不能接入 FlixPatrol
   - 缓解：本任务不做最终判断，留给 SUP-D；但 robots.txt 第一手记录在本任务报告

5. **访问需要验证码**
   - 概率：中
   - 影响：脚本会失败
   - 缓解：在报告中明确标注，不绕过

### 未识别风险

任务执行中如发现新风险，必须记录到报告 § 4 或 § 6，不要默默处理。

## 完成后输出要求（汇报格式）

执行完成后，按以下格式汇报（来自 CLAUDE.md）：

```
任务理解：
- 验证 FlixPatrol 公开页面是否可稳定访问，作为 V1 数据源候选

完成内容：
- 创建 scripts/sup_a_flixpatrol_check.py（XX 行）
- 创建 tests/fixtures/flixpatrol/ 目录，保存 N 个 HTML 样本
- 保存 data/flixpatrol_robots.txt
- 生成 reports/flixpatrol_accessibility_report.md

验证结果：
- 脚本运行：成功 / 失败
- robots.txt：允许 / 禁止 / 部分允许
- URL 访问：N/7 成功，平均响应时间 X ms
- HTML 质量：包含 Top 10 数据 / 需 JavaScript 渲染 / 其他

剩余风险：
- 未确定的服务条款边界（待 SUP-D）
- HTML 解析稳定性（待 SUP-B）
- 长期访问稳定性（待 SUP-E）

后续建议：
- 进入 SUP-B / 调整 URL 后重跑 SUP-A / 立即终止 FlixPatrol 接入
```

---

## 附录 A：参考 robots.txt 解析示例

```python
from urllib.robotparser import RobotFileParser

rp = RobotFileParser()
rp.set_url("https://flixpatrol.com/robots.txt")
rp.read()

# 检查我们的 User-Agent 是否能访问目标路径
ua = "MovieTraceBot/0.1"
allowed = rp.can_fetch(ua, "https://flixpatrol.com/top10/netflix/")
crawl_delay = rp.crawl_delay(ua)
```

## 附录 B：URL 命名安全转换示例

```python
def safe_filename(url: str) -> str:
    """https://flixpatrol.com/top10/netflix/united-states/ → netflix_us.html"""
    from urllib.parse import urlparse
    path = urlparse(url).path.strip("/")
    return path.replace("/", "_").replace("-", "_") + ".html"
```

---

**任务包状态：** ✅ 就绪，等待执行  
**预计执行时间：** 3-4 小时（含报告撰写）  
**下一任务：** SUP-D（合规评估，0.5 天）+ SUP-B（解析稳定性，1 天）
