import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from tests.support.mysql import mysql8_app_database, mysql8_database_url


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class OneClickDemoSeedTest(unittest.TestCase):
    def test_one_click_seed_is_idempotent_and_writes_report_manifest(self) -> None:
        module = importlib.import_module("app.modules.demo.mvp_seed")

        with _temp_database():
            with tempfile.TemporaryDirectory() as tmp:
                env_path = Path(tmp) / ".env.demo"
                report_path = Path(tmp) / "one-click-report.json"
                env_path.write_text("EXISTING=value\nOPENAI_API_KEY=sk-keep-out\n", encoding="utf-8")

                with get_session_factory()() as session:
                    first = module.seed_one_click_mvp_demo(
                        session,
                        env_path=env_path,
                        report_path=report_path,
                    )
                with get_session_factory()() as session:
                    second = module.seed_one_click_mvp_demo(
                        session,
                        env_path=env_path,
                        report_path=report_path,
                    )

                self.assertEqual(second.seed.provider_ids, first.seed.provider_ids)
                self.assertEqual(second.seed.model_config_ids, first.seed.model_config_ids)
                self.assertTrue(second.report["ok"], second.report)
                self.assertGreaterEqual(len(second.seed.provider_ids), 1)
                self.assertGreaterEqual(len(second.seed.model_config_ids), 1)

                env_text = env_path.read_text(encoding="utf-8")
                self.assertIn("EXISTING=value", env_text)
                self.assertIn("HIFY_MVP_DEMO_PROVIDER_IDS=", env_text)
                self.assertIn("HIFY_MVP_DEMO_MODEL_CONFIG_IDS=", env_text)
                self.assertIn("HIFY_MVP_DEMO_SEED_REPORT_PATH=", env_text)
                self.assertNotIn("OPENAI_API_KEY", env_text)
                self.assertNotIn("sk-", env_text)

                manifest = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(manifest["schemaVersion"], "hify.mvp_demo_seed_report/1")
                self.assertEqual(manifest["specId"], "106-one-click-demo-seed")
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
                readiness = manifest["runtimeV2LlmReadiness"]
                self.assertTrue(readiness["workflowRunsV2ProviderBinding"])
                self.assertTrue(readiness["chatflowRunsV2ProviderBinding"])
                self.assertTrue(readiness["runtimeLabSopV2ProviderBinding"])
                self.assertTrue(readiness["customerAssistantSopV2ProviderBinding"])
                self.assertEqual(readiness["providerMode"], "mock_safe")
                self.assertFalse(readiness["liveReady"])
                self.assertTrue(readiness["liveProviderRequired"])
                self.assertEqual(readiness["modelConfigIds"], second.seed.model_config_ids)
                self.assertEqual(readiness["preferredAgentName"], "034 RuntimeLab Airline Chatflow LLM Agent")
                self.assertNotIn("sk-", json.dumps(readiness))
                self.assertEqual(manifest["seed"]["providerIds"], second.seed.provider_ids)
                self.assertEqual(manifest["seed"]["modelConfigIds"], second.seed.model_config_ids)

                provider_id = int(second.seed.provider_ids[0])
                model_config_id = int(second.seed.model_config_ids[0])
                with get_session_factory()() as session:
                    provider = Base.metadata.tables["provider"]
                    model_config = Base.metadata.tables["model_config"]
                    provider_row = session.execute(
                        sa.select(provider).where(provider.c.id == provider_id)
                    ).mappings().one()
                    model_row = session.execute(
                        sa.select(model_config).where(model_config.c.id == model_config_id)
                    ).mappings().one()

                self.assertEqual(provider_row["base_url"], "mock://success")
                self.assertEqual(provider_row["auth_config"], {})
                self.assertEqual(model_row["provider_id"], provider_id)
                self.assertTrue(model_row["enabled"])

    def test_one_click_seed_script_runs_without_secret_output(self) -> None:
        with mysql8_database_url("one_click_seed_script") as database_url:
            with tempfile.TemporaryDirectory() as tmp:
                env_path = Path(tmp) / ".env.demo"
                report_path = Path(tmp) / "report.json"
                env_path.write_text("EXISTING=value\nOPENROUTER_API_KEY=sk-keep-out\n", encoding="utf-8")
                env = {
                    **os.environ,
                    "PYTHONPATH": str(PROJECT_ROOT),
                    "HIFY_DATABASE_URL": database_url,
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
                self.assertIn("Seeded Hify one-click MVP demo:", completed.stdout)
                self.assertIn("Verification: passed", completed.stdout)
                self.assertIn("Provider/model configs:", completed.stdout)
                self.assertNotIn("sk-", completed.stdout)
                self.assertTrue(report_path.exists())


class _temp_database:
    def __enter__(self) -> None:
        self._database = mysql8_app_database("one_click_seed")
        self._database.__enter__()

    def __exit__(self, *_exc: object) -> None:
        self._database.__exit__(*_exc)


if __name__ == "__main__":
    unittest.main()
