# A 库（上游生产 DB）表结构参考

> 数据来源：`source_records/节目数据.csv` + `source_records/子节目数据.csv`
> 导入表：`upstream_programs` (735 行) · `upstream_episodes` (6,562 行)
> 生成时间：2026-05-12 +08

---

## 背景

### A 库是什么

A 库是 MovieTrace 项目依赖的**上游生产环境数据库**，存储一个面向非洲市场的流媒体平台的节目与视频元数据。该平台的内容版权覆盖 40+ 个非洲国家，节目以英语为主。

本报告基于用户从该生产 DB 直接导出的两份 CSV 文件（2026-05-12），导入到本项目 SQLite 中作为**本地静态快照**，用于开发验证和 schema 理解。后续将通过 API 方式实现生产 DB → MovieTrace 的增量同步。

### MovieTrace 项目是什么

MovieTrace 自动发现英语影视在多个流媒体平台（Netflix / Prime Video / Disney+ / Apple TV+ / HBO Max / Hulu）的热度变化，标记是否在 A 库（飞书基线）中，生成可审核的推荐清单。

核心流程：**A 库内容 → TMDb 匹配 → FlixPatrol 热度追踪 → 推荐输出**。

### A 库数据对 MovieTrace 的意义

A 库是 MovieTrace 的**输入源和判断基准**：

1. **内容目录** — A 库的节目/子节目定义了"我们有什么内容"，是所有追踪的起点
2. **TMDb 匹配的输入** — 用 `name` 去 TMDb 搜索，建立 A 库内容 ↔ TMDb ID 的映射
3. **增量变更检测** — 通过 `modify_instant` 判断哪些节目/集发生了变更，驱动后续重新匹配和追踪
4. **内容过滤** — 通过 `online_flag` 过滤已下架内容，只追踪当前有效的节目

### 当前情况

- **数据形态**：生产 DB 导出的 CSV 静态快照，已导入 `data/movietrace.db` 的 `upstream_programs` / `upstream_episodes` 两张表
- **同步方式**：当前为一次性导入验证；后续规划通过 API 做增量同步
- **数据质量**：`imdb_id` 全空（匹配只能走名称搜索）、`program_status` 不区分电影/剧集、`delete_flag` 无意义
- **关键缺口**：上游没有 Series 实体，剧集每季是独立记录（如 Better Call Saul S01~S06 是 6 条），需要 MovieTrace 自行构建 `virtual_series` 聚合（P1.5-C）

---

## upstream_programs（节目表 · 735 行）

