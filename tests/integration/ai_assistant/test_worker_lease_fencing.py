from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa

from app.modules.ai_assistant.domain.access_scope import local_ai_assistant_scope
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tool_runtime import ToolRunner
from app.modules.ai_assistant.domain.tools import (
    RiskLevel,
    ToolManifest,
    ToolRegistry,
    ToolResult,
)
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.infra.runtime_job_lease import RuntimeJobLeaseGuard
from app.modules.ai_assistant.runtime_job_worker import AI_ASSISTANT_RUNTIME_JOB_TYPE
from app.modules.runtime.domain.runtime_job_worker import RuntimeJobLeaseLost
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_late_worker_cannot_append_event_after_lease_takeover() -> None:
    with mysql8_session("ai_assistant_worker_lease_fencing") as session:
        owner_repository = AiAssistantRepository(session)
        service = AiAssistantHarnessService(owner_repository)
        assistant_session = service.create_session(title="Lease fencing")
        session_id = int(assistant_session["id"])
        started = service.start_message(
            session_id=session_id,
            message="fence late writes",
            idempotency_key="lease-fencing",
        )
        run_id = int(started.run["id"])
        service.queue_started_message(
            session_id=session_id,
            run_id=run_id,
            message="fence late writes",
        )
        job_repository = RuntimeJobRepository(session)
        job = job_repository.enqueue(
            run_id=run_id,
            owner_type="AI_ASSISTANT",
            owner_id=session_id,
            job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            payload={"runRef": f"ai-assistant-run:{run_id}"},
        )
        claimed = job_repository.claim(
            int(job["id"]),
            worker_id="late-worker",
            lease_seconds=30,
            owner_types=("AI_ASSISTANT",),
        )
        assert claimed is not None
        late_repository = AiAssistantRepository(
            session,
            access_scope=local_ai_assistant_scope(),
            write_guard=RuntimeJobLeaseGuard(
                session,
                job_id=int(job["id"]),
                worker_id="late-worker",
                lease_fence=str(claimed["lease_token"]),
            ),
        )

        runtime_job = sa.Table(
            "runtime_jobs",
            sa.MetaData(),
            autoload_with=session.get_bind(),
        )
        session.execute(
            runtime_job.update()
            .where(runtime_job.c.id == int(job["id"]))
            .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
        )
        session.commit()
        takeover = job_repository.claim(
            int(job["id"]),
            worker_id="takeover-worker",
            lease_seconds=30,
            owner_types=("AI_ASSISTANT",),
        )
        assert takeover is not None

        with pytest.raises(RuntimeJobLeaseLost):
            job_repository.heartbeat(
                int(job["id"]),
                worker_id="late-worker",
                lease_seconds=30,
                lease_token=str(claimed["lease_token"]),
            )
        with pytest.raises(RuntimeJobLeaseLost):
            job_repository.complete(
                int(job["id"]),
                worker_id="late-worker",
                lease_token=str(claimed["lease_token"]),
            )
        with pytest.raises(RuntimeJobLeaseLost):
            late_repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="late.write",
                visible_title="Late write",
                visible_summary="Must be fenced.",
            )

        dispatches: list[dict[str, object]] = []
        registry = ToolRegistry(
            {
                "fenced_tool": (
                    ToolManifest(
                        name="fenced_tool",
                        description="Must not dispatch after lease takeover.",
                        input_schema={"type": "object"},
                        output_schema={"type": "object"},
                        timeout_ms=100,
                        risk_level=RiskLevel.READ,
                        read_resources=[],
                        write_resources=[],
                        policy_ref="test_only",
                    ),
                    lambda payload: (
                        dispatches.append(payload)
                        or ToolResult(status="COMPLETED", output={"dispatched": True})
                    ),
                )
            }
        )
        with pytest.raises(RuntimeJobLeaseLost):
            ToolRunner(
                registry,
                execution_guard=late_repository.write_guard,
            ).run("fenced_tool", {})

        assert dispatches == []
        assert "late.write" not in {
            event["type"]
            for event in owner_repository.list_run_events(run_id)
        }
