# ADR-0011: Secrets 文件路径从 /tmp 迁移到 ~/.config/movietrace/

**状态：** Accepted
**日期：** 2026-05-14
**决策者：** moshuiwang + Claude Code (deepseek-v4-pro)

## 上下文

当前 4 个文件 8 处硬编码 `/tmp/movietrace_phase0_secrets.json`：

- `cli.py` — 5 处（`_load_secrets()`、`daily_discover`、`validate_feishu`、`fetch_tmdb_trending`、`inspect_api_usage`）
- `flixpatrol_api.py` — 1 处（模块级常量 `SECRETS_PATH`）
- `discovery.py` — 1 处（`_load_secrets()`）
- `entity_matching.py` — 1 处（`match_upstream_program` CLI）

`/tmp` 的问题：
- 多用户系统中其他用户可能看到文件（取决于 umask）
- 系统重启或 tmpwatch 可能清理文件
- 语义上不是长期秘密存储目录
- 路径分散在多个模块，未来改路径要改 8 处

## 决策

**迁移 secrets 到 `~/.config/movietrace/secrets.json`，收敛读取逻辑到单一配置模块。**

具体设计：
- 默认路径：`~/.config/movietrace/secrets.json`
- 向后兼容：新路径不存在时 fallback 读取 `/tmp/movietrace_phase0_secrets.json`（带 deprecation warning）
- 收敛到 `src/movietrace/config.py`，提供 `load_secrets()` / `get_secrets_path()` 两个公共函数
- 启动时检查文件权限，非 `0600` 时 warning
- 禁止提交 secrets 到 git（已有 `.gitignore` 保障）

## 后果

**正面：**
- secrets 不会因系统重启丢失
- 单一读取入口，未来改路径只改一处
- 权限检查防止泄露
- 向后兼容，不破坏现有部署

**负面 / 待解决：**
- 需要手动迁移现有 secrets 文件到新位置
- 依赖 `~/.config` 目录，非标准 Linux 环境（如某些容器）可能需要创建

## 备选方案

### 备选 A：环境变量
- 优点：无文件泄露风险，CI 友善
- 缺点：10+ 个 key 不便管理；当前 JSON 结构（嵌套、数组）不适合扁平 env var
- 拒绝原因：OMDb 的 `api_keys` 是数组，Trakt/Feishu 是嵌套对象，环境变量表达力不足

### 备选 B：保持 `/tmp` 不动
- 优点：零成本
- 缺点：不解决 CR-007 指出的安全和持久性问题
- 拒绝原因：用户已确认迁移方向

## 引用

- 来源：CR-007（`reports/code_review_2026-05-14.md`）
- 任务包：`docs/tasks/p1.12_hotfix_f_secrets_path_migration.md`
- 当前硬编码位置：`cli.py:169,337,406,414,612` · `flixpatrol_api.py:15` · `discovery.py:763` · `entity_matching.py:892`
