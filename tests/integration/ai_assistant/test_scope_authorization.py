from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.infra.schema import (
    ai_assistant_tables,
    register_ai_assistant_tables,
)
from app.core.database import Base
from tests.support.mysql import mysql8_session


def test_dependent_run_resources_are_hidden_from_another_access_scope() -> None:
    with mysql8_session(
        "ai_assistant_scope_authorization",
        tables=ai_assistant_tables(),
        register=register_ai_assistant_tables,
    ) as session:
        owner = AiAssistantRepository(
            session,
            access_scope=AiAssistantAccessScope(
                tenant_id="tenant-a",
                user_id="owner",
                workspace_id="workspace-a",
            ),
        )
        assistant_session = owner.create_session(title="Scoped resources")
        run = owner.create_run(
            session_id=assistant_session["id"],
            user_message="Keep child resources scoped",
            idempotency_key="scoped-resources",
        )
        owner.append_event(
            run_id=run["id"],
            session_id=assistant_session["id"],
            event_type="run.started",
            visible_title="Run started",
            visible_summary="Scoped event.",
        )
        owner.record_tool_call(
            run_id=run["id"],
            session_id=assistant_session["id"],
            tool_name="echo_context",
            input_payload={},
            output_payload={},
            status="COMPLETED",
            duration_ms=1,
        )
        owner.create_tool_operation(
            operation_id="scope-operation",
            session_id=int(assistant_session["id"]),
            run_id=int(run["id"]),
            plan_step_id="scope-step",
            tool_name="echo_context",
            effect_class="READ_ONLY",
            idempotency_key=None,
            request_hash="scope-request",
        )
        owner.create_tool_attempt(
            operation_id="scope-operation",
            attempt_id="scope-attempt",
            adapter_name="local",
            status="COMPLETED",
            request_hash="scope-attempt-request",
        )
        approval = owner.create_approval(
            run_id=int(run["id"]),
            session_id=int(assistant_session["id"]),
            tool_name="update_customer_profile",
            risk_level="BUSINESS_WRITE",
            input_payload={"customerId": "C-scope"},
        )
        owner.create_proposed_action(
            run_id=int(run["id"]),
            session_id=int(assistant_session["id"]),
            approval_id=int(approval["id"]),
            action_type="customer.profile.update",
            title="Update customer",
            payload={"customerId": "C-scope"},
        )

        foreign = AiAssistantRepository(
            session,
            access_scope=AiAssistantAccessScope(
                tenant_id="tenant-b",
                user_id="owner",
                workspace_id="workspace-a",
            ),
        )

        assert foreign.list_run_events(int(run["id"])) == []
        assert foreign.list_run_tool_calls(int(run["id"])) == []
        assert foreign.list_run_tool_operations(int(run["id"])) == []
        assert foreign.get_tool_operation("scope-operation") is None
        assert foreign.list_tool_attempts("scope-operation") == []
        assert (
            foreign.cancel_pending_approvals_for_run(
                int(run["id"]),
                "foreign-operator",
            )
            == 0
        )
        assert foreign.cancel_pending_proposed_actions_for_run(int(run["id"])) == 0
        assert len(owner.list_pending_approvals()) == 1
        proposed_action_table = Base.metadata.tables["ai_assistant_proposed_action"]
        proposed_status = session.execute(
            proposed_action_table.select().where(
                proposed_action_table.c.run_id == int(run["id"])
            )
        ).mappings().one()["status"]
        assert proposed_status == "PENDING"
