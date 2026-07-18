from collections.abc import Generator
import os
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.runtime.composition import build_runtime_job_worker
from tests.support.mysql import Mysql8TestDatabase


def test_async_message_persists_job_for_a_standalone_worker_after_api_exit() -> None:
    database = Mysql8TestDatabase("ai_assistant_durable_job_gateway")
    database.__enter__()
    database.create_all()
    workspace = tempfile.TemporaryDirectory()
    previous_workspace = os.environ.get("HIFY_WORKSPACE_ROOT")
    os.environ["HIFY_WORKSPACE_ROOT"] = workspace.name

    def session_override() -> Generator[Session, None, None]:
        with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    app.state.ai_assistant_autonomous_worker_enabled = False
    try:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Durable gateway"},
            ).json()["data"]["id"]
            response = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "complete outside the API process",
                    "idempotencyKey": "durable-gateway-1",
                },
            )
            run_id = int(response.json()["data"]["runId"])

        with database.session_factory() as session:
            job = RuntimeJobRepository(session).get_by_run(
                run_id,
                owner_type="AI_ASSISTANT",
                job_type="ai_assistant_run",
            )
            assert job is not None
            assert job["status"] == "QUEUED"
            assert job["owner_id"] == session_id
            assert job["payload"] == {
                "runRef": f"ai-assistant-run:{run_id}",
            }

            completed = build_runtime_job_worker(
                session,
                owner="ai-assistant",
                worker_id="standalone-after-api-exit",
            ).run_once(job_id=int(job["id"]))

            assert completed["status"] == "COMPLETED"
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.state.ai_assistant_autonomous_worker_enabled = True
        database.__exit__(None, None, None)
        workspace.cleanup()
        if previous_workspace is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = previous_workspace


def test_async_idempotency_reuses_one_durable_job() -> None:
    database = Mysql8TestDatabase("ai_assistant_durable_job_idempotency")
    database.__enter__()
    database.create_all()

    def session_override() -> Generator[Session, None, None]:
        with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    app.state.ai_assistant_autonomous_worker_enabled = False
    try:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Durable idempotency"},
            ).json()["data"]["id"]
            payload = {
                "message": "enqueue once",
                "idempotencyKey": "durable-gateway-replay",
            }
            first = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json=payload,
            ).json()["data"]
            second = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json=payload,
            ).json()["data"]

        assert first["runId"] == second["runId"]
        with database.session_factory() as session:
            rows, total = RuntimeJobRepository(session).list_jobs(
                page=1,
                page_size=10,
                owner_type="AI_ASSISTANT",
            )
            assert total == 1
            assert rows[0]["runId"] == first["runId"]
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.state.ai_assistant_autonomous_worker_enabled = True
        database.__exit__(None, None, None)


def test_queue_backpressure_is_bounded_and_idempotent_retry_repairs_missing_job() -> None:
    database = Mysql8TestDatabase("ai_assistant_durable_job_backpressure")
    database.__enter__()
    database.create_all()
    workspace = tempfile.TemporaryDirectory()
    previous_workspace = os.environ.get("HIFY_WORKSPACE_ROOT")
    os.environ["HIFY_WORKSPACE_ROOT"] = workspace.name

    def session_override() -> Generator[Session, None, None]:
        with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        ai_assistant_runtime_active_job_limit=1,
    )
    try:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Bounded durable queue"},
            ).json()["data"]["id"]
            first = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "occupy queue capacity",
                    "idempotencyKey": "durable-backpressure-first",
                },
            )
            second_request = {
                "message": "retry after capacity returns",
                "idempotencyKey": "durable-backpressure-second",
            }
            rejected = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json=second_request,
            )
            rejected_run_id = int(
                client.get(
                    f"/api/v1/ai-assistant/sessions/{session_id}/runs"
                ).json()["data"]["list"][0]["id"]
            )

        assert first.status_code == 200
        assert rejected.status_code == 429
        with database.session_factory() as session:
            repository = RuntimeJobRepository(session)
            first_job = repository.get_by_run(
                int(first.json()["data"]["runId"]),
                owner_type="AI_ASSISTANT",
                job_type="ai_assistant_run",
            )
            assert first_job is not None
            assert repository.get_by_run(
                rejected_run_id,
                owner_type="AI_ASSISTANT",
                job_type="ai_assistant_run",
            ) is None
            assert build_runtime_job_worker(
                session,
                owner="ai-assistant",
                worker_id="backpressure-release-worker",
            ).run_once(job_id=int(first_job["id"]))["status"] == "COMPLETED"

        with TestClient(app) as client:
            repaired = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json=second_request,
            )

        assert repaired.status_code == 200
        assert int(repaired.json()["data"]["runId"]) == rejected_run_id
        with database.session_factory() as session:
            repaired_job = RuntimeJobRepository(session).get_by_run(
                rejected_run_id,
                owner_type="AI_ASSISTANT",
                job_type="ai_assistant_run",
            )
            assert repaired_job is not None
            assert repaired_job["status"] == "QUEUED"
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        database.__exit__(None, None, None)
        workspace.cleanup()
        if previous_workspace is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = previous_workspace
