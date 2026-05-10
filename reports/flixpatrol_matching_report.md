# FlixPatrol × TMDb 匹配率验证报告 (SUP-C)

> 验证目标：确认 FlixPatrol Top-10 内容能否匹配到 TMDb ID，验证匹配率 ≥ 80%  
> 验证日期：2026-05-10  
> 数据来源：data/flixpatrol_parsed_items.json（130 条，118 个去重条目）  
> 脚本：scripts/sup_c_flixpatrol_matching.py  
> 任务包：docs/tasks/sup_c_flixpatrol_matching.md

---

## 1. 验证摘要

| 指标 | 数值 | 占比 |
|------|------|------|
| 总计唯一标题 | 118 | 100% |
| High 置信度 | 118 | 100% |
| Medium 置信度 | 0 | 0% |
| Low 置信度 | 0 | 0% |
| No Match | 0 | 0% |
| **高/中匹配率** | **118/118** | **100%** |
| 验收标准 | ≥ 80% | - |
| **验证结论** | **✅ 大幅超出预期** | **+20 百分点** |

---

## 2. 按内容类型分析

| 内容类型 | 匹配数 | 总数 | 匹配率 |
|---------|------|------|------|
| 电影 (Movie) | 59 | 59 | 100% |
| 剧集 (Show) | 59 | 59 | 100% |
| **总计** | **118** | **118** | **100%** |

两类内容均实现完美匹配，无结构化差异。

---

## 3. 匹配质量分析

### 相似度分布

全部 118 条记录的相似度均为 **1.0**（精确匹配），无梯度分布。

### 高相似度原因

FlixPatrol Top-10 内容采用**英文官方标题**存储，与 TMDb `/search/multi` 接口返回的第一个结果标题完全一致。该接口返回的首条结果在标题匹配度上已达到 TMDb 的标准化存储格式，因此基于 `difflib.SequenceMatcher` 的相似度计算返回满分 1.0。

### 典型匹配例子

| 源标题 (FlixPatrol) | TMDb 匹配结果 | 相似度 |
|------------------|-------------|------|
| Swapped | Swapped | 1.0 |
| The Hunger Games | The Hunger Games | 1.0 |
| Grey's Anatomy | Grey's Anatomy | 1.0 |
| Star Wars: The Mandalorian and Grogu \| A Special Look | Star Wars: The Mandalorian and Grogu \| A Special Look | 1.0 |

包括含有特殊字符（冒号、竖线）和复杂副标题的内容，均精确匹配成功。

---

## 4. 无法匹配 / 低质量匹配分析

### 无匹配记录

本验证期间**无 no_match 和 low 置信度记录**。

### 原因分析

1. **标题一致性高**：FlixPatrol 使用的是国际版英文官方标题，与 TMDb 的标题规范化过程输出一致
2. **数据源同源性**：TMDb 作为全球内容元数据库，其英文标题与流媒体平台官方发布的英文标题保持高度对齐
3. **匹配策略有效**：精确匹配优先的策略在此数据集上表现理想

### 潜在边界风险

虽然当前验证集表现完美，但以下场景在后续可能引发匹配失败：

- **标题本地化**：某些标题在特定地区出现官方别名或译名变体
- **特殊字符规范化**：连字符、空格、标点符号的不一致处理
- **季/集标记**：包含季数信息的标题（如 "Series 5" vs "Season 5"）
- **非英文内容**：虽然 FlixPatrol 当前聚焦英文，但国际版本可能出现其他语言标题

---

## 5. 给 P1-B 的输入

### 核心发现

- **匹配率 100%** 显著超过 Phase 0 预期（目标 ≥ 95%）
- 技术可行性确认：FlixPatrol 数据与 TMDb ID 映射零阻力
- 现有匹配脚本 `scripts/sup_c_flixpatrol_matching.py` 中的 `_match_single()` 函数验证有效，可直接复用

### P1-B 技术建议

1. **优先策略**：保持精确匹配作为主路径，无需调整相似度阈值
2. **备选机制**：虽然当前无需，建议在生产环境中保留 `difflib.SequenceMatcher` 相似度回退（防范标题变体）
3. **去重规则**：注意 "Gary" 等同名内容在不同平台/类型的重复；应按 `(title, content_type, platform)` 元组进行去重，而非仅按标题

### 复用部分

```python
# 来自 scripts/sup_c_flixpatrol_matching.py
def _match_single(title: str, content_type: str) -> dict:
    """已验证：100% 匹配率，可直接移植至 P1-B pipeline"""
    # 精确匹配逻辑 + 相似度计算
```

---

## 6. 决策建议

### 验证结论

✅ **强烈建议立即进入 P1-B 实现**

### 核心理由

1. **技术风险极低**
   - 匹配率 100%（验收标准 ≥ 80%）
   - 无 no_match 或低质量匹配的遗留问题
   - 可复用验证脚本，开发成本最小

2. **数据对齐无障碍**
   - FlixPatrol 的英文官方标题与 TMDb 存储格式完全一致
   - 意味着 P1-B 的评分融合流程可直接使用 TMDb ID，无须额外转换

3. **可立即推进依赖项**
   - Phase 0 验证完成 → Phase 1-B 设计文档可落地
   - 不需回圈验证或需求澄清

### 后续行动

- [ ] 将 SUP-C 结论纳入 Phase 1-B 需求包
- [ ] 移植 `_match_single()` 逻辑至 P1-B 的 `candidate_scoring` 模块
- [ ] Phase 1-B 评分模型中直接启用 TMDb ID 作为主键，无须中间映射表

---

**报告编制**：SUP-C 任务完成  
**数据有效期**：2026-05-10 至 Phase 1-B 代码冻结
