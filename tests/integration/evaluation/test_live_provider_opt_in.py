from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import time

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


@dataclass(frozen=True)
class LiveLlmConfig:
    base_url: str
    api_key: str
    model: str


def test_live_llm_debug_uses_real_provider_when_opted_in() -> None:
    config = _live_config()
    model_config_id = _seed_live_model(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/evaluators/llm-debug",
            json={
                "modelConfigId": model_config_id,
                "prompt": "Pass only when the actual output preserves the exact expected answer. Return JSON only.",
                "expectedOutput": "refund policy",
                "actualOutput": "refund policy",
                "passingScore": 0.7,
            },
        )

    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["passed"] is True
    assert float(result["score"]) >= 0.7
    assert result["reason"]
    assert result["rawOutput"]
    assert "mock judge" not in result["rawOutput"].lower()
    assert "mock judge" not in result["reason"].lower()


def test_live_llm_judge_runs_inside_experiment_when_opted_in() -> None:
    config = _live_config()
    model_config_id = _seed_live_model(config)

    with TestClient(app) as client:
        workflow = _unwrap(
            client.post(
                "/api/v1/workflows",
                json={
                    "name": f"020.8 Live LLM Workflow {time.time_ns()}",
                    "description": "echo target for live evaluator",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["userMessage"]}},
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {"output": "{{start.userMessage}}", "outputVariable": "output"},
                        },
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            ),
            "create workflow",
        )
        eval_set = _unwrap(
            client.post(
                "/api/v1/eval-sets",
                json={"name": f"020.8 Live LLM Eval Set {time.time_ns()}", "description": "live llm judge"},
            ),
            "create eval set",
        )
        _unwrap(
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={"input": "refund policy", "expectedOutput": "refund policy", "tags": ["live-llm"]},
            ),
            "create case",
        )
        evaluator = _unwrap(
            client.post(
                "/api/v1/evaluators",
                json={
                    "name": f"020.8 Live LLM Judge {time.time_ns()}",
                    "type": "LLM_JUDGE",
                    "config": {
                        "modelConfigId": model_config_id,
                        "rubric": "Pass when actual output preserves expected output. Return JSON only.",
                        "passingScore": 0.7,
                    },
                },
            ),
            "create evaluator",
        )
        experiment = _unwrap(
            client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"020.8 Live LLM Experiment {time.time_ns()}",
                    "targetType": "WORKFLOW",
                    "targetId": workflow["id"],
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                    "evaluatorVersionIds": [],
                    "targetFieldMapping": {"userMessage": "input"},
                    "evaluatorFieldMapping": {"expectedOutput": "expectedOutput", "actualOutput": "__target.output"},
                    "itemConcurrency": 1,
                    "itemRetryCount": 0,
                },
            ),
            "create experiment",
        )
        run = _unwrap(client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs"), "run experiment")

    assert run["status"] == "COMPLETED"
    assert run["totalCases"] == 1
    assert run["passedCases"] == 1
    assert run["caseResults"]
    evaluator_result = run["caseResults"][0]["evaluatorResults"][0]
    assert evaluator_result["type"] == "LLM_JUDGE"
    assert evaluator_result["score"] >= 0.7
    assert "mock judge" not in evaluator_result["reason"].lower()


def _live_config() -> LiveLlmConfig:
    if os.getenv("HIFY_LIVE_LLM_EVAL") != "1":
        pytest.skip("Set HIFY_LIVE_LLM_EVAL=1 to run live provider validation.")
    missing = [
        name
        for name in ("HIFY_LIVE_LLM_BASE_URL", "HIFY_LIVE_LLM_API_KEY", "HIFY_LIVE_LLM_MODEL")
        if not os.getenv(name)
    ]
    if missing:
        pytest.fail(f"Missing live LLM env vars: {', '.join(missing)}")
    return LiveLlmConfig(
        base_url=str(os.environ["HIFY_LIVE_LLM_BASE_URL"]),
        api_key=str(os.environ["HIFY_LIVE_LLM_API_KEY"]),
        model=str(os.environ["HIFY_LIVE_LLM_MODEL"]),
    )


def _seed_live_model(config: LiveLlmConfig) -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"020.8 Live Provider {time.time_ns()}",
                type="OPENAI",
                base_url=config.base_url,
                auth_config={"api_key": config.api_key},
                description="020.8 live LLM gate",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name=f"020.8 Live Model {config.model}",
                model_id=config.model,
                context_size=8192,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)


def _unwrap(response, label: str) -> dict:
    assert response.status_code == 200, f"{label} HTTP {response.status_code}: {response.text}"
    payload = response.json()
    assert payload["code"] == 200, f"{label} API {payload['message']}"
    return payload["data"]
