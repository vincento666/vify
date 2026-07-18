from unittest.mock import Mock, patch

from app.modules.ai_assistant.runtime_job_worker import register_ai_assistant_runtime_job_handler
from app.modules.runtime.domain.runtime_job_registry import RuntimeJobHandlerRegistry


def test_ai_assistant_registers_standalone_runtime_job_handler() -> None:
    registry = RuntimeJobHandlerRegistry()
    session = Mock()

    with patch(
        "app.modules.ai_assistant.runtime_job_worker.complete_ai_assistant_runtime_job"
    ) as complete:
        register_ai_assistant_runtime_job_handler(registry, session)
        job = {"owner_type": "AI_ASSISTANT", "owner_id": 7, "run_id": 42}
        registry.handle(job)

    assert registry.owner_types == ("AI_ASSISTANT",)
    complete.assert_called_once_with(session, job, settings=None)
