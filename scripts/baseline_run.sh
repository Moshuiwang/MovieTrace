#!/bin/bash
# MovieTrace 基线新季追踪脚本
# 由上层调度调用；建议每周运行一次。

PROJECT_DIR="/home/ubuntu/MovieTrace"
cd "$PROJECT_DIR"

LOG_DIR="$PROJECT_DIR/reports/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/baseline_$(date +%Y%m%d).log"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')

{
    echo "=== MovieTrace baseline-track ==="
    echo "开始: $START_TIME"

    source .venv/bin/activate

    PYTHONPATH=src python -m movietrace.cli baseline-track --mode routine 2>&1
    TRACK_EXIT=$?

    if [ "$TRACK_EXIT" -eq 0 ]; then
        PYTHONPATH=src python -m movietrace.cli export-baseline-updates --days 7 2>&1
        EXPORT_EXIT=$?
    else
        EXPORT_EXIT=0
    fi

    if [ "$TRACK_EXIT" -ne 0 ] || [ "$EXPORT_EXIT" -ne 0 ]; then
        EXIT_CODE=1
    else
        EXIT_CODE=0
    fi

    END_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
    START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || date -j -f '%Y-%m-%d %H:%M:%S %z' "$START_TIME" +%s 2>/dev/null)
    END_EPOCH=$(date -d "$END_TIME" +%s 2>/dev/null || date -j -f '%Y-%m-%d %H:%M:%S %z' "$END_TIME" +%s 2>/dev/null)
    DURATION=$(( END_EPOCH - START_EPOCH ))

    echo ""
    echo "=== 运行摘要 ==="
    echo "结束: $END_TIME"
    echo "耗时: ${DURATION}s"
    echo "退出码: $EXIT_CODE (track=$TRACK_EXIT export=$EXPORT_EXIT)"
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "状态: ❌ 异常退出（track=$TRACK_EXIT, export=$EXPORT_EXIT）"
    else
        echo "状态: ✅ 正常完成"
    fi

} >> "$LOG_FILE" 2>&1
