# MovieTrace 本地数据库架构

状态：v0.1  
日期：2026-05-09  
适用阶段：Phase 0 验证包、后续 MVP 原型

## 1. 架构调整结论

MovieTrace 后续应以本地数据库作为系统事实源，飞书多维表格不再承担长期主数据管理职责。

调整后的定位：

| 组件 | 新定位 |
| --- | --- |
| SQLite 本地数据库 | 系统事实源，保存基线、实体、外部 ID、候选、匹配结果、缓存和运行记录 |
| 飞书 `节目` 表 | 输入来源之一，用于导入当前库已有内容 |
| 飞书测试表 | API 权限和写入验证 |
| 飞书 schema 表 | 字段定义和人工对齐资料 |
| 后续飞书推荐表 | 可选协作视图，不作为唯一状态源 |

这个调整的原因是飞书多维表格适合人工查看和少量协作，但不适合作为高频读写、缓存、去重和多数据源匹配的核心数据库。

## 2. 数据流

```text
飞书节目表 / 完整节目库导出
-> baseline_items
-> TMDb / Trakt 匹配
-> canonical_items + external_ids + match_candidates
-> source_records + api_cache
-> content_updates
-> 可选同步到飞书推荐视图
```

## 3. 初始 SQLite 表

| 表 | 用途 |
| --- | --- |
| `schema_migrations` | 记录数据库 schema 版本 |
| `feishu_import_runs` | 记录从飞书读取基线的每次导入 |
| `source_records` | 保存原始来源记录和原始响应引用 |
| `canonical_items` | 统一影视实体，覆盖 movie / series / season / episode |
| `external_ids` | 保存 TMDb / IMDb / Trakt 等外部 ID |
| `baseline_items` | 保存当前库已有内容基线 |
| `content_updates` | 保存待推荐或待处理的内容更新 |
| `match_candidates` | 保存实体匹配候选和置信度 |
| `api_cache` | 缓存外部 API 响应，降低重复请求 |

## 4. Phase 0 建库边界

本阶段只建立数据库 schema 和验证初始化能力。

包含：

- 创建 SQLite 数据库。
- 创建核心表和索引。
- 提供可测试的初始化函数。
- 提供示例配置。

不包含：

- 不导入全量节目表。
- 不实现完整 Feishu -> SQLite 同步。
- 不实现 TMDb / Trakt 全量匹配入库。
- 不实现飞书推荐表同步。
- 不做数据库迁移框架，只记录初始 schema 版本。

## 5. 验收方式

验证命令：

```bash
python3 -m unittest discover -s tests
```

验收标准：

- 测试能创建临时 SQLite 数据库。
- 数据库包含核心表。
- 关键唯一索引存在。
- 连接启用 foreign keys。

