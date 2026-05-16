#!/bin/bash
# MovieTrace 每日自动运行脚本
# 由 crontab 调用，每天上午 08:00 执行（北京时间）

PROJECT_DIR="/home/ubuntu/MovieTrace"
cd "$PROJECT_DIR"

# 防御性时区固定：避免部署到 UTC 服务器 / systemd 清空 TZ 时 RUN_DATE 飘移
export TZ='Asia/Shanghai'

LOG_DIR="$PROJECT_DIR/reports/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/daily_$(date +%Y%m%d).log"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
RUN_DATE=$(date +%Y-%m-%d)

{
    echo "=== MovieTrace daily-discover ==="
    echo "开始: $START_TIME"

    source .venv/bin/activate

    # commit 模式：写入热点发现 content_updates；baseline tracking 由 baseline_run.sh 独立执行。
    PYTHONPATH=src python -m movietrace.cli daily-discover 2>&1
    DISCOVER_EXIT=$?

    # 导出最近 1 天结果到 latest.md / latest.json（固定文件名，每日覆盖）
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
    if [ "$DISCOVER_EXIT" -eq 0 ] && [ "$EXPORT_EXIT" -eq 0 ]; then
        PYTHONPATH=src python -m movietrace.cli sync-feishu-table --source reports/latest.json --date "$RUN_DATE" 2>&1
        SYNC_EXIT=$?

        PYTHONPATH=src python -m movietrace.cli sync-feishu-doc --source reports/latest.md --title "MovieTrace 每日发现 $RUN_DATE" 2>&1
        DOC_EXIT=$?

        if [ "$SYNC_EXIT" -eq 0 ]; then
            PYTHONPATH=src python -m movietrace.cli notify-feishu --level success --date "$RUN_DATE" --log-file "$LOG_FILE" 2>&1
        else
            PYTHONPATH=src python -m movietrace.cli notify-feishu --level error --title "每日同步 - 飞书表格写入失败" --detail "sync-feishu-table exit=$SYNC_EXIT" --log-file "$LOG_FILE" 2>&1
        fi
        NOTIFY_EXIT=$?
    fi

    # 失败告警（discover 或 export 失败时）
    if [ "$DISCOVER_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu --level error --title "每日运行失败" --detail "daily-discover exit=$DISCOVER_EXIT" --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    elif [ "$EXPORT_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu --level error --title "每日运行 - 导出失败" --detail "export-recommendations exit=$EXPORT_EXIT" --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    fi

    # 合并退出码：任意一个非零即异常
    # DOC_EXIT（文档同步）不纳入退出码：文档同步为辅助功能，失败不阻塞核心流程，
    # 错误已通过 NOTIFY_EXIT 告警；SYNC_EXIT（表格同步）为核心路径，纳入退出码。
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
    echo "=== 运行摘要 ==="
    echo "结束: $END_TIME"
    echo "耗时: ${DURATION}s"
    echo "退出码: $EXIT_CODE (discover=$DISCOVER_EXIT export=$EXPORT_EXIT sync=$SYNC_EXIT)"
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "状态: ❌ 异常退出（discover=$DISCOVER_EXIT, export=$EXPORT_EXIT, sync=$SYNC_EXIT）"
    else
        echo "状态: ✅ 正常完成"
    fi

} >> "$LOG_FILE" 2>&1
