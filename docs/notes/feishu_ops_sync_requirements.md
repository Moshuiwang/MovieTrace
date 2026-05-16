# MovieTrace 飞书运营同步需求（历史草案记录）

状态：**已落地**（V1 运行观察期）。2026-05-16 起 V1 闭环：飞书三张子表 + sync_doc + notify + 反馈回流。
原始草案日期：2026-05-14
落地里程碑：P1.21（A 库缺口子表）/ P1.21.5（lark-cli → REST API）/ P1.21.6（数据质量）/ P1.21.9（sync_doc 改 import_task）/ P1.23（运营反馈回流）

> 当前运行状态见 [`STATE.md`](../../STATE.md)；运营字段填写规范见 [`feishu_feedback_spec.md`](../operations/feishu_feedback_spec.md)；CLI 命令清单见 [`context_map.md`](../context_map.md) § 3。本文件作为产品决策的历史草案保留——记录了"为什么这么做"的判断（推荐边界、范围决策），未来调整时可对照参考；不再作为待执行计划。

背景：MovieTrace 已进入 V1 运行观察期，`daily-discover`、`export-recommendations` 已能生成本地 MD/JSON 报告。运营查看结果仍依赖服务器文件或 GitHub，不利于日常消费和异常响应。

---

## 1. 产品定位

**MovieTrace 飞书运营同步**的目标是：

> 把 MovieTrace 每日发现结果自动送达运营可消费的位置，并在异常时主动通知负责人。

它不是新的影视发现逻辑，也不是飞书反向控制 MovieTrace。它是 `daily-discover` 和 `export-recommendations` 之后的运营同步层。

推荐边界：

```text
MovieTrace 主链路：
采集数据 -> 评分/匹配 -> 写 SQLite -> 导出 MD/JSON

飞书运营同步层：
读取 latest.json/latest.md -> 同步飞书多维表格 -> 发送飞书总结/告警
```

核心原则：

1. SQLite + MD/JSON 仍是事实源。
2. 飞书多维表格是运营消费层，不是事实源。
3. 飞书同步失败不应推翻当天发现结果。
4. 飞书同步不反向修改 MovieTrace 数据库。
5. 后续“飞书给远程 AI Agent 下指令”属于独立 Agent 控制面需求，不纳入本阶段。

## 2. 第一阶段范围

第一阶段只做运营同步闭环：

1. `daily-discover` 成功后运行 `export-recommendations --days 1`。
2. 读取 `reports/latest.json`，同步当天更新事件到飞书多维表格。
3. 表格同步成功后，自动发送一条简要飞书总结通知。
4. `daily-discover`、`export-recommendations` 或飞书同步失败时，发送飞书告警。

不做：

- 不新增影视发现、评分、匹配逻辑。
- 不改变 `content_updates` 写入语义。
- 不从飞书读取人工反馈并回写 B 库。
- 不覆盖运营在飞书表中的人工字段。
- 不实现飞书指挥远程 AI Agent。

## 3. 推荐自动化流程

当前 `scripts/daily_run.sh` 已由 crontab 每天 08:00 北京时间调用，并已具备基于退出码的分支判断能力。飞书同步应接入同一个脚本的末尾，而不是另设手动步骤。

目标流程：

```text
crontab
  ↓
scripts/daily_run.sh
  ↓
daily-discover
  ↓ 成功
export-recommendations --days 1
  ↓ 成功
sync-feishu-table --source reports/latest.json --notify-summary --log-file "$LOG_FILE"
  ↓
飞书多维表格更新 + 飞书总结通知

失败分支：
daily-discover/export/sync 任一关键步骤失败
  ↓
notify-feishu 发送失败或部分成功告警
```

建议 CLI 形态：

```bash
PYTHONPATH=src python -m movietrace.cli sync-feishu-table \
  --source reports/latest.json \
  --mode upsert \
  --notify-summary \
  --log-file "$LOG_FILE"
```

失败告警可独立命令：

```bash
PYTHONPATH=src python -m movietrace.cli notify-feishu \
  --level error \
  --title "MovieTrace 每日运行失败" \
  --log-file "$LOG_FILE"
```

## 4. 飞书多维表格产品形态

### 4.1 表格用途

飞书多维表格用于运营查看、筛选和人工补充状态。

第一版建议将表格定位为“更新事件池”：

- 每条记录对应一个 `content_update_id`。
- 重复运行同一天同步不重复插入。
- 运营可在同一张表中按发现日期、优先级、类型筛选。

待定问题：

- 是否改成“每日快照表”，即唯一键为 `run_date + content_update_id`。
- 如果运营希望保留每天完整快照，即使同一事件重复出现，也应采用每日快照模式。

### 4.2 字段建议

系统字段建议：

