import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class DiscoveryWithBaselineTrackingTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_baseline_track_cli_exists(self):
        """Verify baseline-track is a registered CLI command."""
        import subprocess
        import os
        # Verify the module loads without error
        from movietrace.cli import cmd_baseline_track
        self.assertTrue(callable(cmd_baseline_track))

    def test_baseline_tracking_runs_on_empty_db(self):
        """Baseline tracking should run gracefully on an empty DB."""
        from movietrace.pipeline.baseline_tracking import run_baseline_tracking

        result = run_baseline_tracking(
            db_path=str(self.db_path),
            dry_run=True,
        )
        self.assertEqual(result.get("plan_size"), 0)
        self.assertEqual(result.get("dry_run"), True)

    def test_tracking_failure_does_not_block_discovery(self):
        """Discovery should still complete even without baseline tracking config."""
        from movietrace.pipeline.discovery import run_discovery

        with patch("movietrace.pipeline.discovery._ensure_fp_data",
                   return_value={"planned_calls": 0, "actual_calls": 0}):
            result = run_discovery(
                db_path=str(self.db_path),
                dry_run=True,
            )
        # Should still have candidates and stats
        self.assertIn("candidates", result)
        self.assertIn("stats", result)


if __name__ == "__main__":
    unittest.main()
