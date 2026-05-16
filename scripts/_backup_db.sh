#!/bin/bash
# 数据库备份工具 — 供 daily_run.sh / baseline_run.sh source 使用
# 用法：source scripts/_backup_db.sh && backup_database

backup_database() {
    local DB_PATH="${1:-data/movietrace.db}"
    local BACKUP_DIR="data/backups"
    local MAX_BACKUPS="${2:-30}"

    if [ ! -f "$DB_PATH" ]; then
        echo "[backup] 跳过 — $DB_PATH 不存在"
        return 0
    fi

    mkdir -p "$BACKUP_DIR"

    local TIMESTAMP
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    local BACKUP_FILE="$BACKUP_DIR/movietrace_$TIMESTAMP.db"

    cp "$DB_PATH" "$BACKUP_FILE"
    echo "[backup] 已备份 → $BACKUP_FILE"

    # 旋转：只保留最新 $MAX_BACKUPS 个
    local COUNT
    COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -name "movietrace_*.db" -type f | wc -l)
    if [ "$COUNT" -gt "$MAX_BACKUPS" ]; then
        local DELETE_COUNT=$(( COUNT - MAX_BACKUPS ))
        echo "[backup] 清理 $DELETE_COUNT 个旧备份（保留 $MAX_BACKUPS）..."
        find "$BACKUP_DIR" -maxdepth 1 -name "movietrace_*.db" -type f \
            | sort \
            | head -n "$DELETE_COUNT" \
            | xargs rm -f
        echo "[backup] 清理完成"
    fi
}
