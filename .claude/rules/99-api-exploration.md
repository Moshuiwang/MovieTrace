# API 探索铁律（防盲目猜测）

> 外部 API（Feishu / TMDb / Trakt / OMDb / FlixPatrol）接入时的快速反馈循环规范。
> 防止"5 个路径猜测"式的弯路重现。

## 第 0 步：需求澄清 — 动代码前必做

任何 API 接入任务，编码前必填清单：

- [ ] 目标 API 是什么？（如"知识库导入"vs"云空间导入"，而非笼统的"wiki"）
- [ ] 官方文档在哪？（URL + 已读确认）
- [ ] 认证方式是什么？（Bearer / tenant_access_token / user_access_token / API Key）
- [ ] 上限与配额是什么？（速率限制、请求配额、并发限制）
- [ ] 必选参数与可选参数分别是什么？

如任一项答不清楚，**停下澄清**，不继续动代码。

---

## 第 1 步：文档 → 手工测试 → 代码（紧凑单环）

### 1.1 文档阶段

```
查官方 API 文档，记录：
- endpoint 完整 URL（包含 base + path）
- HTTP 方法（GET / POST / PUT）
- 必选参数（body / query / header）
- 期望状态码（通常 200 / 201）
- 响应格式（JSON field 名称）
```

### 1.2 手工测试阶段（代码前）

```bash
# 用 curl / gh api / Postman 做一次真实测试
# 目的：验证文档是否准确、权限是否足够、参数是否正确

curl -X POST https://open.feishu.cn/open-apis/... \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"param": "value"}'

# 记录响应（脱敏 token）
```

**关键约束**：
- 此阶段 **不编代码**，仅用 shell / HTTP 工具
- 成功后才进入代码实现
- 失败时对标"第 2 步"的诊断流程

### 1.3 代码阶段

```python
# 仅在手工测试成功后，才将测试命令改写为代码
# 保持与手工测试的对应性
```

### 1.4 验证阶段（立即运行）

```bash
# 代码写完，立即运行单个验证命令
# 不要积累"N 个 git commit 再测一次"

PYTHONPATH=src python -m pytest tests/test_feishu_api.py::test_wiki_import -v
```

---

## 第 2 步：遇到错误时的 3 阶段诊断

### 阶段 A：错误信号分类（<30 秒）

| 状态码 范围 | 含义 | 初步判断 |
|---|---|---|
| 4xx | 客户端错（格式/权限/参数） | 我方问题，查文档 |
| 5xx | 服务器错 | 服务方问题，等待或查服务状态页 |
| timeout / 网络 | 连接问题 | 检查 URL、代理、网络状态 |
| 本地异常（Exception） | 代码问题 | 堆栈 trace → 定位 |

### 阶段 B：对应查证动作（<5 分钟）

| 错误特征 | 查证动作 | 关键文档 |
|---|---|---|
| 401 Unauthorized | 检查 token 是否过期、是否正确传递 header | 官方 auth 文档 |
| 403 Forbidden | 检查应用权限范围（scope）、是否需要用户授权 | 官方 scope 文档 + 飞书后台申请日志 |
| 400 Bad Request / 422 | 检查必选参数、body 格式、field 类型 | 官方 API 参数表 |
| 404 Not Found | **立即停下查文档**——不要猜第二个路径 | 官方 endpoint 列表 |
| 409 Conflict / 5xx | 检查是否重复请求、是否服务故障 | 官方状态页 + 重试策略 |

### 阶段 C：信息收集清单（问题复现前必做）

记录以下三项后，才可尝试修改：

```
现象：
- HTTP 状态码：[code]
- 响应体（脱敏）：[response]
- 时间戳与 request ID：[如有]

已排除：
- token 是否有效？[是/否]
- endpoint URL 是否正确？[是/否]
- 必选参数是否齐全？[是/否]

下一步定位：
- 需要查哪个文档章节？
- 需要申请哪个权限吗？
- 需要用户确认哪个信息吗？
```

---

## 第 3 步：禁止的 5 个动作

### ❌ 禁止 1：在 404 时猜测第二个路径

```python
# 错：404 响应后，直接尝试另一个路径
def import_to_wiki(self):
    try:
        resp = requests.post('/wiki/v2/spaces/{}/docs/import_docx')  # 404
    except:
        resp = requests.post('/wiki/v2/{}/pages/import_docx')        # 盲目猜测
        
# 正：404 时停下，查官方文档
def import_to_wiki(self):
    # 查飞书文档：发现 drive/v1/import_task 是唯一入口
    resp = requests.post('/drive/v1/import_task', ...)
```

**触发信号**：错误代码为 4xx 且与"路径不存在"相关 → 立即暂停编码，打开官方 API 文档。

### ❌ 禁止 2：改 UA / Token 来"绕过" 400

```python
# 错：改 User-Agent 试图绕过限制
headers = {"User-Agent": "Mozilla/5.0"}  # 伪造浏览器 UA

# 正：检查参数格式、查看官方文档参数表
headers = {"Authorization": f"Bearer {valid_token}"}
# 同时查：是否少了某个必选参数？是否参数类型错了？
```

