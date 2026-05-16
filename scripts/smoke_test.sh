#!/bin/bash
# MovieTrace 冒烟测试（针对测试 base，不影响生产多维表格）
# 用法：bash scripts/smoke_test.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

export TZ='Asia/Shanghai'
export MOVIETRACE_SMOKE=1
export PYTHONPATH=src

echo "=== MovieTrace Smoke Test ==="
echo "目标 base: WyMAbu3waapyTnsZYK5c4EQKnfe (测试副本)"
echo "开始: $(date '+%Y-%m-%d %H:%M:%S +08')"
echo ""

# ── 1. 连通性验证 ──────────────────────────────────────────────────────
echo "[1/4] 验证飞书连接 + 测试 base 读写权限..."
python3 -m movietrace.cli validate-feishu
echo ""

# ── 2. 读取热点发现表 ──────────────────────────────────────────────────
echo "[2/4] 读取测试 base 热点发现表 (dry-run)..."
python3 -m movietrace.cli pull-feishu-feedback --days 1 --output reports/smoke_test --dry-run
echo ""

# ── 3. 同步写入预览 ────────────────────────────────────────────────────
echo "[3/4] 同步热点发现到测试 base (dry-run，不实际写入)..."
python3 -m movietrace.cli sync-feishu-table --dry-run 2>&1 || true
echo ""

# ── 4. A库缺口同步预览 ─────────────────────────────────────────────────
echo "[4/4] 同步 A 库缺口到测试 base (dry-run，不实际写入)..."
python3 -m movietrace.cli sync-feishu-gap-table --dry-run 2>&1 || true
echo ""

echo "=== Smoke test 完成 ==="
echo "结束: $(date '+%Y-%m-%d %H:%M:%S +08')"
