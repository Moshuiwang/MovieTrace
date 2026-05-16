#!/bin/bash
# MovieTrace V1 观察期周报脚本
# 手动每周触发（建议周日），不接 cron。
# 用法：bash scripts/weekly_feedback.sh [--dry-run]

PROJECT_DIR="/home/ubuntu/MovieTrace"
cd "$PROJECT_DIR"

LOG_DIR="$PROJECT_DIR/reports/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/weekly_feedback_$(date +%Y%m%d_%H%M).log"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
DRY_RUN=""
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
fi

{
    echo "=== MovieTrace weekly-feedback ==="
    echo "开始: $START_TIME"
    echo "dry-run: ${DRY_RUN:-false}"
    echo ""

    source .venv/bin/activate 2>/dev/null || true

    echo "[1/2] 拉取飞书运营反馈..."
    PYTHONPATH=src python3 -m movietrace.cli pull-feishu-feedback --days 7 $DRY_RUN 2>&1
    PULL_EXIT=$?

    if [ "$PULL_EXIT" -ne 0 ]; then
        echo ""
        echo "ERROR: pull-feishu-feedback 失败 (exit $PULL_EXIT)，终止"
        echo "结束: $(date '+%Y-%m-%d %H:%M:%S +08')"
        exit $PULL_EXIT
    fi

    echo ""
    echo "[2/2] 生成周报..."
    PYTHONPATH=src python3 -m movietrace.cli export-feedback-report $DRY_RUN 2>&1
    EXPORT_EXIT=$?

    echo ""
    if [ "$EXPORT_EXIT" -eq 0 ]; then
        echo "✓ 周报生成完成"
        PYTHONPATH=src python3 -m movietrace.cli notify-feishu \
            --level success \
            --date "$(date +%Y-%m-%d)" \
            --stats-file reports/feedback/feishu_pull_latest.json 2>/dev/null || true
    else
        echo "ERROR: export-feedback-report 失败 (exit $EXPORT_EXIT)"
        PYTHONPATH=src python3 -m movietrace.cli notify-feishu \
            --level error \
            --title "weekly_feedback 周报生成失败" \
            --detail "export-feedback-report exit $EXPORT_EXIT" 2>/dev/null || true
    fi

    echo ""
    echo "结束: $(date '+%Y-%m-%d %H:%M:%S +08')"
    exit $EXPORT_EXIT

} 2>&1 | tee "$LOG_FILE"

exit "${PIPESTATUS[0]}"
