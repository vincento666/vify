from datetime import datetime
import json
from json import JSONDecodeError
from time import perf_counter
from typing import Any, Mapping

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.core.errors import BizError, ErrorCode
from app.core.responses import success
from app.modules.agent.infra.repository import AgentRepository
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.runtime_lab.domain.classifier import LlmConstrainedIntentClassifier
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.faq_gate import (
    CompositeFaqAnswerGate,
    FaqAnswerGate,
    FaqExactAnswerGate,
    FaqSemanticAnswerGate,
    RuntimeAirlineFaqGate,
)
from app.modules.runtime_lab.domain.payload import format_event, format_session, format_task
from app.modules.runtime_lab.domain.rag_gate import RagAnswerGate
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.schemas import RuntimeLabFallbackAgentRequest, RuntimeLabMessageRequest
from app.modules.runtime_policy.domain.factories import (
    build_agent_output_policy_from_snapshot,
    build_classifier_from_snapshot,
    build_fallback_agent_from_snapshot,
)
from app.modules.runtime_policy.domain.resolver import RuntimePolicyResolveContext, RuntimePolicyResolver
from app.modules.runtime_policy.domain.service import RuntimeDecisionLogService
from app.modules.runtime_policy.domain.service import RuntimePolicyProfileService
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository

router = APIRouter(prefix="/api/v1/runtime-lab", tags=["runtime-lab"])

RUNTIME_LAB_AIRLINE_LLM_AGENT_NAME = "034 RuntimeLab Airline Chatflow LLM Agent"


def get_runtime_lab_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    settings = get_settings()
    effective_policy = RuntimePolicyResolver(RuntimePolicyRepository(session), settings).resolve()
    policy_snapshot = effective_policy["policySnapshot"]
    bindings = _runtime_lab_chatflow_bindings(settings.runtime_lab_sop_chatflow_ids)
    classifier = build_classifier_from_snapshot(policy_snapshot, settings)
    faq_answer_gate = _runtime_lab_faq_answer_gate(settings, session, policy_snapshot)
    faq_semantic_gate = _runtime_lab_faq_semantic_gate(settings, session, policy_snapshot)
    rag_answer_gate = _runtime_lab_rag_answer_gate(settings, session, policy_snapshot)
    fallback_agent = build_fallback_agent_from_snapshot(policy_snapshot, session=session)
    agent_output_policy = build_agent_output_policy_from_snapshot(policy_snapshot)
    policy_thresholds = dict(policy_snapshot.get("thresholds") or {})
    if not bindings:
        return RuntimeLabService(
            RuntimeLabRepository(session),
            classifier=classifier,
            faq_answer_gate=faq_answer_gate,
            faq_semantic_gate=faq_semantic_gate,
            rag_answer_gate=rag_answer_gate,
            fallback_agent=fallback_agent,
            agent_output_policy=agent_output_policy,
            policy_thresholds=policy_thresholds,
        )
    workflow_service = WorkflowService(
        WorkflowRepository(session),
        flow_type="CHATFLOW",
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        chatflow_state_repository=ChatflowStateRepository(session),
        preferred_llm_agent_name=RUNTIME_LAB_AIRLINE_LLM_AGENT_NAME,
    )
    adapter = ChatflowSopRuntimeAdapter(
        workflow_service,
        sop_chatflow_ids=bindings,
        fallback_adapter=FakeSopRuntimeAdapter(),
    )
    return RuntimeLabService(
        RuntimeLabRepository(session),
        adapter=adapter,
        classifier=classifier,
        faq_answer_gate=faq_answer_gate,
        faq_semantic_gate=faq_semantic_gate,
        rag_answer_gate=rag_answer_gate,
        fallback_agent=fallback_agent,
        agent_output_policy=agent_output_policy,
        policy_thresholds=policy_thresholds,
    )


