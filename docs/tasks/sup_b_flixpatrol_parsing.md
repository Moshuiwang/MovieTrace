# 任务包：SUP-B FlixPatrol HTML 解析稳定性测试

**任务包版本：** v1  
**创建日期：** 2026-05-10  
**预计完成：** 2026-05-11（1 天）

---

## 任务名称

SUP-B：FlixPatrol HTML 解析稳定性测试

## 任务类型

`verify` — 验证任务（含 draft 解析器实现）

## 当前阶段

Phase 0+（FlixPatrol 接入验证）

## 来源任务

- [docs/phase0_supplement.md](../phase0_supplement.md) § 任务 SUP-B
- [docs/next_steps_plan.md](../next_steps_plan.md) § Phase 0+ 补充验证
- SUP-A 已完成：6 个 HTML 样本就绪于 `tests/fixtures/flixpatrol/`

## 目标

**回答一个问题：** FlixPatrol 的 HTML 结构是否可以稳定解析？

具体来说：
1. 检查 6 个 HTML 样本的结构，找出 Top-10 数据的 HTML 定位方式
2. 实现解析器，提取：**title、rank、platform、region、content_type**（基础字段）
3. 尝试提取：**week_date、days_in_top10**（扩展字段，不强制，能提取则提取）
4. 跨 6 个页面验证解析逻辑稳定性（不同平台、不同地区）
5. 输出解析准确率统计（字段级别），给出"可解析 / 部分可解析 / 不可解析"结论

## 非目标

- ❌ **不**实现完整的 HTTP 抓取逻辑（那是 P1-B）
- ❌ **不**写入数据库（flixpatrol_charts 表在 P1-B 创建）
- ❌ **不**做实时网络请求（只解析 SUP-A 已保存的 HTML 样本）
- ❌ **不**做大规模测试（只用 6 个已有 HTML 样本）
- ❌ **不**实现缓存、重试、限速逻辑（那是 P1-B）
- ❌ **不**评估服务条款合规性（那是 SUP-D）

## 允许修改范围

**新增文件：**
- `src/movietrace/sources/flixpatrol.py` — draft 解析器（仅解析逻辑，无 HTTP）
- `tests/test_flixpatrol_parsing.py` — pytest 测试（基于 HTML 样本）
- `reports/flixpatrol_parsing_report.md` — 解析准确率报告（中文）
- `requirements.txt` — **新建**，记录项目依赖

**新增依赖（明确允许）：**
- `beautifulsoup4` — HTML 解析（任务包明确授权引入）
- 解析器后端：优先使用 Python stdlib `html.parser`（无需额外安装）；如需性能优化可加 `lxml`，但不强制

## 禁止修改范围

- 🚫 `src/movietrace/db/schema.py`（数据库改动在 P1-B）
- 🚫 `src/movietrace/sources/http.py`（不改现有 HTTP 工具）
- 🚫 `src/movietrace/pipeline/` 下任何文件
- 🚫 `data/movietrace.db`（不写入生产数据库）
- 🚫 `AGENTS.md`、`CLAUDE.md`
- 🚫 `tests/fixtures/flixpatrol/` 下已有 HTML 文件（只读）

## 相关上下文

**SUP-A 结论（已验证）：**
- 6/7 URL 返回 HTTP 200，HTML 服务端渲染，无反爬信号
- robots.txt 允许 `User-agent: *` 访问所有路径
- HTML 样本大小：69 KB – 261 KB

**HTML 样本清单：**

| 文件 | 平台 | 地区 | 大小 |
|------|------|------|------|
| `tests/fixtures/flixpatrol/netflix_global.html` | Netflix | 全球 | 227 KB |
| `tests/fixtures/flixpatrol/netflix_us.html` | Netflix | 美国 | 84 KB |
| `tests/fixtures/flixpatrol/amazon_prime_world.html` | Amazon Prime | 全球 | 202 KB |
| `tests/fixtures/flixpatrol/disney_world.html` | Disney+ | 全球 | 228 KB |
| `tests/fixtures/flixpatrol/apple_tv_world.html` | Apple TV+ | 全球 | 261 KB |
| `tests/fixtures/flixpatrol/hulu_us.html` | Hulu | 美国 | 69 KB |

## 目标字段定义

### 基础字段（必须达到 ≥ 95% 提取成功率）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `title` | str | 内容标题 | `"Squid Game"` |
| `rank` | int | 排名（1-10） | `1` |
| `platform` | str | 流媒体平台 | `"netflix"` |
| `region` | str | 地区 | `"global"` / `"us"` |
| `content_type` | str | 内容类型 | `"movie"` / `"show"` |

### 扩展字段（尽力提取，不作强制要求）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `week_date` | str | 榜单日期（如有） |
| `days_in_top10` | int | 在榜天数（如有） |

## 解析器设计要求

### R1: 解析器模块结构（`src/movietrace/sources/flixpatrol.py`）

```python
# 必须包含的公开函数（类型注解必须）
def parse_top10_page(html: str, platform: str, region: str) -> list[dict]:
    """从 HTML 字符串解析 Top-10 条目列表。
    
    返回格式：
    [
        {
            "rank": 1,
            "title": "...",
            "platform": "netflix",
            "region": "global",
            "content_type": "show",
            "week_date": "2026-05-10",  # 如有
            "days_in_top10": 14,         # 如有
        },
        ...
    ]
    """
```

### R2: 错误处理

1. 解析失败的字段返回 `None`，不抛异常
2. 整页解析失败时返回空列表 `[]`，记录错误日志（`logging` 模块）
3. 不能因为单条数据解析失败导致整个页面结果丢失

### R3: 代码质量

1. 公开函数必须有类型注解
2. 使用 `logging` 而非 `print` 记录解析错误
3. 避免硬编码 CSS 选择器字符串散落各处；集中定义为常量

