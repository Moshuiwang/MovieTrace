#!/bin/bash
# MovieTrace 本地端到端运行脚本
# 完全对齐 scripts/daily_run.sh 生产流程。
#
# 与生产的差异（preflight check 自动检测并标注）：
#   - feishu.doc_folder_token 缺失 → sync-feishu-doc 跳过（非核心步骤，生产也不纳入退出码）
#   - 输出同时打印到终端 + 写日志（生产只写日志）
#
# 用法：
#   ./scripts/local_e2e_run.sh               # 正常运行
#   ./scripts/local_e2e_run.sh --dry-run     # 跳过实际写入（传给 daily-discover）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

export TZ='Asia/Shanghai'
export MOVIETRACE_ENV='dev-e2e'

DRY_RUN=0
for arg in "$@"; do
    if [ "$arg" = "--dry-run" ]; then DRY_RUN=1; fi
done

LOG_DIR="$PROJECT_DIR/reports/logs"
mkdir -p "$LOG_DIR"

DISCOVER_STATS="$LOG_DIR/discover_stats_$(date +%Y%m%d).json"
SYNC_STATS="$LOG_DIR/sync_stats_$(date +%Y%m%d).json"
LOG_FILE="$LOG_DIR/local_e2e_$(date +%Y%m%d_%H%M%S).log"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
RUN_DATE=$(date +%Y-%m-%d)

# ── preflight checks ──────────────────────────────────────────────────────────

SKIP_DOC_SYNC=0

check_secret() {
    python3 -c "
import json, sys
s = json.load(open('$HOME/.config/movietrace/secrets.json'))
keys = '$1'.split('.')
val = s
for k in keys:
    val = val.get(k, {})
sys.exit(0 if val else 1)
" 2>/dev/null
}

echo "=== Preflight checks ==="
if ! check_secret "feishu.doc_folder_token"; then
    echo "[SKIP] sync-feishu-doc: feishu.doc_folder_token 未配置（本地 secrets 无此字段）"
    echo "       生产配置此字段后 sync-feishu-doc 才启用；此步骤在生产也不纳入退出码。"
    SKIP_DOC_SYNC=1
else
    echo "[OK]   sync-feishu-doc: doc_folder_token 已配置"
fi
echo ""

# ── 数据库备份 ────────────────────────────────────────────────────────────────

# shellcheck source=scripts/_backup_db.sh
source "$PROJECT_DIR/scripts/_backup_db.sh" 2>/dev/null || true
backup_database "data/movietrace.db" 30

# ── 主流程（输出同时到终端 + 日志） ──────────────────────────────────────────

