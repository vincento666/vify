from app.core.host.context import RequestContext
from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.infra.schema import (
    ai_assistant_tables,
    register_ai_assistant_tables,
)
from app.modules.ai_assistant.web.router import _action_actor_audit
from tests.support.mysql import mysql8_session


def test_approval_audit_persists_server_principal_and_ignored_body_actor() -> None:
    context = RequestContext(
        actor_id="trusted-operator",
        tenant_id="trusted-tenant",
        org_id="trusted-org",
        request_id="approval-audit-request",
        source="trusted-auth-adapter",
    )
    with mysql8_session(
        "ai_assistant_approval_actor_audit",
        tables=ai_assistant_tables(),
        register=register_ai_assistant_tables,
    ) as session:
        repository = AiAssistantRepository(
            session,
            access_scope=AiAssistantAccessScope(
                tenant_id=context.tenant_id,
                user_id=context.actor_id,
                workspace_id="workspace-a",
            ),
        )
        service = AiAssistantHarnessService(
            repository,
            tool_registry=ToolRegistry.with_demo_tools(),
        )
        assistant_session = service.create_session(title="Approval actor audit")
        waiting = service.run_message(
            int(assistant_session["id"]),
            "update customer profile",
            idempotency_key="approval-actor-audit",
            approval_mode="ask_each_time",
            tool_name="update_customer_profile",
            tool_input={"customerId": "C-actor"},
        )
        assert waiting.approval_id is not None
        actor_audit = _action_actor_audit(context, "spoofed-body-actor")

        service.approve(
            waiting.approval_id,
            str(actor_audit["actorId"]),
            actor_audit=actor_audit,
        )

        approval_event = next(
            event
            for event in repository.list_run_events(int(waiting.run["id"]))
            if event["type"] == "approval.granted"
        )
        assert approval_event["payload"]["actorAudit"]["actorId"] == "trusted-operator"
        assert approval_event["payload"]["actorAudit"]["tenantId"] == "trusted-tenant"
        assert approval_event["payload"]["legacyActorIdField"] == "ignored_mismatch"
