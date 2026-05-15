# 工作日报 — 2026-05-15/16

## Agent 身份卡

| 项 | 值 |
|---|---|
| 工具 | Claude Code CLI |
| 模型 | deepseek-v4-flash |
| 运行环境 | Linux (Ubuntu) · bash shell |
| 起始 commit | `d2352ae` |
| 结束 commit | （待提交） |
| 会话时间 | 2026-05-15 23:30 +08 ~ 2026-05-16 01:15 +08 |
| Token | 未记录（对话未结束） |

## 今日工作主线

### 飞书新 App 迁移 + 多维表格重建

**触发**：用户提供新飞书 App 凭据，需要替换旧的 `cli_a9570907deb95cca` → `cli_aa8d80407af89bdf`，并重建运营用多维表格。

**过程**：

1. **凭据切换**（23:30-23:50）：
   - `~/.config/movietrace/secrets.json`：app_id / app_secret / notify_user_open_id 换新值，旧值 `_deprecated` 保留
   - `~/.lark-cli/config.json`：主 app 从 `cli_a97e85e564f89bd5` 切为 `cli_aa8d80407af89bdf`
   - 发送测试消息失败 — `open_id cross app` 报错：lark-cli 用的旧 app 身份发不到新 app 的 open_id
   - 更新 lark-cli config 后修复

2. **多维表格创建**（23:50-00:20）：
   - API 创建新 Bitable base `P6y3bMbAXazlL5sui4Mc6B5znMb`（MovieTrace 数据中心）
   - 创建 "每日发现" 表，18 个字段
   - 从本地 DB 取 10 条真实数据写入

3. **表结构迭代优化**（00:00-00:55，共 5 轮重建）：
   - 删除默认无用字段（文本/单选/日期/附件）
   - 主键列从"发现日期"改为"标题"
   - 删除"剧集名"（与标题重复）
   - "是否低置信度" checkbox → select（是/否）
   - 发现日期 → date 类型；检测时间/同步时间 → date（yyyy/MM/dd HH:mm）
   - 负责人 → user 人员字段
   - 类型/更新类型/优先级/运营状态/供应商状态 → select + 选项
   - 授予用户 `full_access` 管理权限（`/drive/v1/permissions`）
   - 发现 API 限制：`description` 参数不支持；`date_formatter` 用 `date_formatter` 非 `formatter`

4. **代码重构：名称 → field_id**（00:55-01:10）：
   - `sync.py`：删除表/字段自建逻辑（`_find_or_create_table`、`_ensure_fields` 等），引入 `F` 字典按 `field_id` 定位所有字段
   - `cli.py`：移除 `--table-name` 参数，直接读 `secrets.json` 的 `discovery_table_id`
   - Dry-run 验证通过（80 条记录），全量 451 tests passed

## 关键决策记录

1. **field_id 取代 field_name 定位**：表改名不影响同步代码，字段改名也不影响。重建表需同步更新 `F` 字典（18 行）。
2. **API 创建优于 UI 创建**：每次迭代重建表约 30 秒，手动重建不可行。旧表通过 rename 归档，API delete 在只剩一张表时被拒绝。
3. **飞书 Open API 不支持字段说明**：`description` 参数在所有 field create/update 请求中被拒绝（WrongRequestBody 1254001），只能手动在 UI 添加。

## 当前项目状态

- Phase 1.16：上下文加载规则与文档瘦身 ✅
- Phase 1.20：code review 跟进 ✅
- 测试：451 passed
- 飞书运营同步：已完成字段 ID 重构，待 commit 提交

## 给下一个 Agent 的交接

- **可接任务**：正常运行 `daily_run.sh` 和 `baseline_run.sh`；如需重建表见下方字段映射
- **表信息**：`discovery_table_id = tbl84xx4WNv54An9`（base P6y3bMbAXazlL5sui4Mc6B5znMb；名称"发现运行日志"）
- **字段 ID 映射**：在 `src/movietrace/feishu/sync.py:50-68` 的 `F` 字典
- **不要重做**：不要再改成 field_name 定位；不要再尝试 API 设置 field description
- **配置路径**：secrets `~/.config/movietrace/secrets.json` · lark-cli `~/.lark-cli/config.json`

## 数字总结

- Commits：0（待提交）
- 修改文件：`sync.py`（rewrite）、`cli.py`（-15 lines）
- 外部文件：`secrets.json`、`lark-cli config.json`
- 重建表次数：5