**触发信号**：想改 UA / Secret / Token 来"骗过" 400 → 反而意味着需要查参数表。

### ❌ 禁止 3：错误时静默重试

```python
# 错：循环重试但不记录
for attempt in range(3):
    try:
        resp = requests.post(...)
        return resp
    except:
        pass  # 无日志，下次调试时无线索

# 正：记录 + 选择性重试（指数退避，3 次为限）
import time, logging
for attempt in range(3):
    try:
        resp = requests.post(...)
        return resp
    except Exception as e:
        logging.error(f"Attempt {attempt+1}/3 failed: {e}")
        if attempt < 2:
            time.sleep(2 ** attempt)
        else:
            raise
```

**规则来源**：CLAUDE.md 第 3 条铁律（不掩盖失败）。

### ❌ 禁止 4：跳过文档就开始写 SDK

```python
# 错：假设 API 结构，直接写 helper
class FeishuWikiAPI:
    def import_doc(self, space_id, file_path):
        # 后来才发现参数名错了、endpoint 不存在
        pass

# 正：先读完文档、走过手工测试，再抽象 helper
# 文档确认：endpoint 是 /drive/v1/import_task
# 参数确认：space_id / mount_point_token / file_type
# 然后再写 helper，保证参数映射正确
```

**规则来源**：`.claude/rules/00-core-behaviors.md` Critique-First 规则。

### ❌ 禁止 5：一次改多个参数

```python
# 错：同时改 endpoint + header + body，无法定位原因
def test():
    resp = requests.post(
        '/wiki/v2/spaces/123/docs/import',  # 改了这个
        headers={'Auth': new_token},         # 改了这个
        json={'file_id': 'xxx', 'type': 'pdf'}  # 改了这个
    )

# 正：改一个、测一个、再改下一个
def test():
    # 第一轮：验证 endpoint
    resp = requests.post('/drive/v1/import_task', ...)
    print(f"Status: {resp.status_code}")
    
    # 第二轮：验证 header（仅改这一个）
    # 第三轮：验证 body（仅改这一个）
```

**规则来源**：科学方法（单变量控制）。

---

## 现实案例：wiki 导入弯路

### ❌ 违反情况

| 决策点 | 应该执行的规则 | 实际行为 | 后果 |
|---|---|---|---|
| 用户说"放到 wiki" | 第 0 步：需求澄清 | 未澄清"wiki"= 飞书知识库 API 还是云空间文件夹 | 错误假设导入 API 形式 |
| 第一个 404 | 第 2 步B：404 时查文档 | 尝试第二个路径（/wiki/v2/spaces/...) | 进入猜测循环 |
| 连续 5 次 404 | 第 3 步禁止 1 | 仍在改路径（猜测） | 浪费 4 次 try-catch |
| mount_no_permission | 第 2 步C：信息收集 | 未查官方文档确认 mount_type 支持的值 | 错误诊断：以为是权限，实际是 API 设计 |

### ✅ 正确流程（如果遵守）

```
第 0 步：用户说"放到 wiki"
→ 澄清：飞书知识库 API 是什么？
→ 用户：应该用知识库 API 导入
→ 查飞书官方文档：https://open.feishu.cn/document/...
→ 发现：驱动型导入用 /drive/v1/import_task，mount_type 只支持 1

第 1 步：手工测试
→ curl -X POST /drive/v1/import_task \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@report.md" \
    -F "mount_type=1" \
    -F "mount_point_token=$FOLDER_TOKEN"
→ 响应：成功 200 / 权限错 403

第 2 步：诊断（仅需一轮，而非五轮）
→ 403 → 查权限
→ 确认应用权限已授予
→ 手工测试再次成功
→ 进入代码阶段

总耗时：澄清 5min + 查文档 10min + 手工测试 5min = 20min
实际耗时：盲目猜测 5 个路径 = 60+ min
```

---

## 检查清单（任务前）

API 接入任务开工前，扫过这个清单：

- [ ] 官方文档链接已加入任务包吗？
- [ ] 已手工测试一次吗？（curl / Postman）
- [ ] 认证方式确认无误吗？
- [ ] 能复现第一个成功的 200 响应吗？
- [ ] 失败时的诊断流程明确吗？（不是"再试一次"）
- [ ] 代码中的 endpoint 与文档对应吗？（copy-paste 检查）

任一项答"否" → 不开工。

---

## 相关规则交叉引用

- **Critique-First 清单**：[`.claude/rules/00-core-behaviors.md`](00-core-behaviors.md) § 第 2-5 题
- **失败处置**：[`.claude/rules/10-validation.md`](10-validation.md)
- **Feishu 合规**：[`.claude/rules/23-feishu-integration.md`](23-feishu-integration.md)
- **外部源合规**：[`.claude/rules/22-sources-compliance.md`](22-sources-compliance.md)

---

**生效日期**：2026-05-17（wiki 导入完整性分析后）
