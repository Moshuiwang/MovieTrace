# 从生产环境拉取日志

## 背景

生产环境（ubuntu 账户）的 cron 任务（`daily-discover`、`sync-feishu-table`）运行时会在 `/home/ubuntu/MovieTrace/reports/logs/` 下生成日志文件。开发环境需要查看这些日志来调试生产问题，但**不修改生产环境本身**。

本文档描述如何从开发环境（wang 账户）安全地拉取生产日志。

## 前置条件

✅ 已配置：
- 生产服务器：`ai.chunbai.com`
- 生产账户：`ubuntu`
- 开发账户：`wang`（与生产在同一 VPS 上）
- SSH 密钥认证：wang 可以无密码 SSH 到 ubuntu 账户

**如果还未配置，执行以下命令一次**（在本地电脑执行）：

```bash
ssh ubuntu@ai.chunbai.com << 'EOF'
# 生成 wang 的 SSH 密钥（如果没有）
sudo -u wang bash -c 'mkdir -p ~/.ssh && ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" || true'

# 添加 wang 的公钥到 ubuntu 的 authorized_keys
WANG_PUBKEY=$(sudo -u wang cat /home/wang/.ssh/id_rsa.pub)
mkdir -p /home/ubuntu/.ssh
echo "$WANG_PUBKEY" >> /home/ubuntu/.ssh/authorized_keys
chmod 600 /home/ubuntu/.ssh/authorized_keys

# 验证
sudo -u wang ssh -o StrictHostKeyChecking=no ubuntu@ai.chunbai.com "whoami"
EOF
```

## 使用方法

### 快速拉取日志

在开发环境执行：

```bash
cd /home/wang/myapp/Claude/MovieTrace
./scripts/fetch-prod-logs.sh
```

脚本会：
1. 通过 SSH 连接到生产环境（ubuntu 账户）
2. 从 `/home/ubuntu/MovieTrace/reports/logs/` 拉取所有日志文件
3. 保存到 `./reports/logs/logs/`
4. 列出最新的日志文件

### 查看日志

拉取完成后，查看最新的日志：

```bash
# 今天的日志
cat ./reports/logs/logs/daily_$(date +%Y%m%d).log

# 特定日期的日志
cat ./reports/logs/logs/daily_20260520.log

# 查看所有日志文件
ls -lh ./reports/logs/logs/
```

### 日志文件说明

| 文件 | 说明 |
|---|---|
| `daily_YYYYMMDD.log` | 每日 cron 的完整运行日志（包含 discover、export、sync、notify 的步骤） |
| `discover_stats_YYYYMMDD.json` | 每日 discovery 的统计数据（发现的新集数等） |
| `sync_stats_YYYYMMDD.json` | 飞书表格同步的统计数据 |
| `baseline_YYYYMMDD.log` | baseline tracking 的日志（如果有执行） |

## 调试生产问题

### 场景 1：生产 cron 运行失败

1. 拉取日志：`./scripts/fetch-prod-logs.sh`
2. 查看最新日志：`cat ./reports/logs/logs/daily_$(date +%Y%m%d).log`
3. 找到"❌ 异常退出"或错误堆栈
4. 根据错误修复代码，提交 PR

### 场景 2：特定日期的问题

```bash
./scripts/fetch-prod-logs.sh
cat ./reports/logs/logs/daily_20260519.log  # 查看 5 月 19 日的日志
```

## 故障排除

### 问题：Permission denied

**现象**：`scp: mkdir ./reports/logs: Permission denied`

**原因**：`./reports/logs` 目录权限不对（属于 root）

**解决**：
```bash
sudo chown -R wang:wang ./reports/logs
```

### 问题：Host key verification failed

**现象**：`Host key verification failed`

**原因**：SSH 首次连接需要确认 host key

**解决**：
```bash
ssh-keyscan -t rsa ai.chunbai.com >> ~/.ssh/known_hosts
```

### 问题：Permission denied (publickey)

**现象**：`ubuntu@ai.chunbai.com: Permission denied (publickey)`

**原因**：SSH 密钥配置不正确

**解决**：
1. 验证 wang 的私钥存在：`ls -la ~/.ssh/id_rsa`
2. 重新配置 authorized_keys（参考"前置条件"部分）

## 脚本详解

`scripts/fetch-prod-logs.sh` 的工作原理：

```bash
# 1. 定义源和目标路径
PROD_HOST="ubuntu@ai.chunbai.com"
PROD_LOG_DIR="/home/ubuntu/MovieTrace/reports/logs"
DEV_LOG_DIR="./reports/logs"

# 2. 创建本地目录
mkdir -p "$DEV_LOG_DIR"

# 3. 通过 scp 拉取日志（递归复制整个目录）
scp -r "$PROD_HOST:$PROD_LOG_DIR/" "$DEV_LOG_DIR"

# 4. 显示最新的日志文件
ls -lh "$DEV_LOG_DIR"
```

## 注意事项

- ⚠️ **日志是读取权限**：拉下来的日志是只读的，不会修改生产环境
- ⚠️ **定期清理**：`./reports/logs/logs/` 会逐渐变大，可以定期删除旧日志
- ✅ **安全**：使用 SSH 密钥认证，无需密码，无需在脚本中存储凭证

## 相关资源

- 生产部署链路：[`docs/context_map.md § 生产部署`](../context_map.md)
- 日志生成位置：[`scripts/daily_run.sh`](../../scripts/daily_run.sh)（生产 cron 脚本）
