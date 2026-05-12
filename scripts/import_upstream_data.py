"""将 source_records/ 下的 A 库 CSV 导入 SQLite。

用法：
    PYTHONPATH=src python scripts/import_upstream_data.py

前置条件：
    - migration 005 已执行（upstream_programs / upstream_episodes 表已创建）
    - source_records/节目数据.csv 和 子节目数据.csv 存在
"""

import csv
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "movietrace.db"
PROGRAM_CSV = PROJECT_ROOT / "source_records" / "节目数据.csv"
EPISODE_CSV = PROJECT_ROOT / "source_records" / "子节目数据.csv"

# CSV column → upstream_programs column mapping (columns are identical except CSV has 'id' first)
PROGRAM_COLS = [
    "country_count", "country_codes", "country_code_property_types",
    "multi_language_count", "multi_language_ids", "language_ids",
    "multi_language_names", "multi_language_summaries",
    "multi_language_bright_spots", "multi_language_update_infos",
    "multi_language_json", "id", "imdb_id", "code", "program_status",
    "make_by_star", "name", "make_year", "program_number", "episodes",
    "poster_type", "delete_flag", "metadata_modify_flag", "online_flag",
    "encryption_type", "tenant_id", "update_status", "first_publish_time",
    "fk_publisher_id", "download_right", "download_right_info",
    "status_explanation", "turn_on_watermark", "watermark_location",
    "create_id", "create_instant", "modify_id", "modify_instant",
]

EPISODE_COLS = [
    "country_count", "country_codes", "country_code_available",
    "multi_language_count", "multi_language_ids", "language_ids",
    "multi_language_names", "multi_language_summaries",
    "multi_language_bright_spots", "multi_language_update_infos",
    "multi_language_json", "id", "code", "name", "episode", "paragraph",
    "duration_hour", "duration_minute", "duration_second",
    "fk_program_content_id", "fk_video_ondemand_id", "video_status",
    "effective_time", "source_type", "delete_flag", "metadata_modify_flag",
    "online_flag", "direct_weight", "tenant_id", "first_publish_time",
    "dot_status", "prologue_time", "epilogue_time", "support_download",
    "support_download_remarks", "original_publisher", "original_source",
    "import_video_name", "create_id", "create_instant", "modify_id",
    "modify_instant", "pc_id", "pc_imdb_id", "pc_code", "pc_name",
    "pc_type", "pc_program_status",
]


def clean_row(row: dict, col_list: list[str]) -> tuple:
    """Extract and clean values for a list of columns."""
    return tuple(row.get(col, "") for col in col_list)


def import_csv(conn: sqlite3.Connection, csv_path: Path, table: str,
               col_list: list[str], batch_size: int = 500) -> int:
    """Import CSV into table. Returns row count."""
    placeholders = ", ".join(["?"] * len(col_list))
    cols_str = ", ".join(col_list)
    sql = f"insert or ignore into {table} ({cols_str}) values ({placeholders})"

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        total = 0
        for i, row in enumerate(reader):
            # Clean BOM from first row's column names
            if i == 0:
                cleaned = {}
                for k, v in row.items():
                    cleaned[k.lstrip("﻿").strip()] = v
                row = cleaned
            batch.append(clean_row(row, col_list))
            if len(batch) >= batch_size:
                conn.executemany(sql, batch)
                total += len(batch)
                batch = []
        if batch:
            conn.executemany(sql, batch)
            total += len(batch)
    return total


def main():
    if not PROGRAM_CSV.exists():
        print(f"错误: {PROGRAM_CSV} 不存在", file=sys.stderr)
        sys.exit(1)
    if not EPISODE_CSV.exists():
        print(f"错误: {EPISODE_CSV} 不存在", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("pragma foreign_keys = on")

    # Verify tables exist
    tables = conn.execute(
        "select name from sqlite_master where type='table' and name in ('upstream_programs', 'upstream_episodes')"
    ).fetchall()
    existing = {r[0] for r in tables}
    if "upstream_programs" not in existing or "upstream_episodes" not in existing:
        print("错误: upstream 表未创建，请先运行 migration 005", file=sys.stderr)
        sys.exit(1)

    # Check if already imported
    cur = conn.execute("select count(*) from upstream_programs")
    if cur.fetchone()[0] > 0:
        print("警告: upstream_programs 表非空，将清空后重新导入")
        conn.execute("delete from upstream_episodes")
        conn.execute("delete from upstream_programs")

    print("导入 节目数据 → upstream_programs ...")
    n_prog = import_csv(conn, PROGRAM_CSV, "upstream_programs", PROGRAM_COLS)
    print(f"  导入: {n_prog} 行")

    print("导入 子节目数据 → upstream_episodes ...")
    n_ep = import_csv(conn, EPISODE_CSV, "upstream_episodes", EPISODE_COLS)
    print(f"  导入: {n_ep} 行")

    conn.commit()

    # Verify
    prog_count = conn.execute("select count(*) from upstream_programs").fetchone()[0]
    ep_count = conn.execute("select count(*) from upstream_episodes").fetchone()[0]
    orphan_count = conn.execute("""
        select count(*) from upstream_episodes e
        left join upstream_programs p on e.fk_program_content_id = p.id
        where p.id is null
    """).fetchone()[0]

    print(f"\n验证:")
    print(f"  upstream_programs: {prog_count} 行")
    print(f"  upstream_episodes: {ep_count} 行")
    print(f"  孤儿引用: {orphan_count}")

    conn.close()
    print("\n导入完成。")


if __name__ == "__main__":
    main()
