#!/bin/bash
# MovieTrace 冒烟测试（针对测试 base + 测试 DB，不影响生产）
# 用法：
#   bash scripts/smoke_test.sh          # 真实写入
#   bash scripts/smoke_test.sh --dry-run # 仅预览
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

export TZ='Asia/Shanghai'
export MOVIETRACE_SMOKE=1
export PYTHONPATH=src

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
fi

echo "=== MovieTrace Smoke Test ==="
echo "目标 base: WyMAbu3waapyTnsZYK5c4EQKnfe (测试副本)"
echo "目标 DB:   data/movietrace_smoke.db"
echo "dry-run:   ${DRY_RUN:-false}"
echo "开始: $(date '+%Y-%m-%d %H:%M:%S +08')"
echo ""

# 预处理：初始化烟雾测试数据库（从生产 DB 复制）
SMOKE_DB="data/movietrace_smoke.db"
if [ -f "data/movietrace.db" ]; then
    echo "[0/4] 复制生产数据库到烟雾测试库..."
    cp data/movietrace.db "$SMOKE_DB"
    echo "  $SMOKE_DB 已就绪"
else
    echo "[0/4] ⚠ 生产数据库不存在，跳过复制"
fi
echo ""

cleanup() {
    if [ -f "$SMOKE_DB" ]; then
        echo "[清理] 删除烟雾测试库..."
        rm -f "$SMOKE_DB" "$SMOKE_DB-wal" "$SMOKE_DB-shm" 2>/dev/null || true
        echo "  已删除"
    fi
}
trap cleanup EXIT

# ── 1. 连通性验证 ──────────────────────────────────────────────────────
echo "[1/5] 验证飞书连接 + 测试 base 读写权限..."
python3 -m movietrace.cli validate-feishu
echo ""

# ── 2. 同步热点发现到测试 base ─────────────────────────────────────────
echo "[2/5] 同步热点发现到测试 base..."
python3 -m movietrace.cli sync-feishu-table $DRY_RUN
echo ""

# ── 3. A库缺口同步 ─────────────────────────────────────────────────────
echo "[3/5] 同步 A 库缺口到测试 base..."
python3 -m movietrace.cli sync-feishu-gap-table $DRY_RUN || true
echo ""

# ── 4. 拉取反馈验证 ────────────────────────────────────────────────────
echo "[4/5] 回读确认写入..."
python3 -m movietrace.cli pull-feishu-feedback --days 1 --output reports/smoke_test $DRY_RUN
echo ""

# ── 5. 周报生成 ────────────────────────────────────────────────────────
echo "[5/5] 生成周报（验证报告管线）..."
python3 -m movietrace.cli export-feedback-report \
    --input reports/smoke_test/feishu_pull_latest.json \
    --output reports/smoke_test \
    $DRY_RUN 2>&1 || true
echo ""

echo "=== Smoke test 完成 ==="
echo "结束: $(date '+%Y-%m-%d %H:%M:%S +08')"
