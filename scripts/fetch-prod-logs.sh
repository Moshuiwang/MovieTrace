#!/bin/bash
# 从生产环境拉取日志到开发环境

PROD_HOST="ubuntu@ai.chunbai.com"
PROD_LOG_DIR="/home/ubuntu/MovieTrace/reports/logs"
DEV_LOG_DIR="./reports/logs"

# 创建目录
mkdir -p "$DEV_LOG_DIR"

echo "📥 正在从生产环境拉取日志..."
echo "源: $PROD_HOST:$PROD_LOG_DIR"
echo "目标: $DEV_LOG_DIR"
echo ""

# 拉取日志文件
scp -r "$PROD_HOST:$PROD_LOG_DIR/" "$DEV_LOG_DIR" 2>&1 || {
  echo "❌ 拉取失败，请检查网络连接或 SSH 配置"
  exit 1
}

echo ""
echo "✅ 日志拉取成功"
echo ""
echo "📋 最新日志文件："
ls -lh "$DEV_LOG_DIR" | grep -E "daily_|discover_|sync_" | tail -5
