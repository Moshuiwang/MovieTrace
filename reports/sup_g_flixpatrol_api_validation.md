# SUP-G FlixPatrol 付费 API 功能验证报告

## 1. 摘要

- **验证日期：** 2026-05-11
- **订阅 plan：** Start（$9.99/月，1,000 calls/month）
- **调用 endpoint 数：** 6 平台 × 1 地区（united-states）× 1 内容类型（Movies）
- **API 版本：** v2（`https://api.flixpatrol.com/v2/top10s`）
- **认证方式：** HTTP Basic Auth（API key 作为 username，无密码）

| 验证项 | 结论 | 详情 |
|--------|------|------|
| 连通性与鉴权 | ✅ 通过 | 6/6 平台返回 200 |
| 6 平台覆盖 | ✅ 通过 | Netflix / Prime Video / Disney+ / Apple TV+ / HBO Max / Hulu 全部可获取 |
| 字段完整度 | ✅ 通过 | P1-C 必须字段全部齐备，TMDb ID 直接可用 |

**结论：FlixPatrol $9.99 API 可以替代 HTML 爬虫作为 P1-B 数据来源。推荐 API 路径。**

---

## 2. 连通性与鉴权

### 认证测试

- **API key 来源：** `/tmp/movietrace_phase0_secrets.json` → `flixpatrol.api_key`
- **Key 状态：** 已加载，已脱敏处理（`aku_********************Bpx6`）
- **认证结果：** `aku_` 前缀 key 通过 HTTP Basic Auth 成功认证
- **无 401/403 错误**，认证机制正常工作

### 响应性能

| 平台 | 响应时间 | 状态 |
|------|----------|------|
| Netflix | 937ms | 200 |
| Prime Video | 1,655ms | 200 |
| Disney+ | 979ms | 200 |
| Apple TV+ | 28,734ms | 200（60s timeout） |
| HBO Max | 1,219ms | 200 |
| Hulu | 924ms | 200 |

- **P50 响应：** ~1,000ms（不含 Apple TV+）
- **P95 响应：** ~1,700ms（不含 Apple TV+）
- **Apple TV+ 异常：** 首次 30s 超时，60s timeout 后成功（28.7s）。属服务端延迟波动，非 API 不可用。P1-B 实现建议默认 60s timeout，并对该平台增加重试逻辑。

### 错误响应格式

API 错误以 JSON 返回，格式为：
```json
{"error": {"action": "readAll", "code": "validation", "message": "..."}}
```
格式清晰、可解析。验证过程中观察到的错误类型：
- 参数格式错误 → 400 + validation message（参数调试阶段）
- 超时 → URLError（仅 Apple TV+ 首次请求）

---

## 3. 6 平台覆盖完整性

### 验证策略

- 全 6 平台 × United States × Movies（type=2）× Daily（date[type]=1）
- API 默认返回最早的 300 条记录（30 天数据），通过 `date[from][gte]` 参数可筛选日期

### 平台端点与结果

| # | 平台 | Company ID | 条目数 | 排名范围 | HTTP |
|---|------|-----------|--------|----------|------|
| 1 | Netflix | `cmp_IA6TdMqwf6kuyQvxo9bJ4nKX` | 300 | 1-10 | 200 |
| 2 | Prime Video | `cmp_qypvowjqFhEIpCc0HlQ6VoYk` | 300 | 1-10 | 200 |
| 3 | Disney+ | `cmp_oGtsgdpOrjIu3XzTEnWPt87Y` | 300 | 1-10 | 200 |
| 4 | Apple TV+ | `cmp_VvmYc7OphiUds0Hgjbz5MESn` | 300 | 1-10 | 200 |
| 5 | HBO Max | `cmp_6UhCvnTeRkgZUtcNGslX9bJL` | 300 | 1-10 | 200 |
| 6 | Hulu | `cmp_9iwHIMYOCvD6zprSPoHgTJau` | 300 | 1-10 | 200 |