| 字段 | 含义 | 关键事实 | 对本项目的意义 |
|------|------|----------|----------------|
| `id` | 主键，上游节目 ID | 整数，唯一标识一个"节目"（实际粒度 = 季级） | 🔴 external_id，匹配 canonical_item |
| `name` | 节目名称 | 如 "Better Call Saul S01"、"Avatar The Way of Water" | 🔴 TMDb 搜索输入 + 季号提取源 |
| `online_flag` | 上架状态 | `1`=已上架(597) / `0`=已下架(137) / `2`=其他(1) | 🔴 过滤条件，只追踪已上架内容 |
| `modify_instant` | 修改时间 | 100% 有值 | 🔴 增量更新的核心：比对前后值判断节目是否有变更 |
| `code` | 业务编码 | UUID 格式，唯一 | 🟡 备选 external_id |
| `make_year` | 制作年份区间 | 仅 89 条有值，如 "2021-2025" | 🟡 TMDb 搜索时可辅助年份过滤（覆盖率 12%） |
| `multi_language_names` | 多语言标题 | 如 `287:Better Call Saul S01` | 🟡 剥离前缀后可作为英文标题 |
| `multi_language_summaries` | 多语言摘要 | 同 names | 🟡 同上 |
| `multi_language_bright_spots` | 多语言亮点 | 同 names | 🟡 同上 |
| `multi_language_json` | 多语言完整 JSON | `[{id, languageId, name, summary, brightSpot, updateInfo}]` | 🟡 结构化英文标题来源 |
| `modify_id` | 修改人 ID | 598 条为 `1`，其余空 | 🟡 辅助判断是否人工操作 |
| `program_status` | 节目类型标记 | `MOVIE`(734) / `TV_PLAY`(1) | ⚪ 原始数据质量差，不区分电影/剧集，暂不可用 |
| `delete_flag` | 删除/有效标记 | 全为 `1` | ⚪ 无意义，可忽略 |
| `imdb_id` | IMDb ID | 全空 | ⚪ 暂不适用，待上游后续补填 |
| `first_publish_time` | 首次发布时间 | 599 条有值 | ⚪ 暂无用途 |
| `create_instant` | 创建时间 | 100% 有值 | ⚪ 暂无用途 |
| `make_by_star` | 是否明星内容 | 全为 `0` | ⚪ 暂无用途 |
| `program_number` | 节目序号 | 仅 88 条有值 | ⚪ 暂无用途 |
| `episodes` | 集数 | 全空 | ⚪ 暂无用途 |
| `poster_type` | 海报类型 | `0`(732) | ⚪ 暂无用途 |
| `country_count` | 可用国家数 | 仅 1 条有值 | ⚪ 暂无用途 |
| `country_codes` | 可用国家列表 | ISO 3166-1 alpha-2，主要为非洲区 | ⚪ 暂无用途 |
| `country_code_property_types` | 各国版权属性 | 如 `-O:0 \| AO:0 \| ...` | ⚪ 暂无用途 |
| `multi_language_count` | 多语言数量 | `1` 或 `0` | ⚪ 暂无用途 |
| `multi_language_ids` | 多语言记录 ID | 整数 | ⚪ 暂无用途 |
| `language_ids` | 语言编码 | 全为 `287` | ⚪ 暂无用途 |
| `multi_language_update_infos` | 多语言更新说明 | 全是 `287:`（空内容） | ⚪ 暂无用途 |
| `encryption_type` | 加密类型 | 全为 `0`（无 DRM） | ⚪ 暂无用途 |
| `tenant_id` | 租户 ID | 全为 `-1`（单租户） | ⚪ 暂无用途 |
| `update_status` | 更新状态 | `0` 或 `1` | ⚪ 暂无用途 |
| `fk_publisher_id` | 发行商 ID | 全空 | ⚪ 暂无用途 |
| `download_right` | 下载权限 | 全为 `1` | ⚪ 暂无用途 |
| `download_right_info` | 下载权限详情 | 全空 | ⚪ 暂无用途 |
| `status_explanation` | 状态说明 | 全空 | ⚪ 暂无用途 |
| `turn_on_watermark` | 开启水印 | 全为 `0` | ⚪ 暂无用途 |
| `watermark_location` | 水印位置 | 全空 | ⚪ 暂无用途 |
| `metadata_modify_flag` | 元数据修改标记 | `0` 或 `1` | ⚪ 暂无用途 |
| `create_id` | 创建人 ID | 全空 | ⚪ 暂无用途 |

---

## upstream_episodes（子节目表 · 6,562 行）