| 字段 | 来源 | 说明 |
| --- | --- | --- |
| `content_update_id` | `latest.json` | 幂等唯一键 |
| `发现日期` | daily run 日期 | 便于按天筛选 |
| `标题` | `title` | 内容标题 |
| `类型` | `content_type`，如后续 JSON 提供 | movie / tv |
| `更新类型` | `update_type` | `new_discovery` / `new_season` 等 |
| `优先级` | `priority` | P0 / P1 / P2 |
| `hot_score` | `hot_score`，如后续 JSON 提供 | 热度分 |
| `剧集名` | `series_name` | TV 剧集名 |
| `季号` | `season` | 新季号 |
| `TMDb TV ID` | `tmdb_tv_id` | 追溯用 |
| `是否低置信度` | `match_confidence_low`，如后续 JSON 提供 | 人工确认入口 |
| `数据源状态` | `source_data_status` | fresh / fallback / failed |
| `检测时间` | `created_at` | MovieTrace 检测时间 |
| `同步时间` | 同步命令生成 | 写入飞书时间 |
| `同步批次` | daily run id | 如 `2026-05-15` |

人工字段建议单独保留，不由同步程序覆盖：

| 字段 | 说明 |
| --- | --- |
| `运营状态` | 待看 / 已看 / 采纳 / 忽略 |
| `运营备注` | 人工备注 |
| `供应商状态` | 未提交 / 已提交 / 已反馈 |
| `负责人` | 运营负责人 |

同步规则：

1. 只写系统字段。
2. 创建记录时可初始化人工字段为空或默认“待看”。
3. 更新已有记录时不得覆盖人工字段。

## 5. 飞书总结通知

表格同步成功后，必须发送一条简要总结通知给负责人或运营群。

通知不替代表格，只提供当日状态和入口。

建议内容：

```text
MovieTrace 每日发现完成 - 2026-05-15

同步结果：成功
同步条数：18
新增发现：6
新季更新：12
待人工确认：1
优先级：P0=0 / P1=12 / P2=6
数据源：TMDb fresh，Trakt fresh，FlixPatrol fallback

飞书表格：<链接>
本地日志：reports/logs/daily_20260515.log
```

失败或部分成功通知至少包含：

- `daily-discover` 是否成功。
- `export-recommendations` 是否成功。
- `sync-feishu-table` 是否成功。
- 失败原因摘要。
- 本地日志路径。

## 6. lark-cli 调研结论

用户建议使用飞书官方开源 CLI：`larksuite/cli`。

调研结论：

- 官方仓库：<https://github.com/larksuite/cli>
- 官方文档：<https://feishu-cli.com/zh/>
- npm 包：`@larksuite/cli`
- 二进制：`lark-cli`
- 许可证：MIT
- 官方定位：面向 AI Agent 和开发者的飞书/Lark 命令行工具
- 覆盖能力：消息、云文档、多维表格、电子表格、知识库、任务等
- 分发方式：npm 安装 Go 编译的跨平台二进制

本机环境确认：

```text
node --version  -> v20.20.2
npm --version   -> 10.8.2
lark-cli --version -> lark-cli version 1.0.23
```

当前认证状态观察：

- `lark-cli auth status` 显示 bot/tenant 身份可用。
- user token 已过期。
- 第一阶段多维表写入和消息发送应优先使用 `--as bot`。

相关命令能力已确认：

```bash
# 多维表记录搜索
lark-cli base +record-search --as bot ...

# 多维表记录创建/更新
lark-cli base +record-upsert --as bot ...

# 批量创建/更新
lark-cli base +record-batch-create --as bot ...
lark-cli base +record-batch-update --as bot ...

# 飞书消息发送
lark-cli im +messages-send --as bot --markdown ...
```

## 7. 依赖与运行约束

### 7.1 依赖定位

`lark-cli` 不属于 Python 依赖，不应写入 `requirements.txt`。

它应作为运行环境前置条件记录在运维文档中：

```bash
npm install -g @larksuite/cli
lark-cli config init
lark-cli auth login --recommend
lark-cli auth status
```

### 7.2 crontab 环境风险

当前交互式 shell 中的 `lark-cli` 路径来自用户级 Node 管理环境：

```text
/run/user/1000/fnm_multishells/.../bin/lark-cli
```

该路径可能不会出现在 crontab 的 `PATH` 中。

产品/实现需求：

1. `daily_run.sh` 必须能在非交互式 crontab 环境中定位 `lark-cli`。
2. 建议提供 `LARK_CLI_BIN` 配置项或在脚本中设置稳定 PATH。
3. 找不到 `lark-cli` 时，应将飞书同步标记为失败，并尝试通过可用通知渠道告警；不能影响已完成的本地发现结果。

### 7.3 配置建议

建议配置分层：

