#!/bin/bash
# MovieTrace 基线新季追踪脚本
# 由上层调度调用；建议每周运行一次。

PROJECT_DIR="/home/ubuntu/MovieTrace"
cd "$PROJECT_DIR"

# 防御性时区固定：避免部署到 UTC 服务器 / systemd 清空 TZ 时 RUN_DATE 飘移
export TZ='Asia/Shanghai'

LOG_DIR="$PROJECT_DIR/reports/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/baseline_$(date +%Y%m%d).log"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S +08')
RUN_DATE=$(date +%Y-%m-%d)

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

    # 飞书表格同步（baseline 报告用独立源文件）
    SYNC_EXIT=0
    DOC_EXIT=0
    GAP_EXIT=0
    NOTIFY_EXIT=0
    if [ "$TRACK_EXIT" -eq 0 ] && [ "$EXPORT_EXIT" -eq 0 ]; then
        PYTHONPATH=src python -m movietrace.cli sync-feishu-table --source reports/baseline_latest.json --date "$RUN_DATE" 2>&1
        SYNC_EXIT=$?

        PYTHONPATH=src python -m movietrace.cli sync-feishu-doc --source reports/baseline_latest.md --title "MovieTrace 基线追踪 $RUN_DATE" 2>&1
        DOC_EXIT=$?

        # A库缺口快照同步（直接读 DB 状态，不依赖 content_updates 事件）
        PYTHONPATH=src python -m movietrace.cli sync-feishu-gap-table 2>&1
        GAP_EXIT=$?

        if [ "$SYNC_EXIT" -eq 0 ] && [ "$GAP_EXIT" -eq 0 ]; then
            PYTHONPATH=src python -m movietrace.cli notify-feishu --level success --date "$RUN_DATE" --log-file "$LOG_FILE" 2>&1
        elif [ "$SYNC_EXIT" -ne 0 ]; then
            PYTHONPATH=src python -m movietrace.cli notify-feishu --level error --title "基线同步 - 飞书表格写入失败" --detail "sync-feishu-table exit=$SYNC_EXIT" --log-file "$LOG_FILE" 2>&1
        else  # GAP_EXIT != 0
            PYTHONPATH=src python -m movietrace.cli notify-feishu --level error --title "基线同步 - A库缺口表写入失败" --detail "sync-feishu-gap-table exit=$GAP_EXIT" --log-file "$LOG_FILE" 2>&1
        fi
        NOTIFY_EXIT=$?
    fi

    if [ "$TRACK_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu --level error --title "基线追踪失败" --detail "baseline-track exit=$TRACK_EXIT" --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    elif [ "$EXPORT_EXIT" -ne 0 ]; then
        PYTHONPATH=src python -m movietrace.cli notify-feishu --level error --title "基线追踪 - 导出失败" --detail "export-baseline-updates exit=$EXPORT_EXIT" --log-file "$LOG_FILE" 2>&1
        NOTIFY_EXIT=$?
    fi

    # DOC_EXIT（文档同步）不纳入退出码：辅助功能，失败不阻塞核心流程。
    # GAP_EXIT（A库缺口快照）为核心路径，纳入退出码。
    if [ "$TRACK_EXIT" -ne 0 ] || [ "$EXPORT_EXIT" -ne 0 ] || [ "$SYNC_EXIT" -ne 0 ] || [ "$GAP_EXIT" -ne 0 ]; then
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
    echo "退出码: $EXIT_CODE (track=$TRACK_EXIT export=$EXPORT_EXIT sync=$SYNC_EXIT gap=$GAP_EXIT)"
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "状态: ❌ 异常退出（track=$TRACK_EXIT, export=$EXPORT_EXIT, sync=$SYNC_EXIT, gap=$GAP_EXIT）"
    else
        echo "状态: ✅ 正常完成"
    fi

} >> "$LOG_FILE" 2>&1
