import json
import tempfile
import unittest
from pathlib import Path


class HeartbeatTest(unittest.TestCase):
    def test_ping_writes_json(self):
        from movietrace.pipeline.heartbeat import ping

        with tempfile.TemporaryDirectory() as tmpdir:
            hb_path = Path(tmpdir) / "heartbeat.json"
            ping("1/8 test", "detail", hb_path=str(hb_path))

            data = json.loads(hb_path.read_text())
            self.assertEqual(data["step"], "1/8 test")
            self.assertEqual(data["detail"], "detail")
            self.assertEqual(data["status"], "running")
            self.assertIn("ts", data)
            self.assertIn("pid", data)

    def test_done_updates_status(self):
        from movietrace.pipeline.heartbeat import done, ping

        with tempfile.TemporaryDirectory() as tmpdir:
            hb_path = Path(tmpdir) / "heartbeat.json"
            ping("1/8 test", hb_path=str(hb_path))
            done(hb_path=str(hb_path))

            data = json.loads(hb_path.read_text())
            self.assertEqual(data["status"], "done")

    def test_ping_silent_on_write_failure(self):
        from movietrace.pipeline.heartbeat import ping

        with tempfile.TemporaryDirectory() as tmpdir:
            hb_path = Path(tmpdir) / "missing" / "heartbeat.json"
            ping("1/8 test", hb_path=str(hb_path))

    def test_ping_overwrites_previous(self):
        from movietrace.pipeline.heartbeat import ping

        with tempfile.TemporaryDirectory() as tmpdir:
            hb_path = Path(tmpdir) / "heartbeat.json"
            ping("1/8 first", "old", hb_path=str(hb_path))
            ping("2/8 second", "new", hb_path=str(hb_path))

            data = json.loads(hb_path.read_text())
            self.assertEqual(data["step"], "2/8 second")
            self.assertEqual(data["detail"], "new")


if __name__ == "__main__":
    unittest.main()
