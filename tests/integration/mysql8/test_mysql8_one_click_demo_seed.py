import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MYSQL8_TEST_DATABASE_URL = os.getenv("HIFY_MYSQL8_TEST_DATABASE_URL")
PROJECT_ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(MYSQL8_TEST_DATABASE_URL, "set HIFY_MYSQL8_TEST_DATABASE_URL for MySQL8 one-click demo seed")
class Mysql8OneClickDemoSeedTest(unittest.TestCase):
    def test_one_click_seed_command_records_mysql8_persistence_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.demo"
            report_path = Path(tmp) / "one-click-mysql8-report.json"
            env_path.write_text("EXISTING=value\nOPENROUTER_API_KEY=sk-keep-out\n", encoding="utf-8")
            env = {
                **os.environ,
                "PYTHONPATH": str(PROJECT_ROOT),
                "HIFY_DATABASE_URL": str(MYSQL8_TEST_DATABASE_URL),
                "HIFY_ONE_CLICK_DEMO_ENV_PATH": str(env_path),
                "HIFY_ONE_CLICK_DEMO_REPORT_PATH": str(report_path),
            }

            completed = subprocess.run(
                [sys.executable, "scripts/seed_one_click_mvp_demo.py"],
                cwd=PROJECT_ROOT,
                env=env,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn("sk-", completed.stdout)
            manifest = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["verification"]["ok"], manifest)
            self.assertEqual(manifest["persistence"]["dialect"], "mysql")
            self.assertEqual(manifest["persistence"]["databaseUrlKind"], "mysql")
            self.assertTrue(manifest["persistence"]["mysql8LiveRoundTrip"])
            self.assertEqual(manifest["persistence"]["topologyCounts"]["storyCount"], 3)
            self.assertGreaterEqual(manifest["persistence"]["topologyCounts"]["chatflowBindingCount"], 15)
            self.assertGreaterEqual(manifest["persistence"]["topologyCounts"]["knowledgeBaseCount"], 1)
            self.assertGreaterEqual(manifest["persistence"]["topologyCounts"]["customerSessionCount"], 3)
            self.assertGreaterEqual(manifest["persistence"]["topologyCounts"]["providerModelCount"], 1)
            self.assertNotIn("password", json.dumps(manifest["persistence"]).lower())
            self.assertNotIn("sk-", json.dumps(manifest["persistence"]))


if __name__ == "__main__":
    unittest.main()
