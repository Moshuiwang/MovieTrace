#!/bin/bash
# ============================================================
# DEV SHADOW 每日运行脚本 — 仅限开发环境 /home/wang/myapp/Claude/MovieTrace
# ============================================================
# 警告：本脚本必须 NOT 在生产服务器 /home/ubuntu/MovieTrace 上运行。
# 生产脚本：scripts/daily_run.sh（只读对照，不要修改）
#
# 用途：在开发分支上模拟生产 cron，每天 08:00 +08 执行，连续观察 7 天。
# 开发和生产使用不同 DB、不同飞书表格，API 用量约为生产的 2 倍（已知成本）。
# ============================================================

PROJECT_DIR="/home/wang/myapp/Claude/MovieTrace"
cd "$PROJECT_DIR"

# 防御性时区固定
export TZ='Asia/Shanghai'
export MOVIETRACE_ENV='dev-shadow'

LOG_DIR="$PROJECT_DIR/reports/logs"
mkdir -p "$LOG_DIR"

# ============================================================
# 总开关检查：如需立即停止 shadow 跑，执行：
#   touch ~/.config/movietrace/shadow_disabled.flag
# ============================================================
if [ -f "$HOME/.config/movietrace/shadow_disabled.flag" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SHADOW] Kill switch active, exiting." >> "$LOG_DIR/dev_shadow_daily_$(date +%Y%m%d).log"
    exit 0
fi

LOG_FILE="$LOG_DIR/dev_shadow_daily_$(date +%Y%m%d).log"
DISCOVER_STATS="$LOG_DIR/dev_shadow_discover_stats_$(date +%Y%m%d).json"
SYNC_STATS="$LOG_DIR/dev_shadow_sync_stats_$(date +%Y%m%d).json"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
RUN_DATE=$(date +%Y-%m-%d)

{
    echo "=== MovieTrace DEV SHADOW daily-discover ==="
    echo "开始: $START_TIME"
    echo "Git branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "Git commit: $(git rev-parse --short HEAD)"
    echo "Project dir: $PROJECT_DIR"

    source "$PROJECT_DIR/.venv/bin/activate"

    # 数据库备份（保留最新 30 个）
    source "$PROJECT_DIR/scripts/_backup_db.sh" 2>/dev/null || true
    backup_database "data/movietrace.db" 30

    PYTHONPATH=src python -m movietrace.cli daily-discover --stats-out "$DISCOVER_STATS" 2>&1
    DISCOVER_EXIT=$?

    # 导出最近 1 天结果
    if [ "$DISCOVER_EXIT" -eq 0 ]; then
        PYTHONPATH=src python -m movietrace.cli export-recommendations --days 1 2>&1
        EXPORT_EXIT=$?
    else
        EXPORT_EXIT=0
    fi

    # 飞书表格同步
    SYNC_EXIT=0
    DOC_EXIT=0
    NOTIFY_EXIT=0
    DOC_URL=""
    if [ "$DISCOVER_EXIT" -eq 0 ] && [ "$EXPORT_EXIT" -eq 0 ]; then
        PYTHONPATH=src python -m movietrace.cli sync-feishu-table \
            --source reports/latest.json --date "$RUN_DATE" \
            --stats-out "$SYNC_STATS" 2>&1
        SYNC_EXIT=$?

        _DOC_OUTPUT=$(PYTHONPATH=src python -m movietrace.cli sync-feishu-doc \
            --source reports/latest.md --title "MovieTrace DEV SHADOW 每日发现 $RUN_DATE" 2>&1)
        DOC_EXIT=$?
        echo "$_DOC_OUTPUT"
        DOC_URL=$(echo "$_DOC_OUTPUT" | grep "^Doc URL:" | awk '{print $3}')

        if [ "$SYNC_EXIT" -eq 0 ]; then
            PYTHONPATH=src python -m movietrace.cli notify-feishu \
                --level success --date "$RUN_DATE" \
                --discover-stats-file "$DISCOVER_STATS" \
                --stats-file "$SYNC_STATS" \
                --report-file reports/latest.json \
                --doc-url "$DOC_URL" \
                --log-file "$LOG_FILE" 2>&1
        else
            PYTHONPATH=src python -m movietrace.cli notify-feishu \
                --level error \
                --title "[DEV SHADOW] 每日同步 - 飞书表格写入失败" \
                --detail "sync-feishu-table exit=$SYNC_EXIT" \
                --log-file "$LOG_FILE" 2>&1
        fi
        NOTIFY_EXIT=$?
    fi

    # 失败告警（discover 或 export 失败时）
    if [ "$DISCOVER_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu \
            --level error --title "[DEV SHADOW] 每日运行失败" \
            --detail "daily-discover exit=$DISCOVER_EXIT" \
            --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    elif [ "$EXPORT_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu \
            --level error --title "[DEV SHADOW] 每日运行 - 导出失败" \
            --detail "export-recommendations exit=$EXPORT_EXIT" \
            --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    fi

    # 合并退出码：discover / export / sync 任意一个非零即异常
    # DOC_EXIT 不纳入退出码（文档同步为辅助功能）
    if [ "$DISCOVER_EXIT" -ne 0 ] || [ "$EXPORT_EXIT" -ne 0 ] || [ "$SYNC_EXIT" -ne 0 ]; then
        EXIT_CODE=1
    else
        EXIT_CODE=0
    fi

    END_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
    START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || date -j -f '%Y-%m-%d %H:%M:%S %z' "$START_TIME" +%s 2>/dev/null)
    END_EPOCH=$(date -d "$END_TIME" +%s 2>/dev/null || date -j -f '%Y-%m-%d %H:%M:%S %z' "$END_TIME" +%s 2>/dev/null)
    DURATION=$(( END_EPOCH - START_EPOCH ))

    echo ""
    echo "=== DEV SHADOW 运行摘要 ==="
    echo "结束: $END_TIME"
    echo "耗时: ${DURATION}s"
    echo "退出码: $EXIT_CODE (discover=$DISCOVER_EXIT export=$EXPORT_EXIT sync=$SYNC_EXIT)"
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "状态: [SHADOW] 异常退出（discover=$DISCOVER_EXIT, export=$EXPORT_EXIT, sync=$SYNC_EXIT）"
    else
        echo "状态: [SHADOW] 正常完成"
    fi

} >> "$LOG_FILE" 2>&1

exit $EXIT_CODE