| 配置 | 建议位置 | 说明 |
| --- | --- | --- |
| `lark_cli_bin` | `config.yaml` | `lark-cli` 稳定路径 |
| `base_token` | `config.yaml` 或 `secrets.json` | 飞书多维表格 token，视团队安全要求决定 |
| `table_id` | `config.yaml` | 目标表 |
| `notify_chat_id` | `config.yaml` 或 `secrets.json` | 目标群聊/个人会话 |
| App ID / App Secret | lark-cli keychain | 优先交给 `lark-cli config/auth` 管理 |

如果后续不用 `lark-cli` 而改回 Python API，才需要重新讨论 App Secret 在 `secrets.json` 中的格式。

## 8. 幂等策略

第一版建议：

1. 从 `latest.json` 读取每条 `content_update_id`。
2. 使用 `lark-cli base +record-search` 在飞书表中按 `content_update_id` 搜索。
3. 若找到精确匹配记录，使用 `record_id` 更新系统字段。
4. 若没有找到，创建新记录。
5. 若找到多条匹配，记录异常并跳过自动更新，避免覆盖错误记录。

数据量预期每天较小，第一版可以逐条处理。后续若同步量变大，再改为批量查询 + 批量更新。

## 9. 成功/失败分级

建议分级：

| 状态 | 条件 | 通知 |
| --- | --- | --- |
| 成功 | discover 成功、export 成功、飞书表同步成功、总结通知成功 | 成功总结 |
| 部分成功 | discover/export 成功，但飞书表同步失败 | 部分成功告警 |
| 部分成功 | 表格同步成功，但总结通知失败 | 本地日志记录，可选告警 |
| 失败 | discover 失败 | 失败告警 |
| 失败 | export 失败 | 失败告警 |

待定：

- FlixPatrol fallback 是否只在总结里提示，还是触发部分成功。
- P2+ 数量为 0 是否触发异常告警。
- 全部 source fallback 是否触发异常告警。

## 10. 验收标准草案

第一版验收标准：

1. `daily-discover` 成功、`export-recommendations` 成功后，飞书表能看到当天更新事件。
2. 重复运行不会重复插入同一条 `content_update_id`。
3. `sync-feishu-table --notify-summary` 成功后，负责人收到一条简要飞书总结通知。
4. 总结通知包含发现日期、同步条数、类型统计、优先级统计、数据源状态、飞书表链接、本地日志路径。
5. `daily-discover` 或 `export-recommendations` 失败时，飞书收到失败告警。
6. 飞书 API / `lark-cli` 失败时，本地日志清楚记录时间、目标表、命令、退出码、错误摘要。
7. 不改变 `content_updates`、评分、匹配、发现逻辑。
8. 不覆盖飞书表中运营人工维护字段。
9. crontab 非交互式环境中可稳定运行。

## 11. 明天需继续打磨的问题

优先级从高到低：

1. **当前 cron 是否从 dry-run 切到 commit。**  
   当前 `scripts/daily_run.sh` 仍使用 `daily-discover --dry-run`。若继续 dry-run，`export-recommendations` 读到的是历史库中已存在事件，不一定是当天真实新增事件。

2. **飞书表格是事件池还是每日快照。**  
   事件池使用 `content_update_id` 幂等；每日快照使用 `run_date + content_update_id` 幂等。

3. **通知发给谁。**  
   个人、运营群、机器人专用群会影响 `chat_id`、权限和可见范围。

4. **同步哪些内容。**  
   第一版建议同步全部 `latest.json`，用字段区分 P0/P1/P2、低置信度、更新类型。

5. **是否需要同时同步 Markdown 文档。**  
   多维表适合筛选；Markdown 更适合快速阅读。当运营反馈“表格不够可读”时，可追加文档同步。

6. **`lark-cli` 版本是否固定。**  
   当前本机为 1.0.23。生产运行建议记录最低版本，必要时锁定安装版本。

7. **字段 schema 是否由程序自动创建。**  
   第一版建议人工创建飞书表字段，程序启动时只做 schema 检查。自动建字段可放后续增强。

8. **失败告警是否也依赖 `lark-cli`。**  
   如果 `lark-cli` 本身不可用，飞书告警也会失败。是否需要邮件或本地特殊日志作为兜底，待定。

## 12. 后续进入开发前的文档动作

进入实现前应新建任务包，至少明确：

- 允许修改的文件范围。
- CLI 参数。
- `config.yaml` / `secrets.json` 字段。
- 飞书表字段映射。
- `daily_run.sh` 分支逻辑。
- 验证命令。
- 人工验收步骤。

如该需求从“运营同步层”扩大到“飞书控制远程 AI Agent”，应另起项目或 ADR，不应直接塞入 MovieTrace 主链路。
