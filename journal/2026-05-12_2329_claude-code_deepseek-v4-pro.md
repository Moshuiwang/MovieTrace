# Agent 身份卡

- **工具：** Claude Code（VSCode 插件）
- **模型：** DeepSeek V4 Pro
- **会话时间：** 2026-05-12 16:50 +08 ~ 23:29 +08
- **起止 commit：** `4290624` → `bc39e24`
- **运行环境：** Python 3.12 + `.venv/` + Linux

---

# 今日工作主线

## 1. P1.5 全量任务包串行执行

按 B→E→C→D→F 顺序执行了 Phase 1.5 全部 5 个任务包：
- P1.5-B：Schema v6 migration（virtual_series 表 + 列新增）
- P1.5-E：A 库全量实体匹配（match_upstream_program + 脚本）
- P1.5-C：virtual_series 回填（两阶段去重优化）
- P1.5-D：基线主动追踪（poll_scheduler + baseline_tracking + CLI）
- P1.5-F：日报模板 + CLI 语义 + 导出（export_writer + 飞书清理）

测试 284 → 317（+33），全部通过。

## 2. Phase 1.6 首次真实运行 + 验收

### P1.5-E 生产匹配
- 594/594 匹配成功（high 587, medium 7, 零失败）
- 新建 canonical_items 513 条，耗时 15 分钟
- 发现并修复 35 条错误匹配

### P1.5-C 生产回填
- 最终 virtual_series: 307，TV 链接率 100%
- 两阶段去重：192 次 API（节省 185 次）
- 修复旧版 baseline_quality_issues 表冲突

### P1.5-D 基线追踪
- 检测到 8 个新季，写入 6 条 content_updates
- FROM S4, Silo S2, American Horror Story S11 等

## 3. 生产问题修复

### 问题 1：旧版 baseline_quality_issues 表 schema 冲突
- V1 遗留表列名不兼容 → `_ensure_quality_issues_table` 加自动检测重建

### 问题 2：多季同 tmdb_tv_id 的 external_id 丢失
- 同剧后续季的 tmdb external_id 被 `INSERT OR IGNORE` 丢弃
- P1.5-C 回填脚本预检过早跳过 → 去掉预检，走 fallback

### 问题 3：/search/tv 和 /search/movie 返回空
- 结果不含 `media_type` 字段，被 `parse_tmdb_search_results` 过滤
- 修复：加 `default_media_type` 参数

### 问题 4：A 库电影错标 S01
- 如 "Nyad S01"、"Sly S01" 被当 TV 搜索
- 修复：TV 搜索为空时回退 movie 搜索 + detail 端点验证

### 问题 5：匹配质量记录不全
- 只记录 low confidence，不记录 medium 和多候选接近
- 修复：扩展记录范围 + `_check_close_alternatives`

## 4. 审查修复
- 飞书文案清理（daily_writer.py 5 处）
- `feishu/recommendation_writer.py` + 测试删除
- `inspect-baseline` 数据源切到 upstream_programs
- `config.yaml` enabled 开关检查

---

# 关键决策记录

1. P1.5-C 放弃逐条调 API，改用两阶段先去重再调
2. 匹配改为类型专用搜索 + detail 验证，不再用 `/search/multi`
3. A 库 S01 后缀不可信，TV 搜索为空时回退 movie

---

# 数字总结

- **commit 数：** 5（61c4229, 92c201a, 96729a4, ff85bd2, bc39e24）
- **测试：** 284 → 317（+33）
- **新增模块：** 6（virtual_series, poll_scheduler, baseline_tracking, export_writer, migration 006, config.yaml）
- **新增脚本：** 2（p1.5_e_match_all, p1_5_c_backfill_virtual_series）
- **新增 CLI：** 2（baseline-track, export-recommendations）
- **删除文件：** 2（feishu/recommendation_writer.py, test_recommendation_writer.py）
- **生产数据：** canonical_items 903, virtual_series 307, content_updates 6
- **API 调用：** ~800+ 次 TMDb（匹配 634 + 回填 205）
- **耗时：** ~7 小时