| 字段 | 含义 | 关键事实 | 对本项目的意义 |
|------|------|----------|----------------|
| `id` | 主键，子节目 ID | 整数，一条子节目 = 一个视频文件 | 🔴 external_id 来源 |
| `name` | 子节目名称 | 多为 scene release 文件名，如 "FSLS S01E02" | 🔴 正则提取 S/E 编号，对应 TMDb episode 编号 |
| `fk_program_content_id` | → 关联父节目 ID | 100% 填充，指向 `upstream_programs.id` | 🔴 Episode → Program(Season) 关联 |
| `direct_weight` | 排序权重 | 5,480 条有值 (83.5%) | 🔴 集序判断 + 新集检测（权重最大值变大 → 有新集） |
| `modify_instant` | 修改时间 | 100% 有值 | 🔴 增量更新的核心：比对前后值判断某集是否有变更 |
| `code` | 业务编码 | UUID 格式 | 🟡 备选 external_id |
| `pc_id` | 冗余：父节目 ID | 与 fk_program_content_id 对应，1 条为空 | 🟡 省 JOIN |
| `pc_name` | 冗余：父节目名称 | 如 "Better Call Saul S01" | 🟡 省 JOIN |
| `pc_code` | 冗余：父节目 code | UUID | 🟡 冗余字段 |
| `duration_hour` | 时长 — 小时 | 100% 有值 | 🟡 判断是否完整正片（非预告片/花絮） |
| `duration_minute` | 时长 — 分钟 | 100% 有值 | 🟡 同上 |
| `duration_second` | 时长 — 秒 | 100% 有值 | 🟡 同上 |
| `modify_id` | 修改人 ID | 5,602 条有值 | 🟡 辅助判断是否人工操作 |
| `episode` | 集号 | 仅 8 条有值 | ⚪ 暂无用途（覆盖率太低） |
| `paragraph` | 段落/分段 | 仅 9 条有值 | ⚪ 暂无用途 |
| `pc_program_status` | 冗余：父节目状态 | `MOVIE`(6536) / `TV_PLAY`(25) | ⚪ 原始数据质量差，同 program_status |
| `pc_imdb_id` | 冗余：父节目 IMDb ID | 全空 | ⚪ 暂不适用，待上游后续补填 |
| `fk_video_ondemand_id` | → 关联点播视频 ID | 100% 填充 | ⚪ 暂无用途 |
| `pc_type` | 冗余：父节目类型 | 全为 `1` | ⚪ 暂无用途 |
| `video_status` | 视频转码状态 | 全为 `2`（就绪） | ⚪ 暂无用途 |
| `source_type` | 来源类型 | 全为 `0`（默认） | ⚪ 暂无用途 |
| `country_code_available` | 各国可用性 | 如 `-O:1 \| AO:1 \| ...` | ⚪ 暂无用途 |
| `dot_status` | 打点状态 | 全为 `0` | ⚪ 暂无用途 |
| `prologue_time` | 片头时长 | 全空 | ⚪ 暂无用途 |
| `epilogue_time` | 片尾时长 | 全空 | ⚪ 暂无用途 |
| `support_download` | 允许下载 | 全空 | ⚪ 暂无用途 |
| `support_download_remarks` | 下载备注 | 全空 | ⚪ 暂无用途 |
| `import_video_name` | 导入视频名 | 全空 | ⚪ 暂无用途 |
| `original_publisher` | 原始发行方 | 全空 | ⚪ 暂无用途 |
| `original_source` | 原始来源 | 全空 | ⚪ 暂无用途 |
| `effective_time` | 生效时间 | 全空 | ⚪ 暂无用途 |
| `create_instant` | 创建时间 | 100% 有值 | ⚪ 暂无用途 |
| `create_id` | 创建人 ID | 全空 | ⚪ 暂无用途 |

---

## 数据关系

```
upstream_programs (1)  ←→  (N) upstream_episodes
       id           ←  fk_program_content_id
```

- 734 个去重父节目，平均每节目 8.9 条子节目
- 1 条孤儿子节目（fk=3841，父节目不在表中）
- 2 条孤独节目（无子节目：Old Dads、Concrete Utopia）

---

## 对 MovieTrace 的核心依赖字段汇总

| 优先级 | 字段 | 用途 |
|--------|------|------|
| 🔴 必不可少 | `upstream_programs.id` | canonical_item 的 external_id |
| 🔴 必不可少 | `upstream_programs.name` | TMDb 搜索 + 季号提取 |
| 🔴 必不可少 | `upstream_programs.online_flag` | 过滤已下架内容 |
| 🔴 必不可少 | `upstream_programs.modify_instant` | 增量更新检测 |
| 🔴 必不可少 | `upstream_episodes.name` | 正则提取 S/E 编号，对应 TMDb episode 编号 |
| 🔴 必不可少 | `upstream_episodes.fk_program_content_id` | Episode → Program 关联 |
| 🔴 必不可少 | `upstream_episodes.direct_weight` | 集序 + 新集检测 |
| 🔴 必不可少 | `upstream_episodes.modify_instant` | 增量更新检测 |
| 🟡 高价值辅助 | `upstream_episodes.duration_*` | 正片/花絮过滤 |
| 🟡 高价值辅助 | `upstream_episodes.pc_name` | 省 JOIN 的父节目名 |
| ⏳ 待补填 | `imdb_id` | 全空，待上游后续补填；补填后可走 ID 直连匹配 |
