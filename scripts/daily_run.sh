#!/bin/bash
# MovieTrace 每日自动运行脚本
# 由 crontab 调用，每天上午 08:00 执行（北京时间）

PROJECT_DIR="/home/ubuntu/MovieTrace"
cd "$PROJECT_DIR"

LOG_DIR="$PROJECT_DIR/reports/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/daily_$(date +%Y%m%d).log"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')

{
    echo "=== MovieTrace daily-discover ==="
    echo "开始: $START_TIME"

    source .venv/bin/activate

    # dry-run 模式：完整流程但不写业务结果。改为 commit 模式时删除 --dry-run
    PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run 2>&1
    EXIT_CODE=$?

    END_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
    START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || date -j -f '%Y-%m-%d %H:%M:%S %z' "$START_TIME" +%s 2>/dev/null)
    END_EPOCH=$(date -d "$END_TIME" +%s 2>/dev/null || date -j -f '%Y-%m-%d %H:%M:%S %z' "$END_TIME" +%s 2>/dev/null)
    DURATION=$(( END_EPOCH - START_EPOCH ))

    echo ""
    echo "=== 运行摘要 ==="
    echo "结束: $END_TIME"
    echo "耗时: ${DURATION}s"
    echo "退出码: $EXIT_CODE"
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "状态: ❌ 异常退出（退出码 $EXIT_CODE）"
    else
        echo "状态: ✅ 正常完成"
    fi

} >> "$LOG_FILE" 2>&1
