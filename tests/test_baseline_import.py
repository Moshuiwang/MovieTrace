import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class BaselineImportTest(unittest.TestCase):
    def test_import_feishu_records_replaces_existing_source_rows(self):
        from movietrace.db.schema import connect_database, initialize_database
        from movietrace.pipeline.baseline_import import import_feishu_baseline_records

        first_records = [
            {
                "record_id": "rec1",
                "fields": {
                    "节目名": "Silo S01",
                    "已下载": True,
                    "备注": "keep this note",
                },
            },
            {
                "record_id": "rec2",
                "fields": {
                    "节目名": "Avatar The Way of Water",
                    "已上传FTP": True,
                },
            },
        ]
        second_records = [
            {
                "record_id": "rec1",
                "fields": {
                    "节目名": "Silo S01",
                    "已上架": True,
                    "备注": "updated note",
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            initialize_database(db_path)

            first_result = import_feishu_baseline_records(
                db_path,
                base_app_token="base_token",
                table_id="tbl1",
                table_name="节目",
                records=first_records,
            )
            second_result = import_feishu_baseline_records(
                db_path,
                base_app_token="base_token",
                table_id="tbl1",
                table_name="节目",
                records=second_records,
            )

            with connect_database(db_path) as conn:
                rows = conn.execute(
                    """
                    select feishu_record_id, title, online_status, source_note, raw_fields_json
                    from baseline_items
                    order by feishu_record_id
                    """
                ).fetchall()
                run_count = conn.execute(
                    "select count(*) from feishu_import_runs"
                ).fetchone()[0]

        self.assertEqual(first_result.imported_count, 2)
        self.assertEqual(second_result.imported_count, 1)
        self.assertEqual(run_count, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "rec1")
        self.assertEqual(rows[0][1], "Silo S01")
        self.assertEqual(rows[0][2], "已上架")
        self.assertEqual(rows[0][3], "updated note")
        self.assertEqual(json.loads(rows[0][4])["节目名"], "Silo S01")


if __name__ == "__main__":
    unittest.main()
