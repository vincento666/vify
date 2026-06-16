import os
import tempfile
import unittest
from pathlib import Path

import sqlalchemy as sa

from app.core.config import get_settings
from app.core.database import Base, get_session_factory, initialise_database
from app.modules.runtime_lab.infra.airline_chatflow_seed import (
    AIRLINE_CHATFLOW_SOP_IDS,
    seed_runtime_lab_airline_chatflows,
    seed_runtime_lab_live_agent,
    write_runtime_lab_env,
)
from app.modules.workflow.infra.repository import WorkflowRepository


class RuntimeLabAirlineChatflowSeedTest(unittest.TestCase):
    def test_seed_creates_fifteen_chatflow_sop_bindings_and_is_idempotent(self) -> None:
        with _temp_database():
            with get_session_factory()() as session:
                first = seed_runtime_lab_airline_chatflows(session)
                second = seed_runtime_lab_airline_chatflows(session)
                agent_id = seed_runtime_lab_live_agent(session, api_key="sk-test-runtime-lab")
                repository = WorkflowRepository(session)
                model_config = Base.metadata.tables["model_config"]
                runtime_model = session.execute(
                    sa.select(model_config.c.extra_params).where(model_config.c.name == "034 RuntimeLab Airline qwen")
                ).mappings().first()

                self.assertEqual(tuple(first.keys()), AIRLINE_CHATFLOW_SOP_IDS)
                self.assertEqual(second, first)
                self.assertEqual(len(first), 15)
                self.assertGreater(agent_id, 0)
                self.assertIsNotNone(runtime_model)
                self.assertEqual(runtime_model["extra_params"]["fallbackModel"], "deepseek/deepseek-v4-flash")

                for sop_id, chatflow_id in first.items():
                    workflow = repository.get(chatflow_id, flow_type="CHATFLOW")
                    nodes = repository.list_nodes(chatflow_id)
                    self.assertIsNotNone(workflow, sop_id)
                    self.assertIn("034 RuntimeLab Airline SOP", str(workflow["name"]))
                    self.assertGreaterEqual(len(nodes), 6)
                    self.assertTrue(any(node["type"] == "INFORMATION_COLLECTION" for node in nodes), sop_id)
                    self.assertTrue(any(node["type"] == "LLM" for node in nodes), sop_id)
                    self.assertTrue(any(node["type"] == "QUESTION" for node in nodes), sop_id)
                    collect_node = next(node for node in nodes if node["type"] == "INFORMATION_COLLECTION")
                    followup_template = str(collect_node["config"].get("followupTemplate") or "")
                    self.assertIs(collect_node["config"].get("includeHistory"), True, sop_id)
                    self.assertIn("{{missing_labels}}", followup_template, sop_id)
                    self.assertIn("{{collected_notice}}", followup_template, sop_id)
                    self.assertIn("当前只差", followup_template, sop_id)
                    for field in collect_node["config"]["fields"]:
                        self.assertEqual(field["targetScope"], "conversation", f"{sop_id}.{field['name']}")
                        self.assertEqual(field["targetVariable"], field["name"], f"{sop_id}.{field['name']}")
                    policy_llm_node = next(node for node in nodes if node["type"] == "LLM" and node["node_key"] == "policy_llm")
                    policy_prompt = str(policy_llm_node["config"].get("prompt") or "")
                    self.assertIn("{{conversation.route}}", policy_prompt, sop_id)
                    self.assertIn("{{conversation.order_no}}", policy_prompt, sop_id)
                    if sop_id == "flight_booking":
                        final_llm_node = next(node for node in nodes if node["type"] == "LLM" and node["node_key"] == "final_llm")
                        final_prompt = str(final_llm_node["config"].get("prompt") or "")
                        self.assertIn("订单编号 CA1301-20231027-8899", final_prompt)
                    if sop_id == "change_flight":
                        target_time_field = next(field for field in collect_node["config"]["fields"] if field["name"] == "target_time")
                        self.assertEqual(target_time_field["historyMode"], "current_turn_only")
                        self.assertIn("不要使用原出行时间", target_time_field["extractionHint"])

    def test_env_writer_is_idempotent_and_keeps_secrets_out_of_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("EXISTING=value\nHIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODEL=old\n", encoding="utf-8")

            write_runtime_lab_env(env_path, bindings={"flight_booking": 12, "refund_ticket": 13})
            write_runtime_lab_env(env_path, bindings={"flight_booking": 12, "refund_ticket": 13})

            content = env_path.read_text(encoding="utf-8")
            self.assertEqual(content.count("# RuntimeLab 034 airline Chatflow bindings."), 1)
            self.assertIn("EXISTING=value", content)
            self.assertIn("HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=flight_booking:12,refund_ticket:13", content)
            self.assertIn("HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODEL=qwen/qwen3.5-9b", content)
            self.assertIn("HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_FALLBACK_MODEL=deepseek/deepseek-v4-flash", content)
            self.assertNotIn("API_KEY=", content)
            self.assertNotIn("sk-", content)


class _temp_database:
    def __enter__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._previous_url = os.environ.get("HIFY_DATABASE_URL")
        os.environ["HIFY_DATABASE_URL"] = f"sqlite:///{Path(self._tmp.name) / 'seed.db'}"
        get_settings.cache_clear()
        initialise_database()

    def __exit__(self, *_exc: object) -> None:
        if self._previous_url is None:
            os.environ.pop("HIFY_DATABASE_URL", None)
        else:
            os.environ["HIFY_DATABASE_URL"] = self._previous_url
        get_settings.cache_clear()
        self._tmp.cleanup()
