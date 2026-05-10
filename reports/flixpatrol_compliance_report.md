# FlixPatrol 服务条款合规评估报告 (SUP-D)

> 验证目标：评估 FlixPatrol 数据抓取的合规边界，给出可接入 / 限制接入 / 不可接入结论  
> 验证日期：2026-05-10  
> 执行环境：手工访问 + Python stdlib HTTP 请求  
> 任务包：`docs/tasks/sup_d_flixpatrol_compliance.md`

---

## 1. 验证摘要

| 评估项 | 结论 |
|--------|------|
| robots.txt 许可 | ✅ `User-agent: *; Allow: /`，MovieTraceBot 明确允许 |
| 服务条款文本 | ⚠️ 条款页面**内容为空**，无实质性约束条款 |
| 隐私政策文本 | ⚠️ 隐私页面**内容为空**，无实质性内容 |
| 商业 API 存在 | ⚠️ 有付费 API（$9.99/月起），意味着数据有商业价值 |
| 爬虫专项禁止 | ✅ 未明确禁止非 AI 爬虫（仅禁止 ClaudeBot、GPTBot 等 AI 爬虫） |
| 技术反爬措施 | ✅ 无（SUP-A 验证：无验证码、无 JS 渲染、无速率限制信号） |
| **综合结论** | **⚠️ 条件接入** |

---

## 2. robots.txt 分析（第一手依据）

**文件位置：** `data/flixpatrol_robots.txt`（SUP-A 已保存）

### 关键规则

```
User-agent: GPTBot
User-agent: ClaudeBot
User-agent: Claude-Web
User-agent: PerplexityBot
User-agent: Amazonbot
...（AI 爬虫列表）
Disallow: /

User-agent: AhrefsBot
User-agent: SemrushBot
...（SEO 商业爬虫）
Crawl-delay: 10

User-agent: *
Allow: /
```

**解读：**

1. FlixPatrol 明确区分了三类爬虫：
   - **AI 爬虫**（ClaudeBot、GPTBot 等）→ 全面禁止（`Disallow: /`）
   - **SEO 商业爬虫**（AhrefsBot、SemrushBot 等）→ 允许但限速（`Crawl-delay: 10`）
   - **通用爬虫**（`User-agent: *`）→ 允许（`Allow: /`）

2. `MovieTraceBot` 不在任何禁止列表中，属于 `User-agent: *` 范围，**robots.txt 层面明确允许访问**。

3. 对 `User-agent: *` 未设置 `Crawl-delay`，无最低间隔要求。

**注意：** 我们在 SUP-A 验证中发现 Python 标准库 `RobotFileParser.read()` 存在 Bug（二次请求用 Python 默认 UA 导致 403），已修复为直接解析已抓取内容。

---

## 3. 服务条款分析

### 3.1 实际访问情况

| URL | 状态 | 内容 |
|-----|------|------|
| `https://flixpatrol.com/about/terms-and-conditions/` | ✅ HTTP 200 | **内容为空**（仅有导航栏和页脚） |
| `https://flixpatrol.com/about/privacy-policy/` | ✅ HTTP 200 | **内容为空**（仅有导航栏和页脚） |
| `https://flixpatrol.com/terms/` | ❌ HTTP 404 | 不存在 |
| `https://flixpatrol.com/legal/` | ❌ HTTP 404 | 不存在 |

### 3.2 解读

FlixPatrol 在 About 页面列出了"Terms & Conditions"和"Privacy Policy"链接，但对应页面**没有实质性条款文本**。这意味着：

- **无明确禁止数据采集的条款**：无法引用任何条文来禁止我们的访问行为
- **无明确授权数据采集的条款**：同样无法依据条款主张合规
- **法律真空状态**：缺少条款是风险因素，而非绿灯信号

---

## 4. 商业 API 观察

FlixPatrol 提供付费 API，定价如下：

| 套餐 | 价格 | API 调用量 |
|------|------|-----------|
| Start | $9.99/月 | 1,000 次/月 |
| Premium | $49/月（或 $490/年） | 1,000 次/月 + 完整数据集 |
| Enterprise | 定制 | 无限次 |

**合规含义：**

1. **FlixPatrol 将其数据视为商业产品**：存在付费 API 表明数据有明确的商业价值，大规模无偿使用存在隐性冲突。
2. **V1 阶段的访问规模属于"小量研究级"**：24 小时缓存 + 每日最多 10 个 URL，远低于 Start 套餐 1,000 次/月的量级，对其商业利益影响极小。
3. **长期商业化使用应考虑付费 API**：若 MovieTrace 进入规模化运营，建议从付费 API 获取数据。

