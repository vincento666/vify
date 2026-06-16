import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.core.config import get_settings
from app.core.database import get_session_factory, initialise_database
from app.modules.demo.mvp_seed import MVP_DEMO_HOST_CONTEXT, seed_mvp_demo, verify_mvp_demo_topology


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_STORIES = {
    "refund_baggage_parallel",
    "invoice_interrupt_flight_status",
    "chatflow_block_resume_recommendation",
}


class MvpDemoBootstrapContractTest(unittest.TestCase):
    def test_seed_command_runs_verification_and_writes_secret_free_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "mvp-demo.db"
            env_path = Path(tmp) / ".env.demo"
            env_path.write_text("OPENROUTER_API_KEY=sk-should-not-survive\nEXISTING=value\n", encoding="utf-8")
            env = {
                **os.environ,
                "PYTHONPATH": str(PROJECT_ROOT),
                "HIFY_DATABASE_URL": f"sqlite:///{db_path}",
                "HIFY_MVP_DEMO_ENV_PATH": str(env_path),
            }

            completed = subprocess.run(
                [sys.executable, "scripts/seed_mvp_demo.py"],
                cwd=PROJECT_ROOT,
                env=env,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Verification: passed", completed.stdout)
            self.assertIn("Story coverage: 3/3", completed.stdout)
            self.assertNotIn("sk-", completed.stdout)
            env_text = env_path.read_text(encoding="utf-8")
            self.assertIn("EXISTING=value", env_text)
            self.assertNotIn("OPENROUTER_API_KEY", env_text)
            self.assertNotIn("sk-", env_text)
            self.assertIn("HIFY_MVP_DEMO_HOST_CONTEXT_JSON=", env_text)

            _reset_database_url(env["HIFY_DATABASE_URL"])
            with get_session_factory()() as session:
                report = verify_mvp_demo_topology(session, env_text=env_text)
            self.assertTrue(report["ok"], report)
            self.assertEqual(set(report["storyIds"]), EXPECTED_STORIES)
            self.assertEqual(report["storyCoverage"]["covered"], 3)
            self.assertGreaterEqual(report["chatflowBindings"]["count"], 15)
            self.assertGreaterEqual(report["knowledge"]["faqCount"], 3)
            self.assertTrue(report["security"]["secretFreeEnv"])
            self.assertEqual(report["hostContext"]["tenantId"], MVP_DEMO_HOST_CONTEXT["tenantId"])
            self.assertTrue(report["hostContext"]["envConfigured"])

    def test_reusable_verifier_reports_story_task_action_and_knowledge_contract(self) -> None:
        with _temp_database():
            with get_session_factory()() as session:
                seed = seed_mvp_demo(session)
                report = verify_mvp_demo_topology(session)

            self.assertTrue(report["ok"], report)
            self.assertEqual(set(report["storyIds"]), EXPECTED_STORIES)
            self.assertEqual(report["storyCoverage"]["covered"], len(seed.story_ids))
            for story_id in seed.story_ids:
                story = report["stories"][story_id]
                self.assertGreaterEqual(story["taskCount"], 1)
                self.assertGreaterEqual(story["eventCount"], 1)
                self.assertEqual(story["hostTenantId"], MVP_DEMO_HOST_CONTEXT["tenantId"])
                if story_id in {"refund_baggage_parallel", "invoice_interrupt_flight_status", "chatflow_block_resume_recommendation"}:
                    self.assertGreaterEqual(story["pendingActionCount"], 1)
            self.assertIn("退票", report["knowledge"]["keywords"])
            self.assertIn("航班动态", report["knowledge"]["keywords"])
            self.assertIn("恢复", report["knowledge"]["keywords"])


class _temp_database:
    def __enter__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._previous_url = os.environ.get("HIFY_DATABASE_URL")
        _reset_database_url(f"sqlite:///{Path(self._tmp.name) / 'seed.db'}")

    def __exit__(self, *_exc: object) -> None:
        if self._previous_url is None:
            os.environ.pop("HIFY_DATABASE_URL", None)
        else:
            os.environ["HIFY_DATABASE_URL"] = self._previous_url
        get_settings.cache_clear()
        self._tmp.cleanup()


def _reset_database_url(url: str) -> None:
    os.environ["HIFY_DATABASE_URL"] = url
    get_settings.cache_clear()
    initialise_database()