{
    echo "=== MovieTrace local-e2e-run ==="
    echo "开始: $START_TIME"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "[DRY-RUN 模式：daily-discover 传 --dry-run，不写 content_updates]"
    fi
    echo ""

    source .venv/bin/activate

    # ── Step 1: daily-discover ────────────────────────────────────────────────
    echo "[1/5] daily-discover..."
    DISCOVER_ARGS="--stats-out $DISCOVER_STATS"
    if [ "$DRY_RUN" -eq 1 ]; then DISCOVER_ARGS="$DISCOVER_ARGS --dry-run"; fi
    # shellcheck disable=SC2086
    PYTHONPATH=src python -m movietrace.cli daily-discover $DISCOVER_ARGS 2>&1
    DISCOVER_EXIT=$?

    # ── Step 2: export-recommendations ───────────────────────────────────────
    EXPORT_EXIT=0
    if [ "$DISCOVER_EXIT" -eq 0 ] && [ "$DRY_RUN" -eq 0 ]; then
        echo ""
        echo "[2/5] export-recommendations --days 1..."
        PYTHONPATH=src python -m movietrace.cli export-recommendations --days 1 2>&1
        EXPORT_EXIT=$?
    elif [ "$DRY_RUN" -eq 1 ]; then
        echo "[2/5] export-recommendations: 跳过（dry-run 模式无 content_updates 可导出）"
    fi

    # ── Step 3-5: 飞书同步（dry-run 时跳过全部） ──────────────────────────────
    SYNC_EXIT=0
    DOC_EXIT=0
    NOTIFY_EXIT=0
    DOC_URL=""

    if [ "$DISCOVER_EXIT" -eq 0 ] && [ "$EXPORT_EXIT" -eq 0 ] && [ "$DRY_RUN" -eq 0 ]; then

        # Step 3: sync-feishu-table
        echo ""
        echo "[3/5] sync-feishu-table..."
        PYTHONPATH=src python -m movietrace.cli sync-feishu-table \
            --source reports/latest.json --date "$RUN_DATE" \
            --stats-out "$SYNC_STATS" 2>&1
        SYNC_EXIT=$?

        # Step 4: sync-feishu-doc（非核心，缺配置时跳过）
        echo ""
        if [ "$SKIP_DOC_SYNC" -eq 1 ]; then
            echo "[4/5] sync-feishu-doc: [SKIPPED] doc_folder_token 未配置"
            DOC_EXIT=0
        else
            echo "[4/5] sync-feishu-doc..."
            _DOC_OUTPUT=$(PYTHONPATH=src python -m movietrace.cli sync-feishu-doc \
                --source reports/latest.md --title "MovieTrace 每日发现 $RUN_DATE" 2>&1)
            DOC_EXIT=$?
            echo "$_DOC_OUTPUT"
            DOC_URL=$(echo "$_DOC_OUTPUT" | grep "^Doc URL:" | awk '{print $3}')
        fi

        # Step 5: notify-feishu
        echo ""
        echo "[5/5] notify-feishu..."
        if [ "$SYNC_EXIT" -eq 0 ]; then
            PYTHONPATH=src python -m movietrace.cli notify-feishu \
                --level success --date "$RUN_DATE" \
                --discover-stats-file "$DISCOVER_STATS" \
                --stats-file "$SYNC_STATS" \
                --report-file reports/latest.json \
                ${DOC_URL:+--doc-url "$DOC_URL"} \
                --log-file "$LOG_FILE" 2>&1
        else
            PYTHONPATH=src python -m movietrace.cli notify-feishu \
                --level error \
                --title "每日同步 - 飞书表格写入失败" \
                --detail "sync-feishu-table exit=$SYNC_EXIT" \
                --log-file "$LOG_FILE" 2>&1
        fi
        NOTIFY_EXIT=$?

    elif [ "$DRY_RUN" -eq 1 ]; then
        echo "[3/5] sync-feishu-table: 跳过（dry-run）"
        echo "[4/5] sync-feishu-doc:   跳过（dry-run）"
        echo "[5/5] notify-feishu:     跳过（dry-run）"
    fi

    # 失败告警路径（与生产一致）
    if [ "$DISCOVER_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu \
            --level error --title "每日运行失败" \
            --detail "daily-discover exit=$DISCOVER_EXIT" \
            --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    elif [ "$EXPORT_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu \
            --level error --title "每日运行 - 导出失败" \
            --detail "export-recommendations exit=$EXPORT_EXIT" \
            --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    fi

    # ── 退出码（与生产一致：DOC_EXIT 不纳入） ────────────────────────────────
    if [ "$DISCOVER_EXIT" -ne 0 ] || [ "$EXPORT_EXIT" -ne 0 ] || [ "$SYNC_EXIT" -ne 0 ]; then
        EXIT_CODE=1
    else
        EXIT_CODE=0
    fi

    END_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
    START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null)
    END_EPOCH=$(date -d "$END_TIME" +%s 2>/dev/null)
    DURATION=$(( END_EPOCH - START_EPOCH ))

    echo ""
    echo "=== 运行摘要 ==="
    echo "结束: $END_TIME"
    echo "耗时: ${DURATION}s"
    echo "日志: $LOG_FILE"
    echo "退出码: $EXIT_CODE (discover=$DISCOVER_EXIT export=$EXPORT_EXIT sync=$SYNC_EXIT doc=$DOC_EXIT notify=$NOTIFY_EXIT)"
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "状态: FAIL (discover=$DISCOVER_EXIT, export=$EXPORT_EXIT, sync=$SYNC_EXIT)"
    else
        echo "状态: OK"
    fi

    exit "$EXIT_CODE"

} 2>&1 | tee -a "$LOG_FILE"