- **全部 6 平台返回 Top 10 排名数据**（ranking 值均在 1-10）
- **无缺失或异常平台**
- 注：默认返回最早 300 条（Netflix 样本：2020-03-20 至 2020-04-18），P1-B 需在请求中加 `date[from][gte]=YYYY-MM-DD` 限制日期范围

### 默认响应数据量

- 每次请求返回 **300 items**（对应约 30 天 × 10 名/天）
- 如需更大数据量，可能涉及分页（`links` 字段在响应顶层出现）
- 1,000 calls/月配额下，6 平台 × 30 天/月 = 180 calls/月（每日跑），配额充足

---

## 4. 字段完整度对齐需求

### API 响应字段 vs P1-C hot_score 评分需求

| P1-C 需求字段 | 用途 | 必须/期望 | API 字段映射 | 状态 |
|--------------|------|-----------|-------------|------|
| title | 与 TMDb 匹配 | 必须 | `movie.data.title` | ✅ 字符串 |
| content_type | 分类、去重 | 必须 | `type`（2=movie, 3=tv show） | ✅ 整数枚举 |
| ranking | 评分权重 | 必须 | `ranking` | ✅ 1-10 |
| days_in_top10 | 持续热度 | 期望 | `daysTotal` | ✅ 可为 null |
| platform 标识 | 区分 6 平台 | 必须 | `company.data.id`（如 `cmp_IA...`） | ✅ |
| region 标识 | 区分榜单 | 必须 | `country.data.id`（如 `cnt_iM...`） | ✅ |
| snapshot_date | 时间维度 | 必须 | `date.from` / `date.to` | ✅ YYYY-MM-DD |
| TMDb ID | 与 canonical_items 链接 | 必须 | `movie.data.tmdbId` | ✅ 整数 |

**全部 8 项需求字段均可在 API 响应中直接获取，无字段缺失。**

### TMDb ID 可获取性

- **策略：直接获取**（优于 HTML 路径的 title+year 检索）
- `movie.data.tmdbId` 在 100% 采样条目中出现（300/300 验证通过）
- 这对 P1-B 是重大利好：无需二次调用 TMDb 搜索 API，节省开发量和 API 调用成本

### 响应数据结构（复合文档格式）

```json
{
  "links": {...},
  "type": "top10s",
  "data": [
    {
      "type": "top10s",
      "data": {
        "movie": {
          "type": "titles",
          "data": {
            "title": "Spenser Confidential",
            "tmdbId": 581600,
            "imdbId": 8629748
          }
        },
        "company": {"type": "companies", "data": {"id": "cmp_..."}},
        "country": {"type": "countries", "data": {"id": "cnt_..."}},
        "ranking": 1,
        "type": 2,
        "date": {"type": 1, "from": "2020-03-20", "to": "2020-03-20"},
        "daysTotal": null,
        "value": 10,
        "rankingLast": 0
      },
      "legacy": {"id": 988}
    }
  ]
}
```

- 采用 **JSON:API 风格复合文档**，嵌套实体（movie/company/country）通过 `type` + `data` + `legacy` 结构关联
- 解析时需从 `response["data"][i]["data"]` 提取 item 级别的扁平字段
- `movie`、`company`、`country` 为嵌套关联对象，需再深入 `.data` 取实际属性

---

## 5. 与 HTML 路径的对比表

| 维度 | API 路径（$9.99/mo） | HTML 路径（SUP-B） |
|------|---------------------|-------------------|
| **数据获取** | 结构化 JSON，字段固定 | CSS selector 解析，依赖 DOM 结构 |
| **TMDb ID** | 直接提供 `movie.data.tmdbId` | 无，需 title+year 二次检索 |
| **合规** | 付费订阅，按 ToS 使用 | 条件接入（24h 缓存 + 2s 间隔 + UA） |
| **可靠性** | 稳定 schema（复合文档格式） | 受 HTML 改版影响，需维护 parser |
| **成本** | $9.99/月（1,000 calls） | 0（但有人力维护成本） |
| **调用量** | 180 calls/月（6 平台 × 30 天），占配额 18% | 无配额限制，但慢（每 call ~2s） |
| **改版风险** | 低（API versioning） | 中高（HTML 结构无保证） |
| **数据粒度** | 天级 Top 10，可聚合到周/月 | 天级 + 周榜（两个页面） |
| **获取速率** | ~1s/call（Apple TV+ 除外） | ~2s/call + 2s 合规间隔 = ~4s |
| **额外信息** | IMDB ID、value（热度分）、多语言 | 有限（页面上可见的部分） |