### R4: 测试覆盖（`tests/test_flixpatrol_parsing.py`）

必须包含以下测试：
1. 对 6 个 HTML 样本各运行一次 `parse_top10_page()`，验证结果非空
2. 对 Netflix Global 样本，验证 rank=1 的条目存在且 title 非空
3. 验证所有基础字段的提取成功率 ≥ 95%（以条目总数为分母）
4. 验证跨平台解析结果的 platform 字段与输入参数一致

## 验收标准

### 必须达成（否则 NO-GO）

1. ✅ `pytest tests/test_flixpatrol_parsing.py -v` 全部通过
2. ✅ 6 个 HTML 样本均能运行 `parse_top10_page()` 无异常
3. ✅ 基础字段（title、rank、content_type）提取成功率 ≥ 95%
4. ✅ 报告生成，包含全部章节（见下方报告结构）
5. ✅ `requirements.txt` 已创建，包含 `beautifulsoup4`

### 期望达成

6. 至少 1 个扩展字段（week_date 或 days_in_top10）可提取
7. 跨 6 个页面解析逻辑一致（相同选择器）
8. 解析每个页面耗时 < 2 秒

### 不算失败但需记录

9. 扩展字段无法提取（HTML 中不存在） → 报告中说明
10. 部分平台页面结构略有差异 → 报告中说明差异，解析器处理或标注

## 报告结构（`reports/flixpatrol_parsing_report.md`，中文）

```markdown
## 1. 验证摘要
- 测试样本数、成功解析数、总条目数
- 初步结论：✅ 可解析 / ⚠️ 部分可解析 / ❌ 不可解析

## 2. HTML 结构分析
- Top-10 数据在 HTML 中的位置（CSS 选择器路径）
- 各平台页面结构一致性

## 3. 字段提取结果
- 基础字段提取成功率（表格）
- 扩展字段提取情况

## 4. 跨平台一致性
- 6 个样本的解析结果对比
- 平台间结构差异说明

## 5. 解析失败分析
- 哪些字段提取失败、原因

## 6. 给 P1-B 的输入
- 解析器可直接复用的代码路径
- P1-B 需要额外处理的边界情况

## 7. 决策建议
- 是否进入 P1-B（完整 FlixPatrol 客户端实现）
```

## 测试要求

```bash
# 安装依赖
pip install beautifulsoup4
pip freeze > requirements.txt

# 运行解析测试
python -m pytest tests/test_flixpatrol_parsing.py -v

# 验证解析准确率（可选，脚本化输出）
python3 -c "
from movietrace.sources.flixpatrol import parse_top10_page
import pathlib
html = pathlib.Path('tests/fixtures/flixpatrol/netflix_global.html').read_text()
results = parse_top10_page(html, 'netflix', 'global')
print(f'条目数: {len(results)}')
print(f'rank=1: {next((r for r in results if r[\"rank\"]==1), None)}')
"
```

## 验证命令

```bash
# 1. 安装依赖并验证
pip install beautifulsoup4 && python3 -c "import bs4; print('bs4 OK:', bs4.__version__)"

# 2. 运行 pytest
python -m pytest tests/test_flixpatrol_parsing.py -v

# 3. 快速冒烟：解析 Netflix Global
python3 -c "
from movietrace.sources.flixpatrol import parse_top10_page
import pathlib
html = pathlib.Path('tests/fixtures/flixpatrol/netflix_global.html').read_text()
items = parse_top10_page(html, 'netflix', 'global')
print(f'解析条目数: {len(items)}')
for item in items[:3]:
    print(item)
"

# 4. 检查报告
cat reports/flixpatrol_parsing_report.md
```

## 风险点

### 已识别风险

1. **页面结构不稳定**
   - 概率：中（FlixPatrol 会更新前端）
   - 影响：现有 HTML 样本可解析，但实时抓取时结构可能变化
   - 缓解：CSS 选择器集中定义，P1-B 加入结构变化检测

2. **部分平台页面结构不同**
   - 概率：中（SUP-A 发现 Amazon Prime 和 Disney+ 有重定向）
   - 影响：同一解析器可能需要条件分支
   - 缓解：用 6 个样本覆盖验证，报告中说明差异

3. **扩展字段不可用**
   - 概率：中（week_date 和 days_in_top10 可能在 JS 渲染后才出现）
   - 影响：P1-B 候选评分中无时效性信号
   - 缓解：报告中明确说明，V1 可先不用时效字段

4. **BeautifulSoup 引入依赖冲突**
   - 概率：低（beautifulsoup4 无重依赖）
   - 影响：.venv 兼容性问题
   - 缓解：pip install 后立即验证

### 未识别风险

任务执行中发现新风险，必须记录到报告 §5，不要默默处理。

## 完成后输出要求

```
任务理解：
- 验证 FlixPatrol HTML 是否可稳定解析，输出 draft 解析器和准确率统计

完成内容：
- 创建 src/movietrace/sources/flixpatrol.py（draft 解析器）
- 创建 tests/test_flixpatrol_parsing.py（N 个测试用例）
- 创建 requirements.txt
- 生成 reports/flixpatrol_parsing_report.md

验证结果：
- pytest: N passed / M failed
- 基础字段提取成功率: X%
- 扩展字段: [可提取 / 不可提取]

剩余风险：
- [列出]

后续建议：
- 进入 P1-B / 调整解析器后重验 / 终止 FlixPatrol 接入
```

---

**任务包状态：** ✅ 就绪，等待执行  
**预计执行时间：** 1 天（含报告撰写）  
**依赖：** SUP-A 已完成 ✅  
**下一任务：** SUP-C（匹配率，0.5 天）+ SUP-D（合规，0.5 天，可并行）
