from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentEvaluationGateContractTest(unittest.TestCase):
    def test_release_is_blocked_when_required_evaluation_gate_fails(self) -> None:
        model_id = _seed_model()
        experiment_id = _seed_failed_experiment()
        with TestClient(app) as client:
            agent_response = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Agent Eval Gate {time.time_ns()}",
                    "systemPrompt": "gate release",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 512,
                    "maxContextTurns": 4,
                    "toolIds": [],
                    "evaluationGate": {
                        "enabled": True,
                        "experimentId": experiment_id,
                        "requiredPassRate": 0.8,
                    },
                },
            )
            self.assertEqual(agent_response.status_code, 200)
            agent = agent_response.json()["data"]
            version = client.post(f"/api/v1/agents/{agent['id']}/versions", json={"name": "candidate"}).json()["data"]

            release_response = client.put(f"/api/v1/agents/{agent['id']}/versions/{version['id']}/release", json={})
            self.assertEqual(release_response.status_code, 400)
            self.assertIn("Evaluation gate failed", release_response.json()["message"])


if __name__ == "__main__":
    unittest.main()


def _seed_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Agent Eval Provider {time.time_ns()}",
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
                name="Agent Eval Model",
                model_id="agent-eval-model",
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


def _seed_failed_experiment() -> int:
    initialise_database()
    register_baseline_tables()
    eval_set = Base.metadata.tables["eval_set"]
    experiment = Base.metadata.tables["evaluation_experiment"]
    run = Base.metadata.tables["evaluation_run"]
    now = datetime.now()
    with get_session_factory()() as session:
        eval_set_id = session.execute(
            eval_set.insert().values(name=f"Gate Eval Set {time.time_ns()}", description="", deleted=False, created_at=now, updated_at=now)
        ).inserted_primary_key[0]
        experiment_id = session.execute(
            experiment.insert().values(
                name=f"Gate Experiment {time.time_ns()}",
                target_type="AGENT",
                target_id=0,
                eval_set_id=eval_set_id,
                evaluator_ids=[],
                status="COMPLETED",
                latest_run_id=None,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        run_id = session.execute(
            run.insert().values(
                experiment_id=experiment_id,
                status="FAILED",
                total_cases=2,
                passed_cases=1,
                failed_cases=1,
                aggregate_score=0.5,
                pass_rate=0.5,
                started_at=now,
                finished_at=now,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.execute(experiment.update().where(experiment.c.id == experiment_id).values(latest_run_id=run_id))
        session.commit()
    return int(experiment_id)