---

## 6. 路径决策建议

### 推荐：API 路径 ✅

**理由：**

1. **TMDb ID 直接可用**是最强论据。HTML 路径需在 P1-B 增加 TMDb 搜索环节（调用 TMDb API 或本地匹配），API 路径完全跳过这个步骤，P1-B 工作量显著下降。
2. 字段完整性无需互补：HTML 路径含有的所有数据 API 都有，且更多（IMDB ID、value 热度分、历史 rankingLast）。
3. $9.99/月成本低于人力维护 HTML parser 的成本。
4. 1,000 calls/月的配额对每日 6 平台 × 2 类型（movie + tv）= 12 calls/天的频率绰绰有余。

### 后续动作清单

| 优先级 | 动作 | 负责人 |
|--------|------|--------|
| P0 | 用户确认"API 路径"决策 | 用户 |
| P1 | 新增 ADR-0006：P1-B 数据源从 HTML 切换到 API | Agent |
| P1 | 写 P1-B 任务包（API 客户端 + 入库），废弃原 HTML 方案设计 | Agent |
| P2 | P1-B 实现时注意：60s timeout、`date[from][gte]` 日期筛选、复合文档解包 | Agent |
| P2 | `src/movietrace/sources/flixpatrol.py`（HTML parser）保留为参考或删除按 P1-B 任务包决定 | Agent |
| P3 | 评估是否同时拿 type=3（TV Shows），增加日耗到 12 calls | 用户 + Agent |

### 给 P1-B 任务包的技术输入

- **API Base URL:** `https://api.flixpatrol.com/v2`
- **Endpoint:** `GET /top10s`
- **Auth:** `Authorization: Basic base64(<api_key>:)`
- **必须参数:** `company[eq]`, `country[eq]`, `date[type][eq]=1`, `type[eq]=2`（或 3）
- **日期筛选参数（取最新）:** `date[from][gte]=YYYY-MM-DD`, `date[from][lte]=YYYY-MM-DD`
- **Item 解包路径:** `response["data"][i]["data"]`
- **字段映射:** 见 § 4 表格
- **错误处理:** 400 → 参数问题；401/403 → API key 失效；429 → 配额超限

---

## 附录 A：原始响应文件

| 平台 | 文件 |
|------|------|
| Netflix | `data/sup_g_api_responses/netflix_united-states.json` |
| Prime Video | `data/sup_g_api_responses/prime-video_united-states.json` |
| Disney+ | `data/sup_g_api_responses/disney-plus_united-states.json` |
| Apple TV+ | `data/sup_g_api_responses/apple-tv-plus_united-states.json`（独立重试获取） |
| HBO Max | `data/sup_g_api_responses/hbo-max_united-states.json` |
| Hulu | `data/sup_g_api_responses/hulu_united-states.json` |

注：`data/` 目录在 `.gitignore` 中，不进 git。

## 附录 B：验证命令与结果

```bash
# 干跑（secrets 加载检查）
PYTHONPATH=src python scripts/sup_g_flixpatrol_api_check.py --dry-run
# → DRY RUN PASSED

# 完整运行
PYTHONPATH=src python scripts/sup_g_flixpatrol_api_check.py > /tmp/sup_g_result.json
# → summary.success=5 (main run; Apple TV+ 30s timeout)
# → summary.success=6 (after individual retry with 60s timeout)

# 单元测试
PYTHONPATH=src python -m pytest tests/test_sup_g_flixpatrol_api.py -v
# → 25 passed
```