---

## 5. 我们的访问行为评估

| 评估维度 | V1 阶段计划 | 评估 |
|---------|-----------|------|
| 访问频率 | 24 小时缓存，每页面每天最多 1 次 | ✅ 极低频率 |
| User-Agent | `MovieTraceBot/0.1`（识别性 UA） | ✅ 透明，可识别 |
| 目标 URL 数量 | 约 10 个（5 平台 × 2 地区） | ✅ 极小范围 |
| 数据用途 | 内部推荐系统，非公开发布 | ✅ 非竞争性 |
| 数据转售 | 无 | ✅ |
| robots.txt 遵守 | 完全遵守（`Allow: /` 范围内） | ✅ |
| 爬取深度 | 仅 Top-10 榜单页面，不遍历全站 | ✅ |

---

## 6. 风险因素识别

### 高风险

- 暂无

### 中等风险

1. **服务条款为空的法律模糊性**：无条款保护双方。若未来 FlixPatrol 追加明确禁止条款，当前行为需立即停止。
   - 缓解：定期（每季度）检查条款页面是否更新

2. **付费 API 存在隐含期待**：FlixPatrol 投入了商业 API，暗示其商业模式依赖数据变现。大规模无偿使用在道义上存在争议。
   - 缓解：V1 保持极低访问频率；商业化阶段考虑付费 API

### 低风险

3. **AI 爬虫禁止条款的扩展解释**：robots.txt 明确禁止 ClaudeBot，未来可能扩展到类 AI 用途的爬虫。
   - 缓解：使用非 AI 标识的 User-Agent（`MovieTraceBot`），不以 AI 公司名义访问

4. **技术层面的访问封禁**：即使 robots.txt 允许，服务器仍可单方面封禁 IP 或 UA。
   - 缓解：礼貌间隔（2-3 秒/请求），出错时不重试

---

## 7. 对比：常见开放数据源的合规标准

| 数据源 | robots.txt | ToS 明确授权 | 商业用途 |
|--------|-----------|------------|---------|
| FlixPatrol | ✅ `Allow: *` | ⚠️ 条款为空 | ⚠️ 有商业 API |
| Wikipedia | ✅ 允许 | ✅ CC BY-SA | ✅ 明确允许 |
| IMDb | ❌ 禁止商业爬取 | ❌ 明确禁止 | ❌ |
| TMDb | N/A | ✅ API ToS | ✅（需 API Key） |

FlixPatrol 的合规情况优于 IMDb（明确禁止），弱于 Wikipedia/TMDb（明确授权）。

---

## 8. 决策建议

**结论：⚠️ 条件接入（Conditional GO）**

### 允许的访问方式

在以下条件下，V1 阶段可以接入 FlixPatrol：

1. ✅ 访问频率：每个 URL 每 24 小时最多 1 次，请求间隔 ≥ 2 秒
2. ✅ User-Agent：使用可识别的 `MovieTraceBot/0.1`，不伪装成浏览器
3. ✅ 访问范围：仅访问 Top-10 榜单页面，不遍历其他内容
4. ✅ 数据用途：仅用于内部推荐逻辑，不公开发布 FlixPatrol 原始数据
5. ✅ 持续监控：每季度检查 robots.txt 和条款页面是否有变化

### 必须停止的触发条件

若出现以下任一情况，**必须立即停止访问**：

- ❌ FlixPatrol 在条款页面新增明确的反爬条款
- ❌ robots.txt 将 MovieTraceBot 或通用爬虫加入 Disallow 列表
- ❌ FlixPatrol 通过法律或技术手段发出明确的停止信号

### 长期建议

- **V1（内测阶段）**：按上述条件接入，免费爬取
- **V2（商业化阶段）**：评估 FlixPatrol Start 套餐（$9.99/月），通过官方 API 获取数据

---

## 9. 下一步行动

- [ ] **P1-B**：按本报告约束实现 FlixPatrol HTTP 客户端（24h 缓存 + 2s 间隔 + 礼貌 UA）
- [ ] **季度检查**（建议 2026-08-10）：重新访问 FlixPatrol 条款页面，确认无变化
- [ ] **商业化评估时**：重新评估付费 API 可行性

---

*合规数据：`data/flixpatrol_robots.txt`（已入库）*  
*参考页面：`https://flixpatrol.com/about/terms-and-conditions/`、`https://flixpatrol.com/about/api/`*
