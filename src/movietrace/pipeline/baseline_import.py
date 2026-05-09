from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from movietrace.db.schema import connect_database


@dataclass(frozen=True)
class BaselineImportResult:
    run_id: int
    imported_count: int
    skipped_count: int


def import_feishu_baseline_records(
    db_path: str | Path,
    *,
    base_app_token: str,
    table_id: str,
    table_name: str,
    records: Iterable[dict[str, Any]],
) -> BaselineImportResult:
    normalized_records = list(records)
    with connect_database(db_path) as conn:
        cursor = conn.execute(
            """
            insert into feishu_import_runs(
                base_app_token, table_id, table_name, status, record_count
            )
            values (?, ?, ?, 'running', 0)
            """,
            (base_app_token, table_id, table_name),
        )
        run_id = int(cursor.lastrowid)

        conn.execute(
            "delete from baseline_items where feishu_record_id is not null"
        )

        imported_count = 0
        skipped_count = 0
        for record in normalized_records:
            fields = record.get("fields") or {}
            title = _text_value(fields.get("节目名"))
            if not title:
                skipped_count += 1
                continue
            conn.execute(
                """
                insert into baseline_items(
                    feishu_record_id,
                    title,
                    online_status,
                    source_note,
                    raw_fields_json,
                    content_granularity,
                    match_status
                )
                values (?, ?, ?, ?, ?, ?, 'unmatched')
                """,
                (
                    record.get("record_id"),
                    title,
                    _online_status(fields),
                    _text_value(fields.get("备注")),
                    json.dumps(fields, ensure_ascii=False, sort_keys=True),
                    _guess_granularity(title),
                ),
            )
            imported_count += 1

        conn.execute(
            """
            update feishu_import_runs
            set status = 'success',
                record_count = ?,
                finished_at = current_timestamp,
                note = ?
            where id = ?
            """,
            (
                imported_count,
                f"skipped_empty_title={skipped_count}",
                run_id,
            ),
        )
        conn.commit()

    return BaselineImportResult(
        run_id=run_id,
        imported_count=imported_count,
        skipped_count=skipped_count,
    )


def _text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("name") or item.get("value")
                if text:
                    parts.append(str(text))
            elif item is not None:
                parts.append(str(item))
        return "".join(parts).strip()
    return str(value).strip()


def _truthy_field(fields: dict[str, Any], field_name: str) -> bool:
    value = fields.get(field_name)
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | dict):
        return bool(value)
    return bool(value)


def _online_status(fields: dict[str, Any]) -> str:
    for field_name, status in (
        ("已上架", "已上架"),
        ("已转码", "已转码"),
        ("已上传FTP", "已上传FTP"),
        ("已下载", "已下载"),
    ):
        if _truthy_field(fields, field_name):
            return status
    return "未知"


def _guess_granularity(title: str) -> str:
    normalized = title.lower()
    if " s" in normalized and normalized.rsplit(" s", 1)[-1][:2].isdigit():
        return "season"
    return "unknown"