@router.post("/sessions")
def create_session(service: RuntimeLabService = Depends(get_runtime_lab_service)) -> dict[str, Any]:
    return success(format_session(service.create_session()))


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: int,
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    effective_policy = RuntimePolicyResolver(RuntimePolicyRepository(session), settings).resolve()
    result = service.handle_command(
        session_id,
        request.message,
        request.idempotency_key,
        enabled_sop_ids=request.enabled_sop_ids,
    )
    if not result.replayed:
        RuntimeDecisionLogService(RuntimePolicyRepository(session)).record_message_decision(
            session_id=session_id,
            message_id=request.idempotency_key or "",
            user_message=request.message,
            command_payload=result.payload,
            effective_policy=effective_policy,
        )
    return success(result.payload)


@router.get("/sessions/{session_id}/tasks")
def list_tasks(
    session_id: int,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    tasks = service.list_tasks(session_id)
    return success({"list": [format_task(task) for task in tasks], "total": len(tasks)})


@router.get("/sessions/{session_id}/events")
def list_events(
    session_id: int,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    events = service.list_events(session_id)
    return success({"list": [format_event(event) for event in events], "total": len(events)})


@router.get("/sessions/{session_id}/chatflow-trace")
def get_chatflow_trace(
    session_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return success(_runtime_lab_chatflow_trace(session_id, session))


@router.get("/config")
def get_config(
    tenant_id: str = Query("", alias="tenantId"),
    bot_id: str = Query("", alias="botId"),
    channel: str = "",
    session_id: str = Query("", alias="sessionId"),
    sop_group: str = Query("", alias="sopGroup"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    context = RuntimePolicyResolveContext(
        tenant_id=tenant_id,
        bot_id=bot_id,
        channel=channel,
        session_id=session_id,
        sop_group=sop_group,
    )
    return success(_runtime_lab_config(settings, session, context))


@router.put("/fallback-agent")
def update_fallback_agent(
    request: RuntimeLabFallbackAgentRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return success(_update_runtime_lab_fallback_agent(session, settings, request))


def _runtime_lab_chatflow_bindings(raw: str | None) -> dict[str, int]:
    text = (raw or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except JSONDecodeError:
            return _runtime_lab_chatflow_bindings(text.strip("{}"))
        if not isinstance(parsed, dict):
            return {}
        return {str(key): int(value) for key, value in parsed.items() if str(key).strip()}
    bindings: dict[str, int] = {}
    for item in text.split(","):
        sop_id, _, chatflow_id = item.partition(":")
        if sop_id.strip() and chatflow_id.strip():
            bindings[sop_id.strip()] = int(chatflow_id.strip())
    return bindings


def _runtime_lab_config(
    settings: Settings,
    session: Session,
    context: RuntimePolicyResolveContext | None = None,
) -> dict[str, Any]:
    bindings = _runtime_lab_chatflow_bindings(settings.runtime_lab_sop_chatflow_ids)
    names = _chatflow_names(session, bindings.values())
    effective = RuntimePolicyResolver(RuntimePolicyRepository(session), settings).resolve(context)
    snapshot = effective["policySnapshot"]
    classifier = snapshot["classifier"]
    fallback_agent = dict(snapshot.get("fallbackAgent") or {})
    fallback_agent_options = _runtime_lab_fallback_agent_options(session)
    fallback_agent_by_id = {int(agent["id"]): agent for agent in fallback_agent_options}
    fallback_agent_id = _optional_int_value(fallback_agent.get("agentId"))
    fallback_agent_row = fallback_agent_by_id.get(fallback_agent_id or 0)
    base_url = str(classifier.get("baseUrl") or "").strip()
    fallback_model = str(classifier.get("fallbackModel") or "").strip()
    api_key_configured = bool(str(classifier.get("apiKeyRef") or "").strip())
    mode = str(classifier.get("mode") or "fake").strip().lower()
    model = str(classifier.get("model") or "").strip()
    return {
        "policyProfile": {
            "source": effective["source"],
            "profileId": effective["profileId"],
            "profileVersion": effective["profileVersion"],
        },
        "sopBindings": [
            {
                "sopId": sop_id,
                "chatflowId": chatflow_id,
                "chatflowName": names.get(chatflow_id, ""),
                "exists": chatflow_id in names,
                "canvasPath": f"/chatflows/{chatflow_id}/canvas",
            }
            for sop_id, chatflow_id in bindings.items()
        ],
        "arbitrator": {
            "mode": mode,
            "model": model,
            "fallbackModel": fallback_model,
            "baseUrl": base_url,
            "apiKeyConfigured": api_key_configured,
            "available": (
                mode != "llm"
                or bool(base_url and model and api_key_configured)
            ),
        },
        "faq": {
            "knowledgeBaseIds": list(snapshot["faq"].get("knowledgeBaseIds") or []),
        },
        "rag": {
            "knowledgeBaseIds": list(snapshot["rag"].get("knowledgeBaseIds") or []),
        },
        "fallbackAgent": {
            "enabled": bool(fallback_agent.get("enabled")),
            "type": str(fallback_agent.get("type") or "fake"),
            "agentId": fallback_agent_id,
            "agentName": str(fallback_agent_row.get("name") or "") if fallback_agent_row else "",
            "available": _runtime_lab_fallback_agent_available(fallback_agent, fallback_agent_row),
        },
        "fallbackAgentOptions": fallback_agent_options,
    }


def _update_runtime_lab_fallback_agent(
    session: Session,
    settings: Settings,
    request: RuntimeLabFallbackAgentRequest,
) -> dict[str, Any]:
    repository = RuntimePolicyRepository(session)
    if request.enabled:
        if request.agent_id is None:
            raise BizError(ErrorCode.BAD_REQUEST, "fallback Agent requires agentId")
        agent = AgentRepository(session).get(int(request.agent_id))
        if agent is None or not bool(agent.get("enabled")):
            raise BizError(ErrorCode.NOT_FOUND, "Fallback Agent not found or disabled")
    effective = RuntimePolicyResolver(repository, settings).resolve()
    snapshot = effective["policySnapshot"]
    fallback_agent = dict(snapshot.get("fallbackAgent") or {})
    if request.enabled:
        fallback_agent.update({"enabled": True, "type": "existing_agent", "agentId": int(request.agent_id)})
    else:
        fallback_agent.update({"enabled": False, "type": "fake", "agentId": None})

    service = RuntimePolicyProfileService(repository)
    if effective.get("source") == "profile" and effective.get("profileId"):
        row = repository.get_profile(int(effective["profileId"]))
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        payload = _runtime_policy_payload_from_row(row)
        payload["fallbackAgent"] = fallback_agent
        profile = service.update_profile(
            int(effective["profileId"]),
            RuntimePolicyProfileRequest.model_validate(payload),
        )
    else:
        payload = _runtime_policy_payload_from_snapshot(snapshot, fallback_agent)
        profile = service.create_profile(RuntimePolicyProfileRequest.model_validate(payload))
    selected_config = _runtime_lab_config(settings, session)
    selected_config["updatedProfile"] = {
        "profileId": profile["id"],
        "profileVersion": profile["version"],
    }
    return selected_config


def _runtime_lab_fallback_agent_options(session: Session) -> list[dict[str, Any]]:
    rows, _total = AgentRepository(session).list_page(1, 100, enabled=True)
    return [
        {
            "id": int(row["id"]),
            "name": str(row.get("name") or ""),
            "description": str(row.get("description") or ""),
            "enabled": bool(row.get("enabled")),
        }
        for row in rows
    ]


def _runtime_lab_fallback_agent_available(
    fallback_agent: Mapping[str, Any],
    agent_row: Mapping[str, Any] | None,
) -> bool:
    if not bool(fallback_agent.get("enabled")):
        return False
    fallback_type = str(fallback_agent.get("type") or "fake")
    if fallback_type == "fake":
        return True
    if fallback_type == "existing_agent":
        return agent_row is not None and bool(agent_row.get("enabled"))
    return False


def _runtime_policy_payload_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": str(row.get("name") or "RuntimeLab routing policy"),
        "description": str(row.get("description") or ""),
        "status": str(row.get("status") or "active"),
        "mode": str(row.get("mode") or "balanced"),
        "bindings": dict(row.get("bindings") or {}),
        "thresholds": dict(row.get("thresholds") or {}),
        "classifier": dict(row.get("classifier") or {}),
        "faq": dict(row.get("faq") or {}),
        "rag": dict(row.get("rag") or {}),
        "fallbackAgent": dict(row.get("fallback_agent") or {}),
        "handoff": dict(row.get("handoff") or {}),
        "audit": dict(row.get("audit") or {}),
    }


def _runtime_policy_payload_from_snapshot(
    snapshot: Mapping[str, Any],
    fallback_agent: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "name": "034 RuntimeLab routing policy",
        "description": "RuntimeLab generated policy for unified routing fallback Agent selection",
        "status": "active",
        "mode": str(snapshot.get("mode") or "balanced"),
        "bindings": dict(snapshot.get("bindings") or {}),
        "thresholds": dict(snapshot.get("thresholds") or {}),
        "classifier": _runtime_policy_schema_safe_classifier(snapshot.get("classifier")),
        "faq": dict(snapshot.get("faq") or {}),
        "rag": dict(snapshot.get("rag") or {}),
        "fallbackAgent": dict(fallback_agent),
        "handoff": dict(snapshot.get("handoff") or {}),
        "audit": {
            "createdBy": "runtime-lab",
            "updatedBy": "runtime-lab",
            "changeReason": "Select RuntimeLab fallback Agent",
        },
    }


def _runtime_policy_schema_safe_classifier(value: Any) -> dict[str, Any]:
    classifier = dict(value or {})
    if str(classifier.get("mode") or "").lower() != "llm":
        return classifier
    required = (
        str(classifier.get("baseUrl") or "").strip(),
        str(classifier.get("apiKeyRef") or "").strip(),
        str(classifier.get("model") or "").strip(),
    )
    if all(required):
        return classifier
    classifier["enabled"] = False
    return classifier


def _runtime_lab_faq_answer_gate(
    settings: Settings,
    session: Session,
    policy_snapshot: Mapping[str, Any] | None = None,
) -> FaqAnswerGate | None:
    faq_config = _runtime_policy_faq_config(settings, policy_snapshot)
    if not bool(faq_config.get("exactEnabled", True)):
        return None
    runtime_faq_gate = RuntimeAirlineFaqGate()
    knowledge_base_ids = _runtime_lab_id_list(faq_config.get("knowledgeBaseIds"))
    if not knowledge_base_ids:
        return runtime_faq_gate
    thresholds = dict((policy_snapshot or {}).get("thresholds") or {})
    return CompositeFaqAnswerGate(
        (
            runtime_faq_gate,
            FaqExactAnswerGate(
                KnowledgeFacade(session),
                knowledge_base_ids=knowledge_base_ids,
                top_k=int(faq_config.get("topK") or 3),
                keyword_min_score=_runtime_lab_threshold(thresholds, "faqKeywordMinScore", 0.0),
                keyword_min_margin=_runtime_lab_threshold(thresholds, "faqKeywordMinMargin", 0.0),
            ),
        )
    )


def _runtime_lab_faq_semantic_gate(
    settings: Settings,
    session: Session,
    policy_snapshot: Mapping[str, Any] | None = None,
) -> FaqSemanticAnswerGate | None:
    faq_config = _runtime_policy_faq_config(settings, policy_snapshot)
    if not bool(faq_config.get("semanticEnabled", True)):
        return None
    knowledge_base_ids = _runtime_lab_id_list(faq_config.get("knowledgeBaseIds"))
    if not knowledge_base_ids:
        return None
    thresholds = dict((policy_snapshot or {}).get("thresholds") or {})
    return FaqSemanticAnswerGate(
        KnowledgeFacade(session),
        knowledge_base_ids=knowledge_base_ids,
        top_k=int(faq_config.get("topK") or 5),
        rerank=bool(faq_config.get("rerank", True)),
        min_score=_runtime_lab_threshold(thresholds, "faqSemanticMinScore", 0.85),
        min_margin=_runtime_lab_threshold(thresholds, "faqSemanticMinMargin", 0.12),
    )


def _runtime_lab_rag_answer_gate(
    settings: Settings,
    session: Session,
    policy_snapshot: Mapping[str, Any] | None = None,
) -> RagAnswerGate | None:
    rag_config = _runtime_policy_rag_config(settings, policy_snapshot)
    if not bool(rag_config.get("enabled", True)):
        return None
    knowledge_base_ids = _runtime_lab_id_list(rag_config.get("knowledgeBaseIds"))
    if not knowledge_base_ids:
        return None
    thresholds = dict((policy_snapshot or {}).get("thresholds") or {})
    return RagAnswerGate(
        KnowledgeFacade(session),
        knowledge_base_ids=knowledge_base_ids,
        top_k=int(rag_config.get("topK") or 3),
        retrieval_mode=str(rag_config.get("retrievalMode") or "hybrid"),
        rerank=bool(rag_config.get("rerank", True)),
        min_score=_runtime_lab_threshold(thresholds, "ragMinScore", 0.7),
        lexical_accept_threshold=_runtime_lab_threshold(thresholds, "ragLexicalAcceptThreshold", 0.6),
    )


def _runtime_policy_faq_config(settings: Settings, policy_snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    if policy_snapshot and isinstance(policy_snapshot.get("faq"), Mapping):
        return dict(policy_snapshot["faq"])
    return {
        "knowledgeBaseIds": _runtime_lab_id_list(settings.runtime_lab_faq_knowledge_base_ids),
        "exactEnabled": True,
        "semanticEnabled": True,
        "topK": 3,
        "rerank": False,
    }


def _runtime_policy_rag_config(settings: Settings, policy_snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    if policy_snapshot and isinstance(policy_snapshot.get("rag"), Mapping):
        return dict(policy_snapshot["rag"])
    return {
        "enabled": True,
        "knowledgeBaseIds": _runtime_lab_id_list(settings.runtime_lab_rag_knowledge_base_ids),
        "retrievalMode": "hybrid",
        "topK": 3,
        "rerank": True,
    }


def _runtime_lab_id_list(raw: Any) -> list[int]:
    if isinstance(raw, (list, tuple)):
        values = raw
    else:
        text = (raw or "").strip()
        if not text:
            return []
        values = text.split(",")
    ids: list[int] = []
    for item in values:
        try:
            ids.append(int(str(item).strip()))
        except ValueError:
            continue
    return ids


def _runtime_lab_threshold(thresholds: Mapping[str, Any], key: str, default: float) -> float:
    raw = thresholds.get(key, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _chatflow_names(session: Session, chatflow_ids: Any) -> dict[int, str]:
    ids = [int(chatflow_id) for chatflow_id in chatflow_ids]
    if not ids:
        return {}
    workflow = Base.metadata.tables["workflow"]
    rows = session.execute(
        workflow.select().where(
            workflow.c.id.in_(ids),
            workflow.c.flow_type == "CHATFLOW",
            workflow.c.deleted.is_(False),
        )
    ).mappings().all()
    return {int(row["id"]): str(row["name"]) for row in rows}


def _runtime_lab_chatflow_trace(session_id: int, session: Session) -> dict[str, Any]:
    runtime_repository = RuntimeLabRepository(session)
    if runtime_repository.get_session(session_id) is None:
        raise BizError(ErrorCode.NOT_FOUND, "Runtime lab session not found")
    workflow_repository = WorkflowRepository(session)
    state_repository = ChatflowStateRepository(session)
    traces = [
        _runtime_task_chatflow_trace(task, runtime_repository, workflow_repository, state_repository)
        for task in runtime_repository.list_tasks(session_id)
    ]
    return {"tasks": traces, "total": len(traces)}


def _runtime_task_chatflow_trace(
    task: dict[str, Any],
    runtime_repository: RuntimeLabRepository,
    workflow_repository: WorkflowRepository,
    state_repository: ChatflowStateRepository,
) -> dict[str, Any]:
    checkpoint = runtime_repository.get_latest_checkpoint(int(task["id"])) or {}
    meta = _chatflow_meta_from_checkpoint(checkpoint)
    chatflow_id = _int_value(meta.get("chatflowId"))
    run_id = _int_value(meta.get("runId"))
    chatflow_session_id = str(meta.get("sessionId") or "")
    workflow = workflow_repository.get(chatflow_id, flow_type="CHATFLOW") if chatflow_id > 0 else None
    node_rows = workflow_repository.list_nodes(chatflow_id) if workflow is not None else []
    edge_rows = workflow_repository.list_edges(chatflow_id) if workflow is not None else []
    node_runs = workflow_repository.list_node_runs(run_id) if run_id > 0 else []
    node_runs_by_key = _latest_node_runs_by_key(node_runs)
    current_step = str(task.get("current_step") or checkpoint.get("current_step") or "")
    events = _chatflow_events(state_repository, chatflow_id, run_id)
    session_variables = _chatflow_session_variables(state_repository, chatflow_id, chatflow_session_id)

    return {
        "taskId": int(task["id"]),
        "sopId": task["sop_id"],
        "status": task["status"],
        "currentStep": current_step,
        "chatflow": {
            "chatflowId": chatflow_id or None,
            "chatflowName": str(workflow.get("name") or "") if workflow else "",
            "exists": workflow is not None,
            "runId": run_id or None,
            "eventId": _optional_int_value(meta.get("eventId")),
            "checkpointId": _optional_int_value(meta.get("checkpointId")),
            "sessionId": chatflow_session_id,
            "canvasPath": f"/chatflows/{chatflow_id}/canvas" if chatflow_id > 0 else "",
            "debugPath": f"/chatflows/{chatflow_id}/canvas?runId={run_id}&debug=1"
            if chatflow_id > 0 and run_id > 0
            else "",
        },
        "nodes": [
            _runtime_trace_node(node, node_runs_by_key.get(str(node["node_key"])), current_step, str(task["status"]))
            for node in node_rows
        ],
        "edges": [
            {
                "sourceNodeKey": edge["source_node_key"],
                "targetNodeKey": edge["target_node_key"],
                "condition": edge.get("condition_expr"),
            }
            for edge in edge_rows
        ],
        "events": events,
        "variables": {
            "businessRefs": task.get("business_refs") or {},
            "collected": checkpoint.get("collected") or {},
            "scoped": _visible_scoped_variables(checkpoint.get("scoped_variables")),
            "session": session_variables,
        },
    }


def _chatflow_meta_from_checkpoint(checkpoint: Mapping[str, Any]) -> Mapping[str, Any]:
    scoped = checkpoint.get("scoped_variables")
    if not isinstance(scoped, Mapping):
        return {}
    meta = scoped.get("__chatflow")
    return meta if isinstance(meta, Mapping) else {}


def _latest_node_runs_by_key(node_runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for node_run in node_runs:
        result[str(node_run.get("node_key") or "")] = node_run
    return result


def _runtime_trace_node(
    node: dict[str, Any],
    node_run: dict[str, Any] | None,
    current_step: str,
    task_status: str,
) -> dict[str, Any]:
    node_key = str(node["node_key"])
    current = node_key == current_step
    return {
        "nodeKey": node_key,
        "nodeType": node["type"],
        "name": node.get("name") or node_key,
        "status": _runtime_node_status(node_run, current=current, task_status=task_status),
        "current": current,
        "elapsedMs": int(node_run.get("elapsed_ms") or 0) if node_run else 0,
        "inputs": (node_run.get("inputs") or {}) if node_run else {},
        "outputs": (node_run.get("outputs") or {}) if node_run else {},
        "usage": _node_usage(node, node_run),
        "error": str(node_run.get("error") or "") if node_run else "",
    }


def _node_usage(node: dict[str, Any], node_run: dict[str, Any] | None) -> dict[str, Any]:
    if node_run is None:
        return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "estimated": False}
    outputs = node_run.get("outputs") if isinstance(node_run.get("outputs"), Mapping) else {}
    usage = outputs.get("__usage") if isinstance(outputs.get("__usage"), Mapping) else {}
    if usage:
        return {
            "inputTokens": _int_value(usage.get("inputTokens")),
            "outputTokens": _int_value(usage.get("outputTokens")),
            "totalTokens": _int_value(usage.get("totalTokens")),
            "estimated": bool(usage.get("estimated", False)),
        }
    if str(node.get("type") or "").upper() == "LLM":
        return {
            "inputTokens": _estimate_tokens(node_run.get("inputs") or {}),
            "outputTokens": _estimate_tokens(outputs),
            "totalTokens": _estimate_tokens(node_run.get("inputs") or {}) + _estimate_tokens(outputs),
            "estimated": True,
        }
    return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "estimated": False}


def _runtime_node_status(node_run: dict[str, Any] | None, *, current: bool, task_status: str) -> str:
    raw = str(node_run.get("status") or "") if node_run else ""
    if current and task_status in {"RUNNING", "WAITING"}:
        if raw in {"", "INTERRUPTED"}:
            return "WAITING"
        if raw == "RUNNING":
            return "RUNNING"
    return raw or "PENDING"


def _chatflow_events(
    state_repository: ChatflowStateRepository,
    chatflow_id: int,
    run_id: int,
) -> list[dict[str, Any]]:
    if chatflow_id <= 0 or run_id <= 0:
        return []
    return [_format_runtime_chatflow_event(event) for event in state_repository.list_events(chatflow_id, run_id)]


def _chatflow_session_variables(
    state_repository: ChatflowStateRepository,
    chatflow_id: int,
    session_id: str,
) -> dict[str, Any]:
    if chatflow_id <= 0 or not session_id:
        return {}
    state = state_repository.get_session(chatflow_id, session_id)
    if state is None:
        return {}
    variables = state.get("variables")
    return dict(variables) if isinstance(variables, Mapping) else {}


def _visible_scoped_variables(scoped: Any) -> dict[str, Any]:
    if not isinstance(scoped, Mapping):
        return {}
    return {str(key): value for key, value in scoped.items() if key != "__chatflow"}


def _format_runtime_chatflow_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(event["id"]),
        "type": event["event_type"],
        "runId": int(event["run_id"]),
        "sequence": int(event["sequence"]),
        "nodeKey": event["node_key"],
        "payload": event["payload"] or {},
        "checkpointId": int(event["checkpoint_id"]) if event.get("checkpoint_id") else None,
        "createdAt": _format_datetime(event.get("created_at")),
    }


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_int_value(value: Any) -> int | None:
    parsed = _int_value(value)
    return parsed if parsed > 0 else None


def _format_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _runtime_lab_intent_classifier(settings: Settings) -> LlmConstrainedIntentClassifier | None:
    mode = settings.runtime_lab_intent_arbitrator_mode.strip().lower()
    if mode != "llm":
        return None
    base_url = (settings.runtime_lab_intent_arbitrator_base_url or "").strip()
    model = settings.runtime_lab_intent_arbitrator_model.strip()
    fallback_model = (settings.runtime_lab_intent_arbitrator_fallback_model or "").strip()
    api_key = (settings.runtime_lab_intent_arbitrator_api_key or "").strip()
    if not base_url or not model:
        return None
    if not api_key and not base_url.startswith("mock://"):
        return None
    client = ProviderBackedOpenAIChatClient(
        ProviderChatConfig(
            provider_type="OPENAI_COMPATIBLE",
            base_url=base_url,
            auth_config={"api_key": api_key},
        ),
        timeout=90.0,
        max_attempts=3,
        retry_sleep=2.0,
    )
    builder = OpenAIChatRequestBuilder()

    def complete(classifier_payload: dict[str, Any]) -> dict[str, Any]:
        llm_payload = builder.build(
            model=model,
            messages=[
                ChatRequestMessage(
                    role="system",
                    content=(
                        "你是民航客服路由仲裁器。只能从用户给定的 candidates 和 allowedActions 中选择，"
                        "返回 JSON 对象：selected_action, selected_candidate_id, confidence, rationale, "
                        "needs_clarification, clarification_question。不要创造候选。"
                    ),
                ),
                ChatRequestMessage(role="user", content=json.dumps(classifier_payload, ensure_ascii=False)),
            ],
            temperature=0.0,
            max_tokens=360,
            extra_params={
                "response_format": {"type": "json_object"},
                "reasoning": {"effort": "none", "exclude": True},
            },
        )
        started_at = perf_counter()
        actual_model = model
        try:
            response = client.complete(llm_payload)
        except Exception:
            if not fallback_model or fallback_model == model:
                raise
            fallback_payload = dict(llm_payload)
            fallback_payload["model"] = fallback_model
            actual_model = fallback_model
            response = client.complete(fallback_payload)
        parsed = _parse_llm_classifier_response(response)
        parsed_output = dict(parsed)
        parsed["_debug"] = {
            "model": actual_model,
            "elapsedMs": int((perf_counter() - started_at) * 1000),
            "input": _redact_llm_payload(llm_payload),
            "output": parsed_output,
            "usage": _usage_from_response(response, llm_payload, parsed_output),
        }
        return parsed

    return LlmConstrainedIntentClassifier(complete)


def _parse_llm_classifier_response(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("LLM classifier response has no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise RuntimeError("LLM classifier response has no text content")
    try:
        parsed = json.loads(content)
    except JSONDecodeError:
        parsed = json.loads(_extract_json_object(content))
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM classifier response JSON is not an object")
    return parsed


def _usage_from_response(response: Mapping[str, Any], request_payload: Any, output_payload: Any) -> dict[str, Any]:
    raw_usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
    input_tokens = _int_value(
        raw_usage.get("prompt_tokens")
        or raw_usage.get("input_tokens")
        or raw_usage.get("promptTokens")
        or raw_usage.get("inputTokens")
    )
    output_tokens = _int_value(
        raw_usage.get("completion_tokens")
        or raw_usage.get("output_tokens")
        or raw_usage.get("completionTokens")
        or raw_usage.get("outputTokens")
    )
    total_tokens = _int_value(raw_usage.get("total_tokens") or raw_usage.get("totalTokens"))
    estimated = False
    if input_tokens == 0:
        input_tokens = _estimate_tokens(request_payload)
        estimated = True
    if output_tokens == 0:
        output_tokens = _estimate_tokens(output_payload)
        estimated = True
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
        estimated = True
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
        "estimated": estimated,
    }


def _estimate_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, int(len(stripped) / 4))


def _redact_llm_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    if "api_key" in sanitized:
        sanitized["api_key"] = "***"
    return sanitized


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise JSONDecodeError("No JSON object found", text, 0)
    return text[start : end + 1]
