from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class LlmJudgeEvaluatorTest(unittest.TestCase):
    def test_llm_judge_evaluator_uses_model_config_and_returns_score(self) -> None:
        model_config_id = _seed_mock_model()

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/evaluators",
                json={
                    "name": f"LLM Judge {time.time_ns()}",
                    "type": "LLM_JUDGE",
                    "config": {
                        "modelConfigId": model_config_id,
                        "rubric": "Pass when actual output preserves the expected answer.",
                        "passingScore": 0.7,
                    },
                },
            )
            self.assertEqual(create_response.status_code, 200)
            evaluator = create_response.json()["data"]

            sample_response = client.post(
                f"/api/v1/evaluators/{evaluator['id']}/test",
                json={
                    "expectedOutput": "refund policy",
                    "actualOutput": "refund policy",
                },
            )
            self.assertEqual(sample_response.status_code, 200)
            result = sample_response.json()["data"]
            self.assertTrue(result["passed"])
            self.assertEqual(result["score"], 1.0)
            self.assertIn("mock judge", result["reason"])

    def test_llm_judge_requires_model_config(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/evaluators/test",
                json={
                    "type": "LLM_JUDGE",
                    "config": {"rubric": "Judge correctness."},
                    "expectedOutput": "ok",
                    "actualOutput": "ok",
                },
            )
            self.assertEqual(response.status_code, 400)


def _seed_mock_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"LLM Judge Provider {time.time_ns()}",
                type="OPENAI",
                base_url="mock://success",
                auth_config={"api_key": "sk-test"},
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="LLM Judge Mock Model",
                model_id="mock-judge-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)


if __name__ == "__main__":
    unittest.main()
