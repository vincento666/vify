import hashlib
import json
from dataclasses import replace
from datetime import datetime
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.core.sanitization import sanitize_text, sanitize_value
from app.modules.customer_assistant.harness_adapter import (
    event_stream_ref,
    reserved_worker_async_refs,
    result_ref,
    sub_agent_run_public_id,
    unsupported_cancellation,
)
from app.modules.customer_assistant.domain.action_executor import MockActionExecutorRegistry
from app.modules.customer_assistant.domain.actor import DEFAULT_CUSTOMER_ASSISTANT_ACTOR, CustomerAssistantActor
from app.modules.customer_assistant.domain.controller import DeterministicTaskRecognitionController
from app.modules.customer_assistant.domain.draft_delivery import MockDraftDeliveryOutbox
from app.modules.customer_assistant.domain.ledger import CustomerAssistantLedger, _task_item
from app.modules.customer_assistant.domain.llm_primary import (
    CustomerAssistantLlmRuntimeMode,
    CustomerAssistantLlmRuntimeSettings,
)
from app.modules.customer_assistant.domain.models import AssistantTurnResult, TaskCommand, TaskCommandType, TaskItem, TaskLedger, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.policy import CustomerAssistantActionPolicy, UnsupportedTaskCommand
from app.modules.customer_assistant.domain.react_core import AssistantTurnContext, ControlledReActCore, CoreObservation
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.shadow import (
    CustomerAssistantShadowClient,
    CustomerAssistantShadowSettings,
    FakeCustomerAssistantShadowClient,
    ShadowCallResult,
    ShadowPhase,
    build_shadow_event_payload,
    call_shadow,
    parse_recommendation_shadow_output,
    parse_task_recognition_shadow_output,
)
from app.modules.customer_assistant.domain.two_stage import (
    TWO_STAGE_EQUIVALENCE_MIN_PASS_RATE,
    TWO_STAGE_EQUIVALENCE_SUITE,
    CustomerAssistantTwoStageRuntime,
    TwoStageFinalizer,
)
from app.modules.customer_assistant.domain.turn_mode import (
    CustomerAssistantTurnMode,
    classify_customer_assistant_turn,
)
from app.modules.customer_assistant.domain.worker_runtime import (
    CustomerAssistantWorkerRuntime,
    parse_worker_run_public_id,
    worker_async_refs,
    worker_result_from_worker_run,
)
from app.modules.customer_assistant.domain.worker_profiles import (
    CustomerAssistantWorkerProfile,
    CustomerAssistantWorkerProfileCatalog,
    customer_assistant_worker_profile_from_mapping,
)
from app.modules.customer_assistant.domain.workers import ChatflowSopWorker, RecommendationAggregator, StubQaWorker
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository, IdempotencyConflict
from app.modules.knowledge.api.facade import KnowledgeContextResult, KnowledgeFacade
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter


_MVP_DEMO_STORY_ORDER = (
    "refund_baggage_parallel",
    "invoice_interrupt_flight_status",
    "chatflow_block_resume_recommendation",
)


class CustomerAssistantService:
    def __init__(
        self,
        repository: CustomerAssistantRepository,
        core: ControlledReActCore | None = None,
        scheduler: LocalWorkerScheduler | None = None,
        aggregator: RecommendationAggregator | None = None,
        shadow_settings: CustomerAssistantShadowSettings | None = None,
        shadow_client: CustomerAssistantShadowClient | None = None,
        llm_runtime_settings: CustomerAssistantLlmRuntimeSettings | None = None,
        llm_primary_client: CustomerAssistantShadowClient | None = None,
        two_stage_runtime: TwoStageFinalizer | None = None,
        action_executor_registry: MockActionExecutorRegistry | None = None,
        draft_delivery_outbox: MockDraftDeliveryOutbox | None = None,
        async_worker_runtime: CustomerAssistantWorkerRuntime | None = None,
        worker_profiles: CustomerAssistantWorkerProfileCatalog | None = None,
        request_context: RequestContext | None = None,
        knowledge_facade: KnowledgeFacade | None = None,
    ) -> None:
        self._repository = repository
        self._ledger = CustomerAssistantLedger(repository)
        self._request_context = request_context
        self._worker_profiles = worker_profiles or CustomerAssistantWorkerProfileCatalog.default()
        self._core = core or ControlledReActCore(
            DeterministicTaskRecognitionController(self._worker_profiles),
            CustomerAssistantActionPolicy(),
        )
        self._scheduler = scheduler or LocalWorkerScheduler(
            {
                "chatflow_sop": ChatflowSopWorker(FakeSopRuntimeAdapter()),
                "stub_qa": StubQaWorker(),
            }
        )
        self._aggregator = aggregator or RecommendationAggregator()
        self._shadow_settings = shadow_settings or CustomerAssistantShadowSettings()
        if shadow_client is not None:
            self._shadow_client = shadow_client
        elif self._shadow_settings.mode == "fake":
            self._shadow_client = FakeCustomerAssistantShadowClient()
        else:
            self._shadow_client = None
        self._llm_runtime_settings = llm_runtime_settings or CustomerAssistantLlmRuntimeSettings()
        self._llm_primary_client = llm_primary_client
        self._two_stage_runtime = two_stage_runtime or CustomerAssistantTwoStageRuntime()
        self._action_executor_registry = action_executor_registry or MockActionExecutorRegistry()
        self._draft_delivery_outbox = draft_delivery_outbox or MockDraftDeliveryOutbox()
        self._async_worker_runtime = async_worker_runtime
        self._knowledge_facade = knowledge_facade

    def create_session(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        row = self._repository.create_session(_session_context_with_host_context(context, self._request_context))
        return _format_session(row)

    def list_demo_stories(self) -> dict[str, Any]:
        rows = self._repository.list_demo_sessions("073")
        stories = [_format_demo_story(row, self._repository) for row in rows]
        stories.sort(key=_demo_story_sort_key)
        return {"list": stories, "total": len(stories)}

    def get_demo_story_metrics(self) -> dict[str, Any]:
        rows = self._repository.list_demo_sessions("073")
        story_rows: list[dict[str, Any]] = []
        task_status_counts: dict[str, int] = {}
        action_status_counts: dict[str, int] = {}
        event_type_counts: dict[str, int] = {}
        event_source_counts: dict[str, int] = {}
        worker_event_type_counts: dict[str, int] = {}
        event_total = 0
        worker_event_total = 0
        recent_failure_reasons: list[dict[str, Any]] = []
        for row in rows:
            story = _format_demo_story(row, self._repository)
            session_id = int(story["sessionId"])
            tasks = self._repository.list_tasks(session_id)
            actions = self._repository.list_proposed_actions(session_id)
            events = self._repository.list_events(session_id)
            metrics = _session_metrics_payload(session_id, tasks, actions, events)
            worker_event_counts = dict(metrics["workerEventCounts"])
            story_rows.append(
                {
                    "storyId": story["storyId"],
                    "title": story["title"],
                    "sessionId": session_id,
                    "sessionStatus": story["sessionStatus"],
                    "taskCount": story["taskCount"],
                    "pendingActionCount": story["pendingActionCount"],
                    "taskStatusCounts": metrics["taskStatusCounts"],
                    "proposedActionStatusCounts": metrics["proposedActionStatusCounts"],
                    "humanConfirmation": metrics["humanConfirmation"],
                    "eventCount": metrics["eventCounts"]["total"],
                    "workerEventCount": worker_event_counts["total"],
                    "recentFailureReasons": metrics["recentFailureReasons"],
                }
            )
            _merge_counts(task_status_counts, dict(metrics["taskStatusCounts"]))
            _merge_counts(action_status_counts, dict(metrics["proposedActionStatusCounts"]))
            _merge_counts(event_type_counts, dict(metrics["eventCounts"]["byType"]))
            _merge_counts(event_source_counts, dict(metrics["eventCounts"]["bySource"]))
            _merge_counts(worker_event_type_counts, dict(worker_event_counts["byType"]))
            event_total += int(metrics["eventCounts"]["total"])
            worker_event_total += int(worker_event_counts["total"])
            for failure in metrics["recentFailureReasons"]:
                recent_failure_reasons.append({**failure, "storyId": story["storyId"]})
        story_rows.sort(key=_demo_story_sort_key)
        return {
            "storyCount": len(story_rows),
            "sessionCount": len(rows),
            "taskStatusCounts": task_status_counts,
            "proposedActionStatusCounts": action_status_counts,
            "humanConfirmation": _human_confirmation(action_status_counts),
            "eventCounts": {
                "total": event_total,
                "byType": event_type_counts,
                "bySource": event_source_counts,
            },
            "workerEventCounts": {
                "total": worker_event_total,
                "byType": worker_event_type_counts,
            },
            "recentFailureReasons": recent_failure_reasons[-5:],
            "stories": story_rows,
        }

    def list_worker_profiles(self) -> dict[str, Any]:
        profiles = self._worker_profiles.list_profiles()
        return {"list": profiles, "total": len(profiles)}

    def upsert_worker_profile(self, profile_id: str, profile_payload: dict[str, Any]) -> dict[str, Any]:
        profile = customer_assistant_worker_profile_from_mapping(
            {
                **profile_payload,
                "profileId": profile_id,
            }
        )
        _validate_worker_profile(profile)
        tenant_id, org_id = customer_assistant_worker_profile_scope(self._request_context)
        return self._repository.upsert_worker_profile(
            profile.profile_id,
            profile.to_dict(),
            tenant_id=tenant_id,
            org_id=org_id,
        )

    def _profile_refs_for_task(self, task: TaskItem) -> dict[str, Any] | None:
        profile = self._worker_profiles.resolve(task.task_key)
        if profile is None:
            return None
        return _worker_profile_refs(profile)

    def _profile_refs_for_command(self, command: TaskCommand) -> dict[str, Any] | None:
        profile = self._worker_profiles.resolve(command.task_key)
        if profile is None:
            return None
        return _worker_profile_refs(profile)

    def _command_payload_with_profile_refs(self, command: TaskCommand) -> dict[str, Any]:
        payload = _command_payload(command)
        profile_refs = self._profile_refs_for_command(command)
        if profile_refs:
            payload["profileRefs"] = profile_refs
        return payload

    def handle_turn(
        self,
        session_id: int,
        message: str,
        idempotency_key: str | None = None,
        actor: CustomerAssistantActor = DEFAULT_CUSTOMER_ASSISTANT_ACTOR,
    ) -> dict[str, Any]:
        self._ensure_session(session_id)
        self._consume_completed_async_worker_results(session_id, actor=actor)
        turn_mode = classify_customer_assistant_turn(actor, message)
        request_hash = _request_hash(message, actor, turn_mode)
        try:
            run, replayed = self._repository.create_run(
                session_id=session_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                input_payload={"message": message, "actor": actor, "turnMode": turn_mode.value},
            )
        except IdempotencyConflict as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        if replayed:
            payload = sanitize_value(dict(run.get("response_payload") or {}))
            payload["replayed"] = True
            return payload

        return self._execute_turn_for_run(int(run["id"]), session_id, message, actor, turn_mode)

    def spawn_sub_agent(
        self,
        *,
        message: str,
        actor: CustomerAssistantActor = DEFAULT_CUSTOMER_ASSISTANT_ACTOR,
        session_id: int | None = None,
        event_level: str = "L1",
    ) -> dict[str, Any]:
        if session_id is None:
            session_id = int(self.create_session({})["id"])
        else:
            self._ensure_session(session_id)
        turn_mode = classify_customer_assistant_turn(actor, message)
        run, _ = self._repository.create_run(
            session_id=session_id,
            idempotency_key=None,
            request_hash=_request_hash(message, actor, turn_mode),
            input_payload={
                "message": message,
                "actor": actor,
                "turnMode": turn_mode.value,
                "tool": "spawn_sub_agent",
                "agentType": "customer_assistant",
                "eventLevel": event_level,
            },
        )
        run_id = int(run["id"])
        payload = _sub_agent_run_payload(run_id=run_id, session_id=session_id, status="running")
        self._repository.append_event(
            session_id,
            "sub_agent_spawned",
            {
                **payload,
                "input": {"message": message, "actor": actor},
                "eventLevel": event_level,
            },
            run_id=run_id,
            source="harness",
            actor=actor,
        )
        return payload

    def run_spawned_sub_agent(
        self,
        run_id: int,
        session_id: int,
        message: str,
        actor: CustomerAssistantActor = DEFAULT_CUSTOMER_ASSISTANT_ACTOR,
        event_level: str = "L1",
    ) -> dict[str, Any]:
        self._ensure_session(session_id)
        turn_mode = classify_customer_assistant_turn(actor, message)
        self._repository.append_event(
            session_id,
            "sub_agent_started",
            {
                "subAgentRunId": sub_agent_run_public_id(run_id),
                "agentType": "customer_assistant",
                "eventLevel": event_level,
            },
            run_id=run_id,
            source="harness",
            actor=actor,
        )
        if self._request_context is not None and _should_record_host_context(self._request_context):
            self._repository.append_event(
                session_id,
                "session_context_snapshot",
                {
                    "subAgentRunId": sub_agent_run_public_id(run_id),
                    "hostContext": sanitize_value(self._request_context.audit_metadata()),
                },
                run_id=run_id,
                source="harness",
                actor=actor,
            )
        self._repository.append_event(
            session_id,
            "sub_agent_progress",
            {
                "subAgentRunId": sub_agent_run_public_id(run_id),
                "stage": "customer_assistant_runtime",
                "status": "running",
            },
            run_id=run_id,
            source="harness",
            actor=actor,
        )
        try:
            result = self._execute_turn_for_run(run_id, session_id, message, actor, turn_mode)
        except BizError as exc:
            self._repository.append_event(
                session_id,
                "sub_agent_failed",
                {
                    "subAgentRunId": sub_agent_run_public_id(run_id),
                    "status": "failed",
                    "error": str(exc),
                },
                run_id=run_id,
                source="harness",
                actor=actor,
            )
            return {"error": str(exc)}
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            self._repository.complete_run(run_id, {"error": error}, status="FAILED", warnings=[error])
            self._repository.append_event(
                session_id,
                "sub_agent_failed",
                {
                    "subAgentRunId": sub_agent_run_public_id(run_id),
                    "status": "failed",
                    "error": error,
                },
                run_id=run_id,
                source="harness",
                actor=actor,
            )
            return {"error": error}
        self._repository.append_event(
            session_id,
            "sub_agent_completed",
            {
                "subAgentRunId": sub_agent_run_public_id(run_id),
                "status": "completed",
                "resultRef": result_ref(run_id),
            },
            run_id=run_id,
            source="harness",
            actor=actor,
        )
        return result

    def get_sub_agent_run(self, run_id: int) -> dict[str, Any]:
        run = self._repository.get_run(run_id)
        if run is None:
            raise BizError(ErrorCode.NOT_FOUND, "Customer assistant run not found")
        session_id = int(run["session_id"])
        self._ensure_session(session_id)
        events = [
            _format_event(row)
            for row in self._repository.list_events(session_id)
            if int(row.get("run_id") or 0) == run_id
        ]
        return {
            **_sub_agent_run_payload(
                run_id=run_id,
                session_id=session_id,
                status=_sub_agent_status(str(run["status"])),
            ),
            "result": sanitize_value(run.get("response_payload") or {}),
            "events": events,
            "warnings": sanitize_value(run.get("warnings_json") or []),
            "startedAt": _iso(run.get("started_at")),
            "completedAt": _iso(run.get("completed_at")),
        }

    def cancel_worker_run(self, worker_run_id: str) -> dict[str, Any]:
        worker_run = self._get_worker_run_row(worker_run_id)
        numeric_worker_run_id = int(worker_run["id"])
        status = "CANCEL_UNSUPPORTED"
        if str(worker_run["status"]) not in {"COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED", "CANCEL_UNSUPPORTED"}:
            self._repository.complete_worker_run(
                numeric_worker_run_id,
                status=status,
                result_payload=dict(worker_run.get("result_payload") or {}),
                error={"code": "CANCEL_UNSUPPORTED", "message": "Cooperative cancellation is not supported for this worker."},
            )
        payload = {
            "workerRunId": worker_run_id,
            "runId": numeric_worker_run_id,
            "parentRunId": int(worker_run["parent_run_id"]),
            "supported": False,
            "reason": "Cooperative cancellation is not supported for this customer-assistant worker.",
        }
        self._repository.append_worker_event(
            numeric_worker_run_id,
            "worker_cancel_requested",
            payload,
            source="customer_assistant_worker",
            actor="operator",
        )
        self._repository.append_worker_event(
            numeric_worker_run_id,
            "worker_cancel_unsupported",
            payload,
            source="customer_assistant_worker",
            actor="operator",
        )
        self._repository.append_event(
            int(worker_run["session_id"]),
            "worker_cancel_requested",
            payload,
            run_id=int(worker_run["parent_run_id"]),
            task_id=int(worker_run["task_id"]),
            source="customer_assistant_worker",
            actor="operator",
        )
        self._repository.append_event(
            int(worker_run["session_id"]),
            "worker_cancel_unsupported",
            payload,
            run_id=int(worker_run["parent_run_id"]),
            task_id=int(worker_run["task_id"]),
            source="customer_assistant_worker",
            actor="operator",
        )
        return {
            "workerRunId": worker_run_id,
            "runId": numeric_worker_run_id,
            "parentRunId": int(worker_run["parent_run_id"]),
            "status": "cancel_unsupported",
            "cancellation": {"supported": False, "reason": payload["reason"]},
        }

    def get_worker_run(self, worker_run_id: str) -> dict[str, Any]:
        self._repository.refresh_external_writes()
        return _format_worker_run(self._get_worker_run_row(worker_run_id))

    def get_worker_result(self, worker_run_id: str) -> dict[str, Any]:
        self._repository.refresh_external_writes()
        row = self._get_worker_run_row(worker_run_id)
        return {
            **_format_worker_run(row),
            "result": sanitize_value(row.get("result_payload") or {}),
            "error": sanitize_value(row.get("error_json") or {}),
        }

    def list_worker_events(self, worker_run_id: str) -> dict[str, Any]:
        self._repository.refresh_external_writes()
        row = self._get_worker_run_row(worker_run_id)
        events = [_format_worker_event(event) for event in self._repository.list_worker_events(int(row["id"]))]
        return {"list": events, "total": len(events)}

    def list_worker_events_after(self, worker_run_id: str, after_sequence: int) -> list[dict[str, Any]]:
        self._repository.refresh_external_writes()
        row = self._get_worker_run_row(worker_run_id)
        return [
            _format_worker_event(event)
            for event in self._repository.list_worker_events_after(int(row["id"]), after_sequence)
        ]

    def ensure_worker_run_access(self, worker_run_id: str) -> None:
        self._get_worker_run_row(worker_run_id)

    def _get_worker_run_row(self, worker_run_id: str) -> dict[str, Any]:
        try:
            numeric_worker_run_id = parse_worker_run_public_id(worker_run_id)
        except ValueError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, "Invalid customer assistant worker run id") from exc
        worker_run = self._repository.get_worker_run(numeric_worker_run_id)
        if worker_run is None:
            raise BizError(ErrorCode.NOT_FOUND, "Customer assistant worker run not found")
        self._ensure_session(int(worker_run["session_id"]))
        return worker_run

    def _execute_turn_for_run(
        self,
        run_id: int,
        session_id: int,
        message: str,
        actor: CustomerAssistantActor,
        turn_mode: CustomerAssistantTurnMode | None = None,
    ) -> dict[str, Any]:
        turn_mode = turn_mode or classify_customer_assistant_turn(actor, message)
        run_started_at = datetime.now()
        self._repository.append_event(
            session_id,
            "run_started",
            {
                "message": message,
                "actor": actor,
                "turnMode": turn_mode.value,
                "startedAt": _iso(run_started_at),
            },
            run_id=run_id,
            actor=actor,
        )
        self._repository.append_event(
            session_id,
            "operator_turn_classified",
            {"actor": actor, "turnMode": turn_mode.value},
            run_id=run_id,
            actor=actor,
        )
        if turn_mode == CustomerAssistantTurnMode.OPERATOR_RECOMMENDATION_TURN:
            result = self._handle_operator_recommendation_turn(session_id, run_id, message, actor, turn_mode)
            payload = _turn_result_payload(result, replayed=False)
            self._repository.complete_run(run_id, payload)
            return payload
        context = AssistantTurnContext(
            session_id=session_id,
            run_id=run_id,
            message=message,
            ledger=self._current_ledger(session_id),
        )
        try:
            result = self._run_core_with_optional_primary_selector(context, session_id, run_id, message, actor)
        except UnsupportedTaskCommand as exc:
            failed_at = datetime.now()
            self._repository.append_event(
                session_id,
                "run_failed",
                {
                    "runId": run_id,
                    "actor": actor,
                    "error": str(exc),
                    "startedAt": _iso(run_started_at),
                    "completedAt": _iso(failed_at),
                    "elapsedMs": _elapsed_ms(run_started_at, failed_at),
                },
                run_id=run_id,
                actor=actor,
            )
            self._repository.complete_run(run_id, {"error": str(exc)}, status="FAILED", warnings=[str(exc)])
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc

        payload = _turn_result_payload(result, replayed=False)
        self._repository.complete_run(run_id, payload)
        return payload

    def _run_core_with_optional_primary_selector(
        self,
        context: AssistantTurnContext,
        session_id: int,
        run_id: int,
        message: str,
        actor: CustomerAssistantActor,
    ) -> AssistantTurnResult:
        def action_handler(commands: list[TaskCommand]) -> dict[str, Any]:
            return self._act(session_id, run_id, message, commands, actor)

        def finalizer(observation: CoreObservation) -> AssistantTurnResult:
            return self._finalize(session_id, run_id, observation, actor)

        try:
            return self._core.run(
                context,
                action_handler=action_handler,
                finalizer=finalizer,
                command_selector=lambda commands: self._select_task_commands(
                    session_id,
                    run_id,
                    message,
                    actor,
                    commands,
                ),
            )
        except TypeError as exc:
            if "command_selector" not in str(exc):
                raise
            return self._core.run(
                context,
                action_handler=action_handler,
                finalizer=finalizer,
            )

    def _handle_operator_recommendation_turn(
        self,
        session_id: int,
        run_id: int,
        message: str,
        actor: CustomerAssistantActor,
        turn_mode: CustomerAssistantTurnMode,
    ) -> AssistantTurnResult:
        context_pack = self._operator_advisory_context_pack(session_id, message)
        self._repository.append_event(
            session_id,
            "operator_advisory_context_packed",
            {
                "turnMode": turn_mode.value,
                "taskCount": len(context_pack["taskSummaries"]),
                "eventCount": context_pack["eventCount"],
                "evidenceCount": len(context_pack["evidence"]),
                "knowledgeSnippetCount": len(context_pack["knowledgeSnippets"]),
                "warnings": list(context_pack["warnings"]),
            },
            run_id=run_id,
            source="operator_advisory",
            actor=actor,
        )
        self._repository.append_event(
            session_id,
            "operator_advisory_harness_summarized",
            {
                "turnMode": turn_mode.value,
                "readOnly": True,
                "taskCount": len(context_pack["taskSummaries"]),
                "eventCount": context_pack["eventCount"],
                "mutationApplied": False,
            },
            run_id=run_id,
            source="harness",
            actor=actor,
        )
        created_actions = self._create_operator_proposed_task_commands(session_id, run_id, message, actor)
        action_rows = _sort_formatted_actions(
            [_format_action(row) for row in self._repository.list_proposed_actions(session_id)]
        )
        recommendation = _operator_advisory_recommendation(message, context_pack, created_actions)
        self._repository.append_event(
            session_id,
            "operator_recommendation_generated",
            {
                "turnMode": turn_mode.value,
                "proposedTaskCommandCount": len(created_actions),
                "warningCount": len(context_pack["warnings"]),
            },
            run_id=run_id,
            source="operator_advisory",
            actor=actor,
        )
        events = [_format_event(row) for row in self._repository.list_events(session_id)]
        return AssistantTurnResult(
            run_id=run_id,
            session_id=session_id,
            reply_type="OPERATOR_RECOMMENDATION",
            operator_recommendation=recommendation,
            customer_reply_draft="",
            task_summaries=list(context_pack["taskSummaries"]),
            proposed_actions=action_rows,
            warnings=list(context_pack["warnings"]),
            events=events,
        )

    def _operator_advisory_context_pack(self, session_id: int, message: str) -> dict[str, Any]:
        task_summaries = [_format_task(row) for row in self._repository.list_tasks(session_id)]
        event_rows = self._repository.list_events(session_id)
        event_summary = [_operator_event_summary(row) for row in event_rows[-8:]]
        evidence = _operator_evidence_from_tasks(task_summaries)
        session_row = self._repository.get_session(session_id)
        session_context = dict((session_row or {}).get("context_json") or {})
        knowledge_snippets = _operator_knowledge_snippets(
            KnowledgeBaseRepository(self._repository.session),
            session_context,
            task_summaries,
            message,
        )
        warnings: list[str] = []
        if not task_summaries:
            warnings.append("Task ledger context missing; operator recommendation is read-only.")
        if not knowledge_snippets:
            warnings.append("Knowledge snippets unavailable for operator advisory context.")
        if not evidence:
            warnings.append("Chatflow/SOP metadata unavailable for operator advisory context.")
        warnings.append("Harness advisory summaries unavailable for operator advisory context.")
        return {
            "taskSummaries": task_summaries,
            "eventSummary": event_summary,
            "eventCount": len(event_rows),
            "evidence": evidence,
            "knowledgeSnippets": knowledge_snippets,
            "warnings": warnings,
        }

    def _create_operator_proposed_task_commands(
        self,
        session_id: int,
        run_id: int,
        message: str,
        actor: CustomerAssistantActor,
    ) -> list[dict[str, Any]]:
        if not _operator_message_requests_task_mutation(message):
            return []
        ledger = self._current_ledger(session_id)
        commands = DeterministicTaskRecognitionController().recognize(message, ledger)
        allowed = {
            TaskCommandType.ADD_TASK,
            TaskCommandType.RETAIN_TASK,
            TaskCommandType.SUSPEND_TASK,
            TaskCommandType.RESUME_TASK,
            TaskCommandType.CANCEL_TASK,
        }
        created: list[dict[str, Any]] = []
        for command in commands:
            if command.type not in allowed:
                continue
            payload = {
                "turnMode": CustomerAssistantTurnMode.OPERATOR_APPLY_TASK_COMMAND.value,
                "requiresConfirmation": True,
                "message": message,
                "taskCommand": _command_payload(command),
            }
            row = self._repository.upsert_proposed_action(
                session_id=session_id,
                run_id=run_id,
                task_id=None,
                action_key=f"operator-task-command:{run_id}:{command.type.value}:{command.task_key}",
                action_type="PROPOSED_TASK_COMMAND",
                title=f"确认任务变更：{command.task_key}",
                payload=payload,
            )
            self._repository.append_event(
                session_id,
                "proposed_task_command_created",
                {
                    "turnMode": CustomerAssistantTurnMode.OPERATOR_RECOMMENDATION_TURN.value,
                    "actionId": row["id"],
                    "taskCommand": _command_payload(command),
                },
                run_id=run_id,
                source="operator_advisory",
                actor=actor,
            )
            created.append(_format_action(row))
        return created

    def list_tasks(self, session_id: int) -> dict[str, Any]:
        self._ensure_session(session_id)
        rows = self._repository.list_tasks(session_id)
        return {"list": [_format_task(row) for row in rows], "total": len(rows)}

    def answer_operator_knowledge_question(self, session_id: int, question: str) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            raise BizError(ErrorCode.BAD_REQUEST, "Operator knowledge question is required")
        self._ensure_session(session_id)
        session_row = self._repository.get_session(session_id)
        session_context = dict((session_row or {}).get("context_json") or {})
        task_summaries = [_format_task(row) for row in self._repository.list_tasks(session_id)]
        action_rows = _sort_formatted_actions(
            [_format_action(row) for row in self._repository.list_proposed_actions(session_id)]
        )
        event_rows = self._repository.list_events(session_id)
        context_summary = _operator_knowledge_qa_context_summary(
            session_id,
            session_context,
            task_summaries,
            action_rows,
            event_rows,
        )
        evidence = _operator_knowledge_qa_evidence(task_summaries)
        sources, warnings = self._operator_knowledge_qa_sources(
            session_context,
            task_summaries,
            normalized_question,
        )
        if not evidence:
            warnings.append("Task/SOP evidence unavailable for this customer-assistant session.")
        answer = _operator_knowledge_qa_answer(
            normalized_question,
            sources,
            context_summary,
            evidence,
            warnings,
        )
        return {
            "sessionId": session_id,
            "question": sanitize_text(normalized_question),
            "answer": answer,
            "sources": sources,
            "evidence": evidence,
            "contextSummary": context_summary,
            "warnings": warnings,
        }

    def _operator_knowledge_qa_sources(
        self,
        session_context: dict[str, Any],
        task_summaries: list[dict[str, Any]],
        question: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        knowledge_base_ids = _operator_knowledge_base_ids(session_context)
        if not knowledge_base_ids:
            return [], ["No session knowledge base ids are configured for operator Q&A."]
        retrieval_settings = dict(session_context.get("retrievalSettings") or {})
        retrieval_mode = str(retrieval_settings.get("mode") or "faq")
        top_k = _positive_int(retrieval_settings.get("topK"), default=3, maximum=5)
        facade = self._knowledge_facade or KnowledgeFacade(self._repository.session)
        query = _operator_knowledge_qa_query(question, task_summaries)
        sources: list[dict[str, Any]] = []
        for knowledge_base_id in knowledge_base_ids:
            results = facade.search_context(
                knowledge_base_id,
                query,
                top_k=top_k,
                retrieval_mode=retrieval_mode,
            )
            sources.extend(
                _operator_knowledge_qa_source(knowledge_base_id, result)
                for result in results
            )
        sources.sort(key=lambda item: (-float(item.get("score") or 0.0), str(item.get("title") or "")))
        warnings: list[str] = []
        if not sources:
            warnings.append("No seeded FAQ or knowledge source matched the operator question.")
        return sources[:top_k], warnings

    def list_events(self, session_id: int) -> dict[str, Any]:
        self._ensure_session(session_id)
        rows = self._repository.list_events(session_id)
        return {"list": [_format_event(row) for row in rows], "total": len(rows)}

    def list_proposed_actions(self, session_id: int) -> dict[str, Any]:
        self._ensure_session(session_id)
        rows = self._repository.list_proposed_actions(session_id)
        actions = _sort_formatted_actions([_format_action(row) for row in rows])
        return {"list": actions, "total": len(actions)}

    def get_session_metrics(self, session_id: int) -> dict[str, Any]:
        self._ensure_session(session_id)
        tasks = self._repository.list_tasks(session_id)
        actions = self._repository.list_proposed_actions(session_id)
        events = self._repository.list_events(session_id)
        return _session_metrics_payload(session_id, tasks, actions, events)

    def list_operator_audit(self, session_id: int) -> dict[str, Any]:
        self._ensure_session(session_id)
        rows = self._repository.list_events(session_id)
        items = [item for row in rows if (item := _operator_audit_row(row)) is not None]
        return {"sessionId": session_id, "list": items, "total": len(items)}

    def update_action(
        self,
        action_id: int,
        *,
        title: str | None = None,
        payload: dict[str, Any] | None = None,
        actor: CustomerAssistantActor = "operator",
    ) -> dict[str, Any]:
        action = self._repository.get_proposed_action(action_id)
        if action is None:
            raise BizError(ErrorCode.NOT_FOUND, "Proposed action not found")
        self._ensure_session(int(action["session_id"]))
        if action["status"] != "PENDING":
            raise BizError(ErrorCode.BAD_REQUEST, "Only pending proposed actions can be modified")
        if title is None and payload is None:
            raise BizError(ErrorCode.BAD_REQUEST, "No proposed action changes supplied")
        changed_fields: list[str] = []
        if title is not None and title != action.get("title"):
            changed_fields.append("title")
        if payload is not None and payload != (action.get("payload") or {}):
            changed_fields.append("payload")
        updated = self._repository.update_proposed_action(action_id, title=title, payload=payload)
        self._repository.append_event(
            int(updated["session_id"]),
            "proposed_action_modified",
            {
                "actionId": action_id,
                "actionType": updated["action_type"],
                "changedFields": changed_fields,
            },
            run_id=int(updated["run_id"]),
            task_id=updated.get("task_id"),
            source="operator_advisory",
            actor=actor,
        )
        return _format_action(updated)

    def propose_task_control(
        self,
        session_id: int,
        task_id: int,
        control_type: str,
        reason: str = "",
        actor: CustomerAssistantActor = "operator",
    ) -> dict[str, Any]:
        self._ensure_session(session_id)
        task = self._repository.get_task(task_id)
        if task is None or int(task["session_id"]) != session_id:
            raise BizError(ErrorCode.NOT_FOUND, "Customer assistant task not found")
        _ensure_task_control_allowed(task, control_type)
        command = _task_control_command(task, control_type, reason)
        action_key = f"task-control:{session_id}:{task_id}:{control_type}:{task.get('version') or 1}"
        input_payload = {
            "tool": "task_control",
            "controlType": control_type,
            "reason": reason,
            "actor": actor,
            "taskId": task_id,
            "taskVersion": task.get("version") or 1,
        }
        run, replayed = self._repository.create_run(
            session_id=session_id,
            idempotency_key=action_key,
            request_hash=_task_control_request_hash(input_payload),
            input_payload=input_payload,
        )
        row = self._repository.upsert_proposed_action(
            session_id=session_id,
            run_id=int(run["id"]),
            task_id=task_id,
            action_key=action_key,
            action_type="PROPOSED_TASK_COMMAND",
            title=f"{_task_control_label(control_type)}：{task['task_key']}",
            payload={
                "turnMode": CustomerAssistantTurnMode.OPERATOR_APPLY_TASK_COMMAND.value,
                "requiresConfirmation": True,
                "controlType": control_type,
                "reason": reason,
                "taskCommand": _command_payload(command),
            },
        )
        self._repository.append_event(
            session_id,
            "task_control_proposed",
            {
                "actionId": int(row["id"]),
                "controlType": control_type,
                "taskId": task_id,
                "taskKey": task["task_key"],
                "requiresConfirmation": True,
            },
            run_id=int(run["id"]),
            task_id=task_id,
            source="operator_advisory",
            actor=actor,
        )
        if not replayed:
            self._repository.complete_run(
                int(run["id"]),
                {
                    "status": "PROPOSED",
                    "actionId": int(row["id"]),
                    "controlType": control_type,
                    "taskId": task_id,
                },
            )
        return _format_action(row)

    def list_events_after(self, session_id: int, after_sequence: int) -> list[dict[str, Any]]:
        self._ensure_session(session_id)
        self._repository.refresh_external_writes()
        rows = self._repository.list_events_after(session_id, after_sequence)
        return [_format_event(row) for row in rows]

    def ensure_session_access(self, session_id: int) -> None:
        self._ensure_session(session_id)

    def refresh_worker_results(self, session_id: int) -> dict[str, Any]:
        self._ensure_session(session_id)
        self._repository.refresh_external_writes()
        consumed = self._consume_completed_async_worker_results(session_id, actor="system")
        rows = self._repository.list_tasks(session_id)
        return {
            "sessionId": session_id,
            "consumed": consumed,
            "tasks": [_format_task(row) for row in rows],
        }

    def confirm_action(self, action_id: int) -> dict[str, Any]:
        action = self._repository.get_proposed_action(action_id)
        if action is None:
            raise BizError(ErrorCode.NOT_FOUND, "Proposed action not found")
        self._ensure_session(int(action["session_id"]))
        if action["status"] != "PENDING":
            raise BizError(ErrorCode.BAD_REQUEST, "Only pending proposed actions can be confirmed")
        if action["action_type"] == "PROPOSED_TASK_COMMAND":
            return self._confirm_proposed_task_command(action)
        updated = self._repository.update_proposed_action_status(action_id, "CONFIRMED")
        self._repository.append_event(
            int(updated["session_id"]),
            "proposed_action_confirmed",
            {"actionId": action_id, "actionType": updated["action_type"]},
            run_id=int(updated["run_id"]),
        )
        return _format_action(updated)

    def _confirm_proposed_task_command(self, action: dict[str, Any]) -> dict[str, Any]:
        payload = dict(action.get("payload") or {})
        command = _task_command_from_proposed_payload(dict(payload.get("taskCommand") or {}))
        session_id = int(action["session_id"])
        run_id = int(action["run_id"])
        mutation = self._ledger.apply_commands(
            session_id,
            run_id,
            str(payload.get("message") or ""),
            [command],
            actor="operator",
        )
        worker_results: list[WorkerResult] = []
        updated_tasks: tuple[TaskItem, ...] = ()
        if command.type == TaskCommandType.RESUME_TASK:
            worker_results, updated_tasks = self._dispatch_ready_tasks(
                session_id,
                run_id,
                str(payload.get("message") or payload.get("reason") or command.reason or ""),
                mutation.ready_tasks,
                actor="operator",
            )
        result_payload: dict[str, Any] = {
            "applied": True,
            "taskCommand": _command_payload(command),
        }
        if worker_results or updated_tasks:
            result_payload["workerResultCount"] = len(worker_results)
            result_payload["updatedTaskIds"] = [task.id for task in updated_tasks]
            worker_run_ids = [result.worker_run_id for result in worker_results if result.worker_run_id]
            if worker_run_ids:
                result_payload["workerRunIds"] = worker_run_ids
        updated = self._repository.update_proposed_action_status(
            int(action["id"]),
            "CONFIRMED",
            result=result_payload,
        )
        self._repository.append_event(
            session_id,
            "proposed_task_command_confirmed",
            {
                "actionId": int(action["id"]),
                "turnMode": CustomerAssistantTurnMode.OPERATOR_APPLY_TASK_COMMAND.value,
                "taskCommand": _command_payload(command),
            },
            run_id=run_id,
            source="operator_advisory",
            actor="operator",
        )
        self._repository.append_event(
            session_id,
            "proposed_action_confirmed",
            {"actionId": int(action["id"]), "actionType": updated["action_type"]},
            run_id=run_id,
            actor="operator",
        )
        return _format_action(updated)

    def reject_action(self, action_id: int) -> dict[str, Any]:
        action = self._repository.get_proposed_action(action_id)
        if action is None:
            raise BizError(ErrorCode.NOT_FOUND, "Proposed action not found")
        self._ensure_session(int(action["session_id"]))
        if action["status"] != "PENDING":
            raise BizError(ErrorCode.BAD_REQUEST, "Only pending proposed actions can be rejected")
        updated = self._repository.update_proposed_action_status(action_id, "REJECTED")
        self._repository.append_event(
            int(updated["session_id"]),
            "proposed_action_rejected",
            {"actionId": action_id, "actionType": updated["action_type"]},
            run_id=int(updated["run_id"]),
        )
        return _format_action(updated)

    def execute_action(self, action_id: int) -> dict[str, Any]:
        action = self._repository.get_proposed_action(action_id)
        if action is None:
            raise BizError(ErrorCode.NOT_FOUND, "Proposed action not found")
        self._ensure_session(int(action["session_id"]))
        if action["status"] != "CONFIRMED":
            raise BizError(ErrorCode.BAD_REQUEST, "Only confirmed proposed actions can be executed")
        executing = self._repository.transition_proposed_action_status(
            action_id,
            expected_status="CONFIRMED",
            next_status="EXECUTING",
        )
        if executing is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Only confirmed proposed actions can be executed")
        self._repository.append_event(
            int(executing["session_id"]),
            "proposed_action_executing",
            {"actionId": action_id, "actionType": executing["action_type"]},
            run_id=int(executing["run_id"]),
        )
        result = self._action_executor_registry.execute(
            str(executing["action_type"]),
            dict(executing.get("payload") or {}),
        )
        result_payload = {
            "executorRef": result.executor_ref,
            "audit": result.audit_payload,
            "error": result.error,
        }
        final_status = "EXECUTED" if result.status == "EXECUTED" else "FAILED"
        updated = self._repository.update_proposed_action_status(action_id, final_status, result=result_payload)
        self._repository.append_event(
            int(updated["session_id"]),
            "proposed_action_executed" if final_status == "EXECUTED" else "proposed_action_failed",
            {
                "actionId": action_id,
                "actionType": updated["action_type"],
                "status": final_status,
                "result": result_payload,
            },
            run_id=int(updated["run_id"]),
        )
        return _format_action(updated)

    def deliver_action(self, action_id: int) -> dict[str, Any]:
        action = self._repository.get_proposed_action(action_id)
        if action is None:
            raise BizError(ErrorCode.NOT_FOUND, "Proposed action not found")
        self._ensure_session(int(action["session_id"]))
        if action["status"] != "CONFIRMED":
            raise BizError(ErrorCode.BAD_REQUEST, "Only confirmed draft actions can be delivered")
        if str(action["action_type"]) != "send_customer_message":
            raise BizError(ErrorCode.BAD_REQUEST, "Only customer reply draft actions can be delivered")
        delivering = self._repository.transition_proposed_action_status(
            action_id,
            expected_status="CONFIRMED",
            next_status="DELIVERING",
        )
        if delivering is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Only confirmed draft actions can be delivered")
        session_id = int(delivering["session_id"])
        run_id = int(delivering["run_id"])
        task_id = delivering.get("task_id")
        start_payload = {
            "actionId": action_id,
            "actionType": delivering["action_type"],
            "status": "DELIVERING",
            "adapterRef": self._draft_delivery_outbox.adapter_ref,
        }
        self._repository.append_event(
            session_id,
            "draft_delivery_started",
            start_payload,
            run_id=run_id,
            task_id=task_id,
            source="draft_delivery_outbox",
            actor="operator",
        )
        delivery = self._draft_delivery_outbox.deliver(dict(delivering.get("payload") or {}))
        result_payload = sanitize_value(
            {
                "delivery": delivery.delivery,
                "error": delivery.error,
            }
        )
        final_status = "SENT" if delivery.status == "SENT" else "FAILED"
        updated = self._repository.update_proposed_action_status(action_id, final_status, result=result_payload)
        event_type = "draft_delivery_sent" if final_status == "SENT" else "draft_delivery_failed"
        self._repository.append_event(
            int(updated["session_id"]),
            event_type,
            {
                "actionId": action_id,
                "actionType": updated["action_type"],
                "status": final_status,
                "delivery": result_payload["delivery"],
                "error": result_payload["error"],
            },
            run_id=int(updated["run_id"]),
            task_id=updated.get("task_id"),
            source="draft_delivery_outbox",
            actor="operator",
        )
        return _format_action(updated)

    def _act(
        self,
        session_id: int,
        run_id: int,
        message: str,
        commands: list[TaskCommand],
        actor: str,
    ) -> dict[str, Any]:
        if commands:
            self._repository.append_event(
                session_id,
                "task_recognized",
                {"commands": [self._command_payload_with_profile_refs(command) for command in commands], "actor": actor},
                run_id=run_id,
                actor=actor,
            )
        self._record_task_recognition_shadow(session_id, run_id, message, commands, actor)
        mutation = self._ledger.apply_commands(session_id, run_id, message, commands, actor=actor)
        worker_results, updated_tasks = self._dispatch_ready_tasks(
            session_id,
            run_id,
            message,
            mutation.ready_tasks,
            actor,
        )
        return {
            "commands": commands,
            "workerResults": worker_results,
            "updatedTasks": updated_tasks,
        }

    def _dispatch_ready_tasks(
        self,
        session_id: int,
        run_id: int,
        message: str,
        ready_tasks: tuple[TaskItem, ...],
        actor: str,
    ) -> tuple[list[WorkerResult], tuple[TaskItem, ...]]:
        if not ready_tasks:
            return [], ()
        worker_spans: dict[int, str] = {}
        ready_task_list = list(ready_tasks)
        for task in ready_task_list:
            span_id = f"run-{run_id}:task-{task.id}:worker"
            if task.id is not None:
                worker_spans[int(task.id)] = span_id
            profile_refs = self._profile_refs_for_task(task)
            task_started_payload: dict[str, Any] = {
                "taskKey": task.task_key,
                "workerType": task.worker_type,
                "startedAt": _iso(datetime.now()),
            }
            worker_started_payload: dict[str, Any] = {
                "taskKey": task.task_key,
                "workerType": task.worker_type,
                "spanId": span_id,
                "startedAt": _iso(datetime.now()),
            }
            if profile_refs:
                task_started_payload["profileRefs"] = profile_refs
                worker_started_payload["profileRefs"] = profile_refs
            self._repository.append_event(
                session_id,
                "task_started",
                task_started_payload,
                run_id=run_id,
                task_id=task.id,
                actor=actor,
            )
            self._repository.append_event(
                session_id,
                "worker_started",
                worker_started_payload,
                run_id=run_id,
                task_id=task.id,
                visibility="debug",
                source=task.worker_type,
                actor=actor,
                span_id=span_id,
            )
        worker_results = self._run_ready_tasks(session_id, run_id, ready_task_list, message, actor)
        for result in worker_results:
            parent_span_id = worker_spans.get(result.task_id)
            for index, event in enumerate(result.events, start=1):
                payload = dict(event.get("payload") or {})
                if result.worker_run_id:
                    payload.setdefault("workerRunId", result.worker_run_id)
                runtime_refs = dict(result.evidence.get("chatflowRuntimeRefs") or {})
                if runtime_refs:
                    payload.setdefault("runtimeRunId", runtime_refs.get("runId"))
                self._repository.append_event(
                    session_id,
                    str(event.get("type") or "worker_result_received"),
                    payload,
                    run_id=run_id,
                    task_id=result.task_id,
                    visibility="debug",
                    source=str(event.get("source") or result.worker_type),
                    actor=actor,
                    parent_span_id=parent_span_id,
                    span_id=f"{parent_span_id}:event-{index}" if parent_span_id else None,
                )
            if result.proposed_actions:
                self._repository.append_event(
                    session_id,
                    "worker_proposed_action",
                    {"count": len(result.proposed_actions)},
                    run_id=run_id,
                    task_id=result.task_id,
                    visibility="debug",
                    source=result.worker_type,
                    actor=actor,
                    parent_span_id=parent_span_id,
                    span_id=f"{parent_span_id}:proposed-action" if parent_span_id else None,
                )
        updated_tasks = self._ledger.apply_worker_results(session_id, run_id, worker_results, actor=actor)
        return worker_results, updated_tasks

    def _run_ready_tasks(
        self,
        session_id: int,
        run_id: int,
        ready_tasks: list[TaskItem],
        message: str,
        actor: str,
    ) -> list[WorkerResult]:
        if self._async_worker_runtime is None:
            return self._scheduler.run(ready_tasks, message)
        async_tasks: list[TaskItem] = []
        legacy_tasks: list[TaskItem] = []
        for task in ready_tasks:
            if self._async_worker_runtime.supports(task):
                async_tasks.append(task)
            else:
                legacy_tasks.append(task)
        async_results = self._async_worker_runtime.start_many_and_wait(
            self._repository,
            session_id=session_id,
            parent_run_id=run_id,
            tasks=async_tasks,
            message=message,
            actor=actor,
        )
        return sorted([*async_results, *self._scheduler.run(legacy_tasks, message)], key=lambda result: result.task_id)

    def _finalize(
        self,
        session_id: int,
        run_id: int,
        observation: CoreObservation,
        actor: str,
    ) -> AssistantTurnResult:
        worker_results = list(observation.action_result.get("workerResults") or [])
        task_rows = self._repository.list_tasks(session_id)
        action_rows = self._repository.list_proposed_actions(session_id)
        task_summaries = [_format_task(row) for row in task_rows]
        proposed_actions = _sort_formatted_actions([_format_action(row) for row in action_rows])
        recommendation_started_at = datetime.now()
        self._repository.append_event(
            session_id,
            "recommendation_started",
            {
                "taskCount": len(task_summaries),
                "proposedActionCount": len(proposed_actions),
                "startedAt": _iso(recommendation_started_at),
            },
            run_id=run_id,
            actor=actor,
        )
        result = self._aggregator.aggregate(
            run_id=run_id,
            session_id=session_id,
            task_summaries=task_summaries,
            worker_results=worker_results,
            proposed_actions=proposed_actions,
            events=[],
        )
        pending_warnings = _worker_result_warnings(worker_results)
        if pending_warnings:
            result = replace(result, warnings=[*result.warnings, *pending_warnings])
        result = self._select_recommendation(
            session_id,
            run_id,
            actor,
            task_summaries,
            result,
        )
        result = self._select_two_stage_recommendation(
            session_id,
            run_id,
            actor,
            task_summaries,
            proposed_actions,
            result,
            observation,
        )
        self._ensure_reply_draft_delivery_action(session_id, run_id, actor, result)
        action_rows = self._repository.list_proposed_actions(session_id)
        proposed_actions = _sort_formatted_actions([_format_action(row) for row in action_rows])
        result = replace(result, proposed_actions=proposed_actions)
        recommendation_completed_at = datetime.now()
        recommendation_timing = {
            "taskCount": len(task_summaries),
            "proposedActionCount": len(proposed_actions),
            "startedAt": _iso(recommendation_started_at),
            "completedAt": _iso(recommendation_completed_at),
            "elapsedMs": _elapsed_ms(recommendation_started_at, recommendation_completed_at),
        }
        self._repository.append_event(
            session_id,
            "recommendation_completed",
            recommendation_timing,
            run_id=run_id,
            actor=actor,
        )
        self._record_recommendation_shadow(
            session_id=session_id,
            run_id=run_id,
            task_summaries=task_summaries,
            result=result,
            actor=actor,
        )
        self._repository.append_event(
            session_id,
            "recommendation_generated",
            recommendation_timing,
            run_id=run_id,
            actor=actor,
        )
        self._repository.append_event(
            session_id,
            "run_completed",
            {"runId": run_id, "actor": actor},
            run_id=run_id,
            actor=actor,
        )
        return replace(result, events=[_format_event(row) for row in self._repository.list_events(session_id)])

    def _ensure_reply_draft_delivery_action(
        self,
        session_id: int,
        run_id: int,
        actor: str,
        result: AssistantTurnResult,
    ) -> None:
        if not _is_task_backed_reply_draft(result.customer_reply_draft, result.task_summaries):
            return
        draft = str(result.customer_reply_draft or "").strip()
        if not _is_deliverable_reply_draft(draft, result.warnings):
            return
        action_key = f"reply-draft:{run_id}:send_customer_message"
        if any(str(action.get("action_key") or "") == action_key for action in self._repository.list_proposed_actions(session_id)):
            return
        session_row = self._repository.get_session(session_id)
        context = dict((session_row or {}).get("context_json") or {})
        payload = _reply_draft_delivery_payload(session_id, run_id, actor, draft, context)
        row = self._repository.upsert_proposed_action(
            session_id=session_id,
            run_id=run_id,
            task_id=None,
            action_key=action_key,
            action_type="send_customer_message",
            title="发送客户回复草稿",
            payload=payload,
        )
        self._repository.append_event(
            session_id,
            "reply_draft_proposed",
            {
                "actionId": int(row["id"]),
                "actionType": row["action_type"],
                "status": row["status"],
                "channel": payload["channel"],
                "conversationId": payload["conversationId"],
                "draftLength": len(draft),
            },
            run_id=run_id,
            source="customer_assistant_recommendation",
            actor=actor,
        )

    def _consume_completed_async_worker_results(self, session_id: int, actor: str) -> int:
        consumed = 0
        for row in self._repository.list_tasks(session_id):
            task = _task_item(row)
            if task.status != TaskStatus.RUNNING:
                continue
            refs = dict(task.last_result.get("workerAsyncRefs") or {})
            worker_run_id = str(refs.get("workerRunId") or "")
            if not worker_run_id:
                continue
            try:
                numeric_worker_run_id = parse_worker_run_public_id(worker_run_id)
            except ValueError:
                continue
            worker_run = self._repository.get_worker_run(numeric_worker_run_id)
            if worker_run is None or str(worker_run["status"]) not in {"COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED", "CANCEL_UNSUPPORTED"}:
                continue
            dispatched_version = _worker_run_task_version(worker_run)
            if dispatched_version is not None and int(row.get("version") or 0) != dispatched_version + 1:
                self._repository.append_event(
                    session_id,
                    "worker_result_stale",
                    {
                        "workerRunId": worker_run_id,
                        "taskId": task.id,
                        "taskVersion": row.get("version"),
                        "dispatchedTaskVersion": dispatched_version,
                    },
                    run_id=int(worker_run["parent_run_id"]),
                    task_id=task.id,
                    source="customer_assistant_worker",
                    actor=actor,
                )
                continue
            result = worker_result_from_worker_run(task, worker_run, refs=worker_async_refs(numeric_worker_run_id))
            self._ledger.apply_worker_results(
                session_id,
                int(worker_run["parent_run_id"]),
                [result],
                actor=actor,
            )
            self._repository.append_event(
                session_id,
                "worker_result_consumed",
                {"workerRunId": worker_run_id, "workerStatus": worker_run["status"], "taskId": task.id},
                run_id=int(worker_run["parent_run_id"]),
                task_id=task.id,
                source="customer_assistant_worker",
                actor=actor,
            )
            consumed += 1
        return consumed

    def _current_ledger(self, session_id: int) -> TaskLedger:
        return TaskLedger(
            session_id=session_id,
            tasks=tuple(_task_item(row) for row in self._repository.list_tasks(session_id)),
        )

    def _ensure_session(self, session_id: int) -> None:
        session = self._repository.get_session(session_id)
        if session is None:
            raise BizError(ErrorCode.NOT_FOUND, "Customer assistant session not found")
        self._ensure_session_owner(session)

    def _ensure_session_owner(self, session: dict[str, Any]) -> None:
        if self._request_context is None or _is_local_request_context(self._request_context):
            return
        context = dict(session.get("context_json") or {})
        host_context = context.get("hostContext")
        if not isinstance(host_context, dict):
            raise BizError(ErrorCode.FORBIDDEN, "Customer assistant session belongs to another tenant")
        if str(host_context.get("tenantId") or "") != self._request_context.tenant_id:
            raise BizError(ErrorCode.FORBIDDEN, "Customer assistant session belongs to another tenant")

    def _select_task_commands(
        self,
        session_id: int,
        run_id: int,
        message: str,
        actor: CustomerAssistantActor,
        baseline_commands: list[TaskCommand],
    ) -> list[TaskCommand]:
        if self._llm_runtime_settings.mode != CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK:
            return baseline_commands
        if self._llm_primary_client is None:
            self._append_llm_primary_event(
                session_id,
                run_id,
                actor,
                "llm_primary_fallback",
                {"phase": "task_recognition", "reason": "client_unavailable"},
            )
            return baseline_commands
        call_result = call_shadow(
            lambda: self._llm_primary_client.recognize_tasks(message=message, commands=baseline_commands),
            parse_task_recognition_shadow_output,
        )
        if not call_result.ok:
            self._append_llm_primary_event(
                session_id,
                run_id,
                actor,
                "llm_primary_fallback",
                {"phase": "task_recognition", "reason": "schema_failure", "error": call_result.error},
            )
            return baseline_commands
        confidence = _confidence(call_result.data.get("confidence"))
        if confidence < self._llm_runtime_settings.min_confidence:
            self._append_llm_primary_event(
                session_id,
                run_id,
                actor,
                "llm_primary_fallback",
                {
                    "phase": "task_recognition",
                    "reason": "low_confidence",
                    "confidence": confidence,
                    "minConfidence": self._llm_runtime_settings.min_confidence,
                },
            )
            return baseline_commands
        try:
            selected_commands = [_task_command_from_primary(command) for command in call_result.data["commands"]]
            CustomerAssistantActionPolicy().validate(selected_commands)
        except ValueError as exc:
            self._append_llm_primary_event(
                session_id,
                run_id,
                actor,
                "llm_primary_fallback",
                {"phase": "task_recognition", "reason": "unsupported_direct_write", "error": str(exc)},
            )
            return baseline_commands
        except (KeyError, TypeError, UnsupportedTaskCommand) as exc:
            self._append_llm_primary_event(
                session_id,
                run_id,
                actor,
                "llm_primary_fallback",
                {"phase": "task_recognition", "reason": "safety_or_policy_failure", "error": str(exc)},
            )
            return baseline_commands
        self._append_llm_primary_event(
            session_id,
            run_id,
            actor,
            "llm_primary_selected",
            {
                "phase": "task_recognition",
                "selectedSource": "llm_primary",
                "confidence": confidence,
                "commandCount": len(selected_commands),
            },
        )
        return selected_commands

    def _append_llm_primary_event(
        self,
        session_id: int,
        run_id: int,
        actor: CustomerAssistantActor,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self._repository.append_event(
            session_id,
            event_type,
            payload,
            run_id=run_id,
            visibility="debug",
            source="llm_primary",
            actor=actor,
        )

    def _select_recommendation(
        self,
        session_id: int,
        run_id: int,
        actor: CustomerAssistantActor,
        task_summaries: list[dict[str, Any]],
        baseline_result: AssistantTurnResult,
    ) -> AssistantTurnResult:
        if self._llm_runtime_settings.mode != CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK:
            return baseline_result
        if self._llm_primary_client is None:
            self._append_llm_primary_event(
                session_id,
                run_id,
                actor,
                "llm_primary_fallback",
                {"phase": "recommendation", "reason": "client_unavailable"},
            )
            return baseline_result
        call_result = call_shadow(
            lambda: self._llm_primary_client.recommend(
                task_summaries=task_summaries,
                operator_recommendation=baseline_result.operator_recommendation,
                customer_reply_draft=baseline_result.customer_reply_draft,
            ),
            parse_recommendation_shadow_output,
        )
        if not call_result.ok:
            self._append_llm_primary_event(
                session_id,
                run_id,
                actor,
                "llm_primary_fallback",
                {"phase": "recommendation", "reason": "schema_failure", "error": call_result.error},
            )
            return baseline_result
        self._append_llm_primary_event(
            session_id,
            run_id,
            actor,
            "llm_primary_selected",
            {"phase": "recommendation", "selectedSource": "llm_primary"},
        )
        return replace(
            baseline_result,
            operator_recommendation=str(call_result.data["operatorRecommendation"]),
            customer_reply_draft=str(call_result.data["customerReplyDraft"]),
            warnings=[*baseline_result.warnings, *list(call_result.data.get("warnings") or [])],
        )

    def _select_two_stage_recommendation(
        self,
        session_id: int,
        run_id: int,
        actor: CustomerAssistantActor,
        task_summaries: list[dict[str, Any]],
        proposed_actions: list[dict[str, Any]],
        baseline_result: AssistantTurnResult,
        observation: CoreObservation,
    ) -> AssistantTurnResult:
        mode = self._llm_runtime_settings.mode
        if mode not in {
            CustomerAssistantLlmRuntimeMode.TWO_STAGE_SHADOW,
            CustomerAssistantLlmRuntimeMode.TWO_STAGE_PRIMARY_WITH_FALLBACK,
        }:
            return baseline_result
        progression = _two_stage_react_progression(observation, task_summaries)
        self._record_two_stage_react_progression(session_id, run_id, actor, progression)
        input_pack = _two_stage_input_pack(task_summaries, proposed_actions, baseline_result, progression)
        candidate = self._two_stage_runtime.finalize(input_pack, baseline_result)
        validation_error = _two_stage_validation_error(candidate, input_pack)
        diff = _recommendation_diff(
            {
                "operatorRecommendation": baseline_result.operator_recommendation,
                "customerReplyDraft": baseline_result.customer_reply_draft,
            },
            candidate if isinstance(candidate, dict) else {},
        )
        promotion_gate = _two_stage_promotion_gate(diff)
        if mode == CustomerAssistantLlmRuntimeMode.TWO_STAGE_SHADOW:
            self._repository.append_event(
                session_id,
                "two_stage_shadow_completed",
                {
                    "schemaVersion": "customer_assistant.two_stage_shadow/1",
                    "reactStep": "final",
                    "legacyStage": "generate_recommendation",
                    "equivalence": {"passed": validation_error == "" and promotion_gate["passed"], "differences": diff},
                    "promotionGate": promotion_gate,
                    "sideEffects": {"extraWorkerDispatches": 0, "extraToolCalls": 0},
                },
                run_id=run_id,
                visibility="debug",
                source="two_stage_react",
                actor=actor,
            )
            return baseline_result
        fallback_reason = validation_error or ("" if promotion_gate["passed"] else "equivalence_threshold_failed")
        if fallback_reason:
            self._repository.append_event(
                session_id,
                "two_stage_fallback",
                {
                    "schemaVersion": "customer_assistant.two_stage_fallback/1",
                    "reactStep": "final",
                    "legacyStage": "generate_recommendation",
                    "reason": fallback_reason,
                    "equivalence": {"passed": False, "differences": diff},
                    "promotionGate": promotion_gate,
                },
                run_id=run_id,
                visibility="debug",
                source="two_stage_react",
                actor=actor,
            )
            return baseline_result
        self._repository.append_event(
            session_id,
            "two_stage_primary_selected",
            {
                "schemaVersion": "customer_assistant.two_stage_primary/1",
                "reactStep": "final",
                "legacyStage": "generate_recommendation",
                "equivalence": {"passed": True, "differences": diff},
                "promotionGate": promotion_gate,
            },
            run_id=run_id,
            visibility="debug",
            source="two_stage_react",
            actor=actor,
        )
        return replace(
            baseline_result,
            operator_recommendation=str(candidate["operatorRecommendation"]),
            customer_reply_draft=str(candidate["customerReplyDraft"]),
            warnings=[*baseline_result.warnings, *list(candidate.get("warnings") or [])],
        )

    def _record_two_stage_react_progression(
        self,
        session_id: int,
        run_id: int,
        actor: CustomerAssistantActor,
        progression: list[dict[str, Any]],
    ) -> None:
        for step in progression:
            self._repository.append_event(
                session_id,
                f"two_stage_{step['reactStep']}_recorded",
                step,
                run_id=run_id,
                visibility="debug",
                source="two_stage_react",
                actor=actor,
                span_id=f"run-{run_id}:two-stage:{step['reactStep']}",
            )

    def _record_task_recognition_shadow(
        self,
        session_id: int,
        run_id: int,
        message: str,
        commands: list[TaskCommand],
        actor: str,
    ) -> None:
        if not self._shadow_enabled(ShadowPhase.TASK_RECOGNITION):
            return
        baseline = {"commands": [self._command_payload_with_profile_refs(command) for command in commands]}
        self._append_shadow_event(
            session_id,
            run_id,
            "llm_shadow_started",
            ShadowPhase.TASK_RECOGNITION,
            actor,
            baseline=baseline,
        )
        call_result = call_shadow(
            lambda: self._shadow_client.recognize_tasks(message=message, commands=commands),  # type: ignore[union-attr]
            parse_task_recognition_shadow_output,
        )
        self._record_shadow_call_result(
            session_id,
            run_id,
            ShadowPhase.TASK_RECOGNITION,
            actor,
            baseline,
            call_result,
            _task_recognition_diff(baseline, call_result.data) if call_result.ok else None,
        )

    def _record_recommendation_shadow(
        self,
        *,
        session_id: int,
        run_id: int,
        task_summaries: list[dict[str, Any]],
        result: AssistantTurnResult,
        actor: str,
    ) -> None:
        if not self._shadow_enabled(ShadowPhase.RECOMMENDATION):
            return
        baseline = {
            "operatorRecommendation": result.operator_recommendation,
            "customerReplyDraft": result.customer_reply_draft,
            "taskSummaries": task_summaries,
        }
        self._append_shadow_event(
            session_id,
            run_id,
            "llm_shadow_started",
            ShadowPhase.RECOMMENDATION,
            actor,
            baseline=baseline,
        )
        call_result = call_shadow(
            lambda: self._shadow_client.recommend(  # type: ignore[union-attr]
                task_summaries=task_summaries,
                operator_recommendation=result.operator_recommendation,
                customer_reply_draft=result.customer_reply_draft,
            ),
            parse_recommendation_shadow_output,
        )
        self._record_shadow_call_result(
            session_id,
            run_id,
            ShadowPhase.RECOMMENDATION,
            actor,
            baseline,
            call_result,
            _recommendation_diff(baseline, call_result.data) if call_result.ok else None,
        )

    def _record_shadow_call_result(
        self,
        session_id: int,
        run_id: int,
        phase: ShadowPhase,
        actor: str,
        baseline: dict[str, Any],
        call_result: ShadowCallResult,
        diff: dict[str, Any] | None,
    ) -> None:
        if not call_result.ok:
            self._append_shadow_event(
                session_id,
                run_id,
                "llm_shadow_failed",
                phase,
                actor,
                baseline=baseline,
                latency_ms=call_result.latency_ms,
                error=call_result.error,
            )
            return
        self._append_shadow_event(
            session_id,
            run_id,
            "llm_shadow_completed",
            phase,
            actor,
            baseline=baseline,
            shadow=call_result.data,
            latency_ms=call_result.latency_ms,
        )
        self._append_shadow_event(
            session_id,
            run_id,
            "llm_shadow_diff_recorded",
            phase,
            actor,
            baseline=baseline,
            shadow=call_result.data,
            diff=diff,
            latency_ms=call_result.latency_ms,
        )

    def _append_shadow_event(
        self,
        session_id: int,
        run_id: int,
        event_type: str,
        phase: ShadowPhase,
        actor: str,
        *,
        baseline: dict[str, Any] | None = None,
        shadow: dict[str, Any] | None = None,
        diff: dict[str, Any] | None = None,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        self._repository.append_event(
            session_id,
            event_type,
            build_shadow_event_payload(
                phase=phase,
                mode=self._shadow_settings.mode,
                model_config_id=self._shadow_settings.model_config_id,
                actor=actor,
                baseline=baseline,
                shadow=shadow,
                diff=diff,
                latency_ms=latency_ms,
                error=error,
            ),
            run_id=run_id,
            visibility="debug",
            source="llm_shadow",
            actor=actor,
        )

    def _shadow_enabled(self, phase: ShadowPhase) -> bool:
        if self._shadow_settings.mode == "off" or self._shadow_client is None:
            return False
        if phase == ShadowPhase.TASK_RECOGNITION:
            return self._shadow_settings.task_recognition_enabled
        return self._shadow_settings.recommendation_enabled


def _request_hash(message: str, actor: str, turn_mode: CustomerAssistantTurnMode | None = None) -> str:
    raw = json.dumps(
        {"actor": actor, "message": message, "turnMode": turn_mode.value if turn_mode else None},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _format_session(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "context": row.get("context_json") or {},
        "version": row.get("version") or 1,
        "createdAt": _iso(row.get("created_at")),
        "updatedAt": _iso(row.get("updated_at")),
    }


def _session_context_with_host_context(
    context: dict[str, Any] | None,
    request_context: RequestContext | None,
) -> dict[str, Any]:
    sanitized = sanitize_value(context or {})
    session_context = dict(sanitized) if isinstance(sanitized, dict) else {"value": sanitized}
    if request_context is not None and _should_record_host_context(request_context):
        session_context["hostContext"] = sanitize_value(request_context.audit_metadata())
    return session_context


def _is_deliverable_reply_draft(draft: str, warnings: list[str]) -> bool:
    if not draft:
        return False
    if draft == "暂无可发送给客户的草稿。":
        return False
    return not any("required worker evidence is pending" in str(warning) for warning in warnings)


def _is_task_backed_reply_draft(customer_reply_draft: str, task_summaries: list[dict[str, Any]]) -> bool:
    draft = str(customer_reply_draft or "").strip()
    if not draft:
        return False
    for task in task_summaries:
        last_result = task.get("lastResult") if isinstance(task.get("lastResult"), dict) else {}
        task_draft = str(last_result.get("customerReplyDraft") or "").strip()
        if task_draft and (draft == task_draft or task_draft in draft):
            return True
    return False


def _reply_draft_delivery_payload(
    session_id: int,
    run_id: int,
    actor: str,
    draft: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    customer = context.get("customer") if isinstance(context.get("customer"), dict) else {}
    payload = {
        "channel": str(context.get("channel") or context.get("sourceChannel") or "mock_web"),
        "conversationId": str(
            context.get("conversationId")
            or context.get("conversation_id")
            or f"customer-assistant-session-{session_id}"
        ),
        "recipient": dict(customer),
        "draft": draft,
        "metadata": {
            "source": "customer_assistant_recommendation",
            "sessionId": session_id,
            "runId": run_id,
            "actor": actor,
        },
    }
    return sanitize_value(payload)


def customer_assistant_worker_profile_scope(request_context: RequestContext | None) -> tuple[str, str]:
    if request_context is None or _is_local_request_context(request_context):
        return "local", "local"
    return request_context.tenant_id or "default", request_context.org_id or "default"


def _should_record_host_context(request_context: RequestContext) -> bool:
    return any(
        (
            request_context.actor_id != "local-user",
            request_context.actor_name not in {"local-user", "Local User"},
            request_context.tenant_id != "local",
            request_context.org_id != "local",
            bool(request_context.roles),
            bool(request_context.permissions),
            bool(request_context.request_id),
            request_context.source != "local",
            request_context.locale != "zh-CN",
        )
    )


def _is_local_request_context(request_context: RequestContext) -> bool:
    return (
        request_context.source == "local"
        and request_context.actor_id == "local-user"
        and request_context.actor_name in {"local-user", "Local User"}
        and request_context.tenant_id == "local"
        and request_context.org_id == "local"
        and not request_context.roles
        and not request_context.permissions
        and not request_context.request_id
    )


def _format_demo_story(row: dict[str, Any], repository: CustomerAssistantRepository) -> dict[str, Any]:
    context = dict(row.get("context_json") or {})
    customer = dict(context.get("customer") or {})
    session_id = int(row["id"])
    tasks = repository.list_tasks(session_id)
    actions = repository.list_proposed_actions(session_id)
    return {
        "storyId": str(context.get("storyId") or context.get("demoSeedKey") or session_id),
        "title": str(context.get("storyTitle") or "未命名演示故事"),
        "sessionId": session_id,
        "sessionStatus": str(row.get("status") or "UNKNOWN"),
        "customerName": sanitize_text(str(customer.get("name") or "演示客户")),
        "maskedPhone": sanitize_text(str(customer.get("phone") or "")),
        "openingMessage": sanitize_text(str(context.get("openingMessage") or "")),
        "taskCount": len(tasks),
        "pendingActionCount": sum(1 for action in actions if str(action.get("status")) == "PENDING"),
        "knowledgeBaseIds": [int(item) for item in list(context.get("knowledgeBaseIds") or [])],
        "chatflowBindings": dict(context.get("chatflowBindings") or {}),
    }


def _demo_story_sort_key(story: dict[str, Any]) -> tuple[int, str]:
    story_id = str(story.get("storyId") or "")
    try:
        return (_MVP_DEMO_STORY_ORDER.index(story_id), story_id)
    except ValueError:
        return (len(_MVP_DEMO_STORY_ORDER), story_id)


def _count_values(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "UNKNOWN")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value)


def _human_confirmation(action_status_counts: dict[str, int]) -> dict[str, Any]:
    adopted = action_status_counts.get("CONFIRMED", 0) + action_status_counts.get("EXECUTED", 0)
    terminal = sum(
        action_status_counts.get(status, 0)
        for status in ("CONFIRMED", "REJECTED", "EXECUTED", "FAILED")
    )
    return {
        "pending": action_status_counts.get("PENDING", 0),
        "adopted": adopted,
        "terminal": terminal,
        "adoptionRate": round(adopted / terminal, 3) if terminal else 0.0,
    }


def _session_metrics_payload(
    session_id: int,
    tasks: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    task_status_counts = _count_values(tasks, "status")
    action_status_counts = _count_values(actions, "status")
    event_type_counts = _count_values(events, "type")
    event_source_counts = _count_values(events, "source")
    return {
        "sessionId": session_id,
        "taskStatusCounts": task_status_counts,
        "proposedActionStatusCounts": action_status_counts,
        "humanConfirmation": _human_confirmation(action_status_counts),
        "eventCounts": {
            "total": len(events),
            "byType": event_type_counts,
            "bySource": event_source_counts,
        },
        "workerEventCounts": _worker_event_counts(events),
        "recentFailureReasons": _recent_failure_reasons(tasks),
    }


def _worker_event_counts(events: list[dict[str, Any]]) -> dict[str, Any]:
    worker_events = [
        row for row in events
        if str(row.get("type") or "").startswith(("worker_", "task_"))
        or str(row.get("source") or "") in {"chatflow_sop", "stub_qa", "react_worker"}
    ]
    return {
        "total": len(worker_events),
        "byType": _count_values(worker_events, "type"),
    }


def _recent_failure_reasons(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    for task in tasks:
        if str(task.get("status") or "") != "FAILED":
            continue
        last_result = sanitize_value(dict(task.get("last_result_json") or {}))
        reason = _failure_reason_text(last_result)
        if not reason:
            continue
        reasons.append(
            {
                "taskId": int(task["id"]),
                "taskType": str(task.get("task_type") or "UNKNOWN"),
                "source": str(task.get("worker_type") or "customer_assistant"),
                "reason": sanitize_text(reason),
            }
        )
    return reasons[-5:]


def _failure_reason_text(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("error", "message", "reason", "status"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item
        for item in value.values():
            nested = _failure_reason_text(item)
            if nested:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _failure_reason_text(item)
            if nested:
                return nested
    if isinstance(value, str):
        return value
    return ""


def _format_task(row: dict[str, Any]) -> dict[str, Any]:
    last_result = sanitize_value(row.get("last_result_json") or {})
    return {
        "id": row["id"],
        "sessionId": row["session_id"],
        "taskKey": row["task_key"],
        "taskType": row["task_type"],
        "businessKey": sanitize_text(str(row["business_key"])),
        "shortId": row["short_id"],
        "status": row["status"],
        "workerType": row["worker_type"],
        "workerRef": row["worker_ref"],
        "checkpoint": sanitize_value(row.get("checkpoint_json") or {}),
        "lastResult": last_result,
        "workerAsyncRefs": last_result.get("workerAsyncRefs") or _unsupported_worker_async_refs(),
        "proposedActions": sanitize_value(row.get("proposed_actions_json") or []),
        "version": row.get("version") or 1,
    }


def _worker_profile_refs(profile: CustomerAssistantWorkerProfile) -> dict[str, Any]:
    return {
        "profileId": profile.profile_id,
        "modelPolicyRef": profile.model_policy_ref,
        "promptRef": profile.prompt_ref,
        "riskPolicyRef": profile.risk_policy_ref,
        "toolRefs": list(profile.tool_refs),
    }


def _validate_worker_profile(profile: CustomerAssistantWorkerProfile) -> None:
    missing = [
        field_name
        for field_name, value in {
            "profileId": profile.profile_id,
            "taskKey": profile.task_key,
            "taskType": profile.task_type,
            "workerType": profile.worker_type,
            "workerRef": profile.worker_ref,
        }.items()
        if not str(value or "").strip()
    ]
    if missing:
        raise BizError(ErrorCode.BAD_REQUEST, f"Missing worker profile fields: {', '.join(missing)}")


def _format_event(row: dict[str, Any]) -> dict[str, Any]:
    formatted = {
        "id": row["id"],
        "sessionId": row["session_id"],
        "runId": row.get("run_id"),
        "sequence": row["sequence"],
        "type": row["type"],
        "visibility": row["visibility"],
        "source": row["source"],
        "actor": row.get("actor") or (row.get("payload") or {}).get("actor") or DEFAULT_CUSTOMER_ASSISTANT_ACTOR,
        "taskId": row.get("task_id"),
        "parentSpanId": row.get("parent_span_id"),
        "spanId": row.get("span_id"),
        "payload": sanitize_value(row.get("payload") or {}),
        "createdAt": _iso(row.get("created_at")),
    }
    formatted["observability"] = _event_observability(formatted)
    return formatted


_OPERATOR_AUDIT_EVENT_TITLES = {
    "task_control_proposed": "任务控制已提出",
    "proposed_task_command_confirmed": "任务控制已确认",
    "proposed_action_modified": "拟议动作已修改",
    "proposed_action_confirmed": "拟议动作已确认",
    "proposed_action_rejected": "拟议动作已拒绝",
    "proposed_action_executing": "拟议动作执行中",
    "proposed_action_executed": "拟议动作已执行",
    "proposed_action_failed": "拟议动作执行失败",
    "draft_delivery_started": "草稿发送中",
    "draft_delivery_sent": "草稿已发送",
    "draft_delivery_failed": "草稿发送失败",
    "reply_draft_proposed": "客户回复草稿待确认",
    "task_started": "任务已启动",
    "worker_started": "Worker 已启动",
    "worker_proposed_action": "Worker 产生拟议动作",
    "task_completed": "任务已完成",
    "task_failed": "任务失败",
    "worker_failed": "Worker 失败",
    "operator_advisory_context_packed": "坐席追问上下文已打包",
}

_OPERATOR_AUDIT_STATUS_BY_EVENT = {
    "task_control_proposed": "PENDING_CONFIRMATION",
    "proposed_task_command_confirmed": "CONFIRMED",
    "proposed_action_modified": "PENDING",
    "proposed_action_confirmed": "CONFIRMED",
    "proposed_action_rejected": "REJECTED",
    "proposed_action_executing": "EXECUTING",
    "proposed_action_executed": "EXECUTED",
    "proposed_action_failed": "FAILED",
    "draft_delivery_started": "DELIVERING",
    "draft_delivery_sent": "SENT",
    "draft_delivery_failed": "FAILED",
    "reply_draft_proposed": "PENDING",
    "task_started": "RUNNING",
    "worker_started": "RUNNING",
    "worker_proposed_action": "PENDING_CONFIRMATION",
    "task_completed": "COMPLETED",
    "task_failed": "FAILED",
    "worker_failed": "FAILED",
    "operator_advisory_context_packed": "PACKED",
}


def _operator_audit_row(row: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(row["type"])
    title = _OPERATOR_AUDIT_EVENT_TITLES.get(event_type)
    if title is None:
        return None
    payload = sanitize_value(row.get("payload") or {})
    if not isinstance(payload, dict):
        payload = {}
    target_type, target_id = _operator_audit_target(row, payload)
    return {
        "id": int(row["id"]),
        "sequence": int(row["sequence"]),
        "eventType": event_type,
        "title": title,
        "actor": sanitize_text(str(row.get("actor") or payload.get("actor") or "system")),
        "source": sanitize_text(str(row.get("source") or "customer_assistant")),
        "status": str(payload.get("status") or _OPERATOR_AUDIT_STATUS_BY_EVENT[event_type]),
        "targetType": target_type,
        "targetId": target_id,
        "summary": _operator_audit_summary(event_type, row, payload),
        "createdAt": _iso(row.get("created_at")),
    }


def _operator_audit_target(row: dict[str, Any], payload: dict[str, Any]) -> tuple[str, int | None]:
    if payload.get("actionId") is not None:
        return "action", _optional_audit_int(payload.get("actionId"))
    task_id = row.get("task_id") or payload.get("taskId")
    if task_id is not None:
        return "task", _optional_audit_int(task_id)
    if payload.get("workerRunId") is not None:
        return "worker", None
    return "session", int(row["session_id"])


def _operator_audit_summary(event_type: str, row: dict[str, Any], payload: dict[str, Any]) -> str:
    if event_type == "task_control_proposed":
        return sanitize_text(
            f"{payload.get('controlType') or 'control'} requested for "
            f"{payload.get('taskKey') or row.get('task_id') or 'task'}"
        )
    if event_type == "proposed_action_modified":
        changed = payload.get("changedFields")
        changed_text = ", ".join(map(str, changed)) if isinstance(changed, list) else "unknown"
        return sanitize_text(f"changed fields: {changed_text}")
    if event_type.startswith("proposed_action") or event_type == "proposed_task_command_confirmed":
        task_command = payload.get("taskCommand") if isinstance(payload.get("taskCommand"), dict) else {}
        action_type = payload.get("actionType") or task_command.get("type") or "action"
        return sanitize_text(f"{action_type} {payload.get('status') or _OPERATOR_AUDIT_STATUS_BY_EVENT[event_type]}")
    if event_type.startswith("draft_delivery"):
        delivery = payload.get("delivery") if isinstance(payload.get("delivery"), dict) else {}
        channel = delivery.get("channel") or payload.get("channel") or "mock_channel"
        return sanitize_text(f"{channel} {payload.get('status') or _OPERATOR_AUDIT_STATUS_BY_EVENT[event_type]}")
    if event_type == "reply_draft_proposed":
        channel = payload.get("channel") or "mock_channel"
        return sanitize_text(f"{channel} {_OPERATOR_AUDIT_STATUS_BY_EVENT[event_type]}")
    if event_type in {"task_started", "task_completed", "task_failed"}:
        return sanitize_text(
            f"{payload.get('taskKey') or row.get('task_id') or 'task'} {_OPERATOR_AUDIT_STATUS_BY_EVENT[event_type]}"
        )
    if event_type in {"worker_started", "worker_failed", "worker_proposed_action"}:
        worker_ref = payload.get("workerRunId") or payload.get("workerType") or row.get("source") or "worker"
        return sanitize_text(f"{worker_ref} {_OPERATOR_AUDIT_STATUS_BY_EVENT[event_type]}")
    if event_type == "operator_advisory_context_packed":
        return sanitize_text(
            f"{payload.get('taskCount') or 0} tasks, {payload.get('knowledgeSnippetCount') or 0} knowledge snippets"
        )
    return sanitize_text(event_type)


def _optional_audit_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_worker_run(row: dict[str, Any]) -> dict[str, Any]:
    worker_run_id = int(row["id"])
    return {
        "id": worker_run_id,
        "workerRunId": worker_async_refs(worker_run_id)["workerRunId"],
        "sessionId": row["session_id"],
        "parentRunId": row["parent_run_id"],
        "taskId": row["task_id"],
        "workerType": row["worker_type"],
        "workerRef": row["worker_ref"],
        "status": row["status"],
        "refs": worker_async_refs(worker_run_id),
        "queuedAt": _iso(row.get("queued_at")),
        "startedAt": _iso(row.get("started_at")),
        "completedAt": _iso(row.get("completed_at")),
    }


def _format_worker_event(row: dict[str, Any]) -> dict[str, Any]:
    formatted = {
        "id": row["id"],
        "workerRunId": worker_async_refs(int(row["worker_run_id"]))["workerRunId"],
        "sequence": row["sequence"],
        "type": row["type"],
        "visibility": row["visibility"],
        "source": row["source"],
        "actor": row.get("actor") or "system",
        "payload": sanitize_value(row.get("payload") or {}),
        "createdAt": _iso(row.get("created_at")),
    }
    formatted["observability"] = _worker_event_observability(formatted)
    return formatted


def _event_observability(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event.get("payload") or {})
    payload_source = str(payload.get("source") or "")
    runtime_refs = dict(payload.get("chatflowRuntimeRefs") or payload.get("runtimeRefs") or {})
    profile_refs = _profile_refs_from_payload(payload)
    worker_run_id = (
        payload.get("workerRunId")
        or dict(payload.get("workerAsyncRefs") or {}).get("workerRunId")
        or dict(payload.get("refs") or {}).get("workerRunId")
    )
    summary: dict[str, Any] = {
        "sourceKind": _summary_source_kind(str(event.get("source") or ""), payload_source),
        "eventMode": _summary_event_mode(event, payload_source),
        "correlationRefs": {
            "assistantRunId": _optional_int(event.get("runId")),
            "taskId": _optional_int(event.get("taskId")),
            "workerRunId": worker_run_id,
            "runtimeRunId": _optional_int(payload.get("runtimeRunId") or payload.get("runId") or runtime_refs.get("runId")),
            "sourceEventId": _optional_int(payload.get("sourceEventId")) or _optional_int(event.get("id")),
            "sourceSequence": _optional_int(payload.get("sourceSequence")) or _optional_int(event.get("sequence")),
        },
    }
    if profile_refs:
        summary["profileRefs"] = profile_refs
    return summary


def _worker_event_observability(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event.get("payload") or {})
    profile_refs = _profile_refs_from_payload(payload)
    summary: dict[str, Any] = {
        "sourceKind": _summary_source_kind(str(event.get("source") or ""), str(payload.get("source") or "")),
        "eventMode": "live",
        "correlationRefs": {
            "workerRunId": event.get("workerRunId"),
            "runtimeRunId": _optional_int(payload.get("runtimeRunId") or payload.get("runId")),
            "sourceEventId": _optional_int(payload.get("sourceEventId")) or _optional_int(event.get("id")),
            "sourceSequence": _optional_int(payload.get("sourceSequence")) or _optional_int(event.get("sequence")),
        },
    }
    if profile_refs:
        summary["profileRefs"] = profile_refs
    return summary


def _profile_refs_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    refs = payload.get("profileRefs")
    return dict(refs) if isinstance(refs, dict) else {}


def _summary_source_kind(source: str, payload_source: str) -> str:
    signal = payload_source or source
    if signal.startswith("chatflow_") or signal == "chatflow_sop":
        return "chatflow"
    if signal.startswith("workflow_"):
        return "workflow"
    if signal in {"customer_assistant_worker", "stub_qa", "react_worker"}:
        return "worker"
    if signal == "customer_assistant":
        return "assistant"
    return "runtime" if signal.endswith("_runtime_v2") else "worker"


def _summary_event_mode(event: dict[str, Any], payload_source: str) -> str:
    if payload_source.endswith("_runtime_v2") and str(event.get("type") or "") == "worker_result_received":
        return "compatibility_summary"
    if event.get("replayed") is True:
        return "replay"
    return "live"


def _format_action(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "sessionId": row["session_id"],
        "runId": row["run_id"],
        "taskId": row.get("task_id"),
        "actionKey": sanitize_text(str(row["action_key"])),
        "actionType": row["action_type"],
        "title": row["title"],
        "payload": sanitize_value(row.get("payload") or {}),
        "status": row["status"],
        "result": sanitize_value(row.get("result_json") or {}),
    }


def _sort_formatted_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(actions, key=_formatted_action_sort_key)


def _formatted_action_sort_key(action: dict[str, Any]) -> tuple[int, int, int]:
    action_type = str(action.get("actionType") or "")
    if action_type == "PROPOSED_TASK_COMMAND":
        priority = 0
    elif action_type == "send_customer_message":
        priority = 2
    else:
        priority = 1
    task_priority = 0 if action.get("taskId") is not None else 1
    return (priority, task_priority, int(action.get("id") or 0))


def _turn_result_payload(result: AssistantTurnResult, *, replayed: bool) -> dict[str, Any]:
    return {
        "runId": result.run_id,
        "sessionId": result.session_id,
        "replyType": result.reply_type,
        "operatorRecommendation": sanitize_text(result.operator_recommendation),
        "customerReplyDraft": sanitize_text(result.customer_reply_draft),
        "taskSummaries": result.task_summaries,
        "proposedActions": result.proposed_actions,
        "warnings": sanitize_value(result.warnings),
        "events": result.events,
        "replayed": replayed,
    }


def _sub_agent_run_payload(*, run_id: int, session_id: int, status: str) -> dict[str, Any]:
    return {
        "subAgentRunId": sub_agent_run_public_id(run_id),
        "runId": run_id,
        "sessionId": session_id,
        "agentType": "customer_assistant",
        "status": status,
        "eventStreamRef": event_stream_ref(session_id, after_sequence=0),
        "resultRef": result_ref(run_id),
        "cancellation": unsupported_cancellation(),
        "workerAsyncRefs": reserved_worker_async_refs(run_id=run_id, session_id=session_id),
    }


def _sub_agent_status(status: str) -> str:
    return {
        "RUNNING": "running",
        "COMPLETED": "completed",
        "FAILED": "failed",
        "CANCELLED": "cancelled",
        "WAITING": "waiting",
    }.get(status.upper(), status.lower())


def _unsupported_worker_async_refs() -> dict[str, Any]:
    return {
        "supported": False,
        "workerRunId": None,
        "workerStatusRef": None,
        "workerEventsRef": None,
        "workerEventStreamRef": None,
        "workerResultRef": None,
        "reason": "No durable async worker run exists for this task.",
    }


def _worker_result_warnings(worker_results: list[WorkerResult]) -> list[str]:
    warnings: list[str] = []
    for result in worker_results:
        if result.status == TaskStatus.RUNNING:
            warnings.append(
                f"required worker evidence is pending for task {result.task_id}; "
                f"poll {result.worker_async_refs.get('workerStatusRef')} for completion."
            )
        elif result.status == TaskStatus.FAILED:
            warnings.append(f"worker failed for task {result.task_id}; inspect worker events before replying.")
    return warnings


def _worker_run_task_version(worker_run: dict[str, Any]) -> int | None:
    task_payload = dict((worker_run.get("input_payload") or {}).get("task") or {})
    raw = task_payload.get("taskVersion")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _run_id_from_worker_run_id(worker_run_id: str) -> int:
    prefix = "customer-assistant-worker-run-"
    if not worker_run_id.startswith(prefix):
        raise BizError(ErrorCode.BAD_REQUEST, "Invalid customer assistant worker run id")
    raw = worker_run_id.removeprefix(prefix)
    try:
        return int(raw)
    except ValueError as exc:
        raise BizError(ErrorCode.BAD_REQUEST, "Invalid customer assistant worker run id") from exc


def _task_command_from_primary(command: dict[str, Any]) -> TaskCommand:
    return TaskCommand(
        type=TaskCommandType(str(command["type"])),
        task_key=str(command["taskKey"]),
        task_type=str(command["taskType"]),
        business_key=str(command["businessKey"]),
        worker_type=str(command["workerType"]),
        worker_ref=str(command["workerRef"]),
        reason=str(command.get("reason") or "llm_primary"),
    )


def _task_command_from_proposed_payload(command: dict[str, Any]) -> TaskCommand:
    try:
        command_type = TaskCommandType(str(command["type"]))
    except (KeyError, ValueError) as exc:
        raise BizError(ErrorCode.BAD_REQUEST, "Invalid proposed task command") from exc
    return TaskCommand(
        type=command_type,
        task_key=str(command.get("taskKey") or ""),
        task_type=str(command.get("taskType") or ""),
        business_key=str(command.get("businessKey") or command.get("taskKey") or ""),
        worker_type=str(command.get("workerType") or ""),
        worker_ref=str(command.get("workerRef") or ""),
        reason=str(command.get("reason") or "operator_confirmed"),
        input_snapshot=dict(command.get("inputSnapshot") or command.get("input_snapshot") or {}),
    )


def _ensure_task_control_allowed(task: dict[str, Any], control_type: str) -> None:
    available = _available_task_controls(str(task.get("status") or ""))
    if control_type not in available:
        raise BizError(
            ErrorCode.BAD_REQUEST,
            f"Task control {control_type} is not allowed for status {task.get('status')}",
        )


def _available_task_controls(status: str) -> tuple[str, ...]:
    if status == TaskStatus.RUNNING.value or status == TaskStatus.PENDING.value:
        return ("cancel",)
    if status == TaskStatus.WAITING.value:
        return ("resume", "cancel")
    if status == TaskStatus.FAILED.value:
        return ("retry",)
    return ()


def _task_control_command(task: dict[str, Any], control_type: str, reason: str) -> TaskCommand:
    command_type = TaskCommandType.CANCEL_TASK if control_type == "cancel" else TaskCommandType.RESUME_TASK
    return TaskCommand(
        type=command_type,
        task_key=str(task["task_key"]),
        task_type=str(task["task_type"]),
        business_key=str(task["business_key"]),
        worker_type=str(task["worker_type"]),
        worker_ref=str(task["worker_ref"]),
        reason=reason or f"operator_{control_type}_control",
        input_snapshot=dict(task.get("input_snapshot_json") or {}),
    )


def _task_control_label(control_type: str) -> str:
    return {
        "retry": "重试任务",
        "cancel": "取消任务",
        "resume": "恢复任务",
    }.get(control_type, "任务控制")


def _task_control_request_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _confidence(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _command_payload(command: TaskCommand) -> dict[str, Any]:
    return {
        "type": command.type.value,
        "taskKey": command.task_key,
        "taskType": command.task_type,
        "businessKey": command.business_key,
        "workerType": command.worker_type,
        "workerRef": command.worker_ref,
        "reason": command.reason,
    }


def _operator_message_requests_task_mutation(message: str) -> bool:
    text = message.strip().lower()
    if not any(term in text for term in ("退票", "退款", "refund", "行李", "baggage")):
        return False
    return any(
        term in text
        for term in (
            "加入",
            "添加",
            "新增",
            "创建",
            "登记",
            "建一个",
            "建个",
            "生成任务",
            "加到",
            "add",
            "create",
        )
    )


def _operator_event_summary(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    return {
        "sequence": row.get("sequence"),
        "type": row.get("type"),
        "actor": row.get("actor"),
        "taskKey": payload.get("taskKey"),
        "source": row.get("source"),
    }


def _operator_evidence_from_tasks(task_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for task in task_summaries:
        last_result = dict(task.get("lastResult") or {})
        result_evidence = dict(last_result.get("evidence") or {})
        checkpoint = dict(task.get("checkpoint") or {})
        worker_type = str(task.get("workerType") or "").lower()
        if not result_evidence and worker_type not in {"chatflow_sop", "chatflow", "workflow"} and not checkpoint:
            continue
        evidence.append(
            {
                "taskKey": task.get("taskKey"),
                "sopId": result_evidence.get("sopId") or task.get("workerRef") or task.get("workerType"),
                "currentStep": result_evidence.get("currentStep")
                or checkpoint.get("currentStep")
                or checkpoint.get("pendingStep")
                or task.get("status"),
            }
        )
    return evidence


def _operator_knowledge_snippets(
    repository: KnowledgeBaseRepository,
    session_context: dict[str, Any],
    task_summaries: list[dict[str, Any]],
    message: str,
) -> list[dict[str, Any]]:
    knowledge_base_ids = _operator_knowledge_base_ids(session_context)
    if not knowledge_base_ids:
        return []
    terms = _operator_knowledge_terms(message, task_summaries)
    snippets: list[dict[str, Any]] = []
    for knowledge_base_id in knowledge_base_ids:
        for faq in repository.list_enabled_faqs(knowledge_base_id):
            score = _operator_faq_score(faq, terms)
            if score <= 0 and terms:
                continue
            snippets.append(
                {
                    "knowledgeBaseId": knowledge_base_id,
                    "faqId": int(faq["id"]),
                    "question": str(faq.get("question") or ""),
                    "answer": str(faq.get("answer") or ""),
                    "category": str(faq.get("category") or ""),
                    "score": score,
                }
            )
    snippets.sort(key=lambda item: (-int(item["score"]), str(item["question"])))
    return snippets[:3]


def _operator_knowledge_base_ids(session_context: dict[str, Any]) -> list[int]:
    ids: list[int] = []
    for item in list(session_context.get("knowledgeBaseIds") or []):
        try:
            parsed = int(item)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            ids.append(parsed)
    return ids


def _operator_knowledge_terms(message: str, task_summaries: list[dict[str, Any]]) -> set[str]:
    haystack = " ".join(
        [
            message,
            *[str(task.get("taskKey") or "") for task in task_summaries],
            *[str(task.get("taskType") or "") for task in task_summaries],
            *[str(task.get("workerRef") or "") for task in task_summaries],
        ]
    ).lower()
    candidates = {
        "退票",
        "退款",
        "refund",
        "行李",
        "行李额",
        "baggage",
        "发票",
        "invoice",
        "航班动态",
        "flight",
        "等待输入",
        "恢复",
        "resume",
        "改签",
        "change",
        "订单号",
    }
    return {term for term in candidates if term.lower() in haystack}


def _operator_faq_score(faq: dict[str, Any], terms: set[str]) -> int:
    if not terms:
        return int(faq.get("priority") or 0)
    faq_keywords = " ".join(str(item) for item in list(faq.get("keywords") or []))
    haystack = " ".join(
        [
            str(faq.get("question") or ""),
            str(faq.get("answer") or ""),
            str(faq.get("category") or ""),
            faq_keywords,
        ]
    ).lower()
    return sum(1 for term in terms if term.lower() in haystack)


def _operator_knowledge_qa_query(question: str, task_summaries: list[dict[str, Any]]) -> str:
    terms = sorted(_operator_knowledge_terms(question, task_summaries))
    if not terms:
        return question
    return " ".join([question, *terms])


def _operator_knowledge_qa_context_summary(
    session_id: int,
    session_context: dict[str, Any],
    task_summaries: list[dict[str, Any]],
    proposed_actions: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    customer = dict(session_context.get("customer") or {})
    return {
        "sessionId": session_id,
        "storyId": sanitize_text(str(session_context.get("storyId") or "")),
        "storyTitle": sanitize_text(str(session_context.get("storyTitle") or "")),
        "customer": {
            "name": sanitize_text(str(customer.get("name") or "")),
            "maskedPhone": sanitize_text(str(customer.get("phone") or "")),
        },
        "taskCount": len(task_summaries),
        "taskStatusCounts": _count_formatted_values(task_summaries, "status"),
        "taskTypes": sorted({sanitize_text(str(task.get("taskType") or "")) for task in task_summaries}),
        "workerRefs": sorted({sanitize_text(str(task.get("workerRef") or "")) for task in task_summaries}),
        "proposedActionCount": len(proposed_actions),
        "pendingActionCount": sum(1 for action in proposed_actions if action.get("status") == "PENDING"),
        "eventCount": len(event_rows),
        "latestEventTypes": [sanitize_text(str(row.get("type") or "")) for row in event_rows[-5:]],
        "knowledgeBaseIds": _operator_knowledge_base_ids(session_context),
    }


def _operator_knowledge_qa_evidence(task_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in _operator_evidence_from_tasks(task_summaries):
        task = _task_summary_by_key(task_summaries, str(item.get("taskKey") or ""))
        evidence.append(
            {
                "type": "TASK_LEDGER",
                "taskKey": sanitize_text(str(item.get("taskKey") or "")),
                "taskType": sanitize_text(str((task or {}).get("taskType") or "")),
                "status": sanitize_text(str((task or {}).get("status") or "")),
                "workerType": sanitize_text(str((task or {}).get("workerType") or "")),
                "workerRef": sanitize_text(str((task or {}).get("workerRef") or "")),
                "sopId": sanitize_text(str(item.get("sopId") or "")),
                "currentStep": sanitize_text(str(item.get("currentStep") or "")),
            }
        )
    return evidence


def _operator_knowledge_qa_source(
    knowledge_base_id: int,
    result: KnowledgeContextResult,
) -> dict[str, Any]:
    answer_excerpt = result.answer or result.content
    source = {
        "knowledgeBaseId": knowledge_base_id,
        "sourceType": sanitize_text(result.source_type),
        "matchType": sanitize_text(result.match_type),
        "score": round(float(result.score), 4),
        "title": sanitize_text(result.title),
        "answerExcerpt": sanitize_text(answer_excerpt)[:600],
    }
    if result.faq_id:
        source["faqId"] = result.faq_id
    if result.document_id:
        source["documentId"] = result.document_id
    if result.chunk_id:
        source["chunkId"] = result.chunk_id
        source["chunkIndex"] = result.chunk_index
    return source


def _operator_knowledge_qa_answer(
    question: str,
    sources: list[dict[str, Any]],
    context_summary: dict[str, Any],
    evidence: list[dict[str, Any]],
    warnings: list[str],
) -> str:
    lines: list[str] = []
    if sources:
        lines.append(str(sources[0].get("answerExcerpt") or sources[0].get("title") or ""))
    else:
        lines.append("未找到可引用的知识库答案，请按当前任务状态保守处理并继续人工确认。")
    task_count = int(context_summary.get("taskCount") or 0)
    if task_count:
        status_counts = dict(context_summary.get("taskStatusCounts") or {})
        status_text = ", ".join(f"{key}={value}" for key, value in sorted(status_counts.items()))
        lines.append(f"Current task ledger: {task_count} task(s), {status_text}.")
    proposed_action_count = int(context_summary.get("proposedActionCount") or 0)
    if proposed_action_count:
        pending_count = int(context_summary.get("pendingActionCount") or 0)
        lines.append(f"Proposed-action ledger: {proposed_action_count} action(s), pending={pending_count}.")
    if evidence:
        evidence_text = "; ".join(
            f"{item.get('taskType')} {item.get('status')} via {item.get('workerRef')}"
            for item in evidence[:3]
        )
        lines.append(f"Evidence summary: {evidence_text}.")
    if sources:
        lines.append(f"Primary source: {sources[0].get('title')} ({sources[0].get('matchType')}).")
    if warnings:
        lines.append(f"Warnings: {'; '.join(warnings)}")
    return sanitize_text("\n".join(line for line in lines if line))


def _count_formatted_values(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "UNKNOWN")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _task_summary_by_key(
    task_summaries: list[dict[str, Any]],
    task_key: str,
) -> dict[str, Any] | None:
    for task in task_summaries:
        if str(task.get("taskKey") or "") == task_key:
            return task
    return None


def _positive_int(value: Any, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(1, parsed))


def _operator_advisory_recommendation(
    message: str,
    context_pack: dict[str, Any],
    proposed_actions: list[dict[str, Any]],
) -> str:
    task_summaries = list(context_pack.get("taskSummaries") or [])
    event_summary = list(context_pack.get("eventSummary") or [])
    evidence = list(context_pack.get("evidence") or [])
    knowledge_snippets = list(context_pack.get("knowledgeSnippets") or [])
    warnings = list(context_pack.get("warnings") or [])
    lines = [f"Operator recommendation for: {message}"]
    if task_summaries:
        task_lines = [
            f"{task['taskKey']} status={task['status']} worker={task['workerType']}"
            for task in task_summaries
        ]
        lines.append(f"- task ledger: {'; '.join(task_lines)}")
    else:
        lines.append("- task ledger: no active customer task; do not mutate ledger without confirmation.")
    if event_summary:
        latest = ", ".join(str(event.get("type")) for event in event_summary[-5:])
        lines.append(f"- event summary: {len(event_summary)} event rows available; latest={latest}")
    if evidence:
        evidence_lines = [
            f"{item.get('taskKey')} SOP/Chatflow {item.get('sopId') or 'unknown'} step={item.get('currentStep')}"
            for item in evidence
        ]
        lines.append(f"- SOP/Chatflow evidence: {'; '.join(evidence_lines)}")
    if knowledge_snippets:
        snippet_lines = [
            f"{item.get('question')}: {item.get('answer')}"
            for item in knowledge_snippets
        ]
        lines.append(f"- knowledge snippets: {'; '.join(snippet_lines)}")
    if proposed_actions:
        titles = ", ".join(str(action.get("title") or action.get("actionType")) for action in proposed_actions)
        lines.append(f"- proposed_task_command: {titles}; pending explicit operator confirmation.")
    if warnings:
        lines.append(f"- warnings: {'; '.join(str(warning) for warning in warnings)}")
    return "\n".join(lines)


def _task_recognition_diff(baseline: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    baseline_commands = [_compact_command(command) for command in baseline.get("commands") or []]
    shadow_commands = [_compact_command(command) for command in shadow.get("commands") or []]
    differences: list[str] = []
    if baseline_commands != shadow_commands:
        differences.append("commands")
    return {"matches": not differences, "differences": differences}


def _recommendation_diff(baseline: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    differences: list[str] = []
    for key in ("operatorRecommendation", "customerReplyDraft"):
        if str(baseline.get(key) or "") != str(shadow.get(key) or ""):
            differences.append(key)
    if len(baseline.get("taskSummaries") or []) != len(shadow.get("taskSummaries") or []):
        differences.append("taskSummaries")
    return {"matches": not differences, "differences": differences}


def _two_stage_promotion_gate(diff: dict[str, Any]) -> dict[str, Any]:
    current_run_pass_rate = 1.0 if diff["matches"] else 0.0
    return {
        "suite": TWO_STAGE_EQUIVALENCE_SUITE,
        "minPassRate": TWO_STAGE_EQUIVALENCE_MIN_PASS_RATE,
        "currentRunPassRate": current_run_pass_rate,
        "passed": current_run_pass_rate >= TWO_STAGE_EQUIVALENCE_MIN_PASS_RATE,
    }


def _two_stage_input_pack(
    task_summaries: list[dict[str, Any]],
    proposed_actions: list[dict[str, Any]],
    baseline_result: AssistantTurnResult,
    react_progression: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    waiting_prompts = [
        prompt
        for task in task_summaries
        if str(task.get("status") or "").upper() == TaskStatus.WAITING.value
        for prompt in _task_waiting_prompts(task)
    ]
    return {
        "schemaVersion": "customer_assistant.two_stage_input/1",
        "taskSummaries": [dict(task) for task in task_summaries],
        "proposedActions": [dict(action) for action in proposed_actions],
        "baseline": {
            "operatorRecommendation": baseline_result.operator_recommendation,
            "customerReplyDraft": baseline_result.customer_reply_draft,
            "warnings": list(baseline_result.warnings),
        },
        "reactProgression": [dict(step) for step in react_progression or []],
        "waitingPrompts": waiting_prompts,
        "safety": {
            "directWritesAllowed": False,
            "highRiskWritesRequire": "proposed_action",
            "rawChainOfThoughtAllowed": False,
        },
    }


def _two_stage_react_progression(
    observation: CoreObservation,
    task_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    commands = [_compact_command(_command_payload(command)) for command in observation.commands]
    worker_results = list(observation.action_result.get("workerResults") or [])
    task_statuses = [
        {"taskKey": str(task.get("taskKey") or ""), "status": str(task.get("status") or "")}
        for task in task_summaries
    ]
    return [
        {
            "schemaVersion": "customer_assistant.two_stage_react_progression/1",
            "reactStep": "plan",
            "legacyStage": "task_recognition",
            "summary": {
                "commandCount": len(commands),
                "commands": commands,
            },
        },
        {
            "schemaVersion": "customer_assistant.two_stage_react_progression/1",
            "reactStep": "action",
            "legacyStage": "task_execute_parallel",
            "summary": {
                "commandCount": len(commands),
                "commands": commands,
                "workerDispatchCount": len(worker_results),
            },
        },
        {
            "schemaVersion": "customer_assistant.two_stage_react_progression/1",
            "reactStep": "observation",
            "legacyStage": "task_execute_parallel",
            "summary": {
                "workerResultCount": len(worker_results),
                "taskStatuses": task_statuses,
            },
        },
    ]


def _two_stage_validation_error(candidate: Any, input_pack: dict[str, Any]) -> str:
    if not isinstance(candidate, dict):
        return "schema_failure"
    if _contains_forbidden_reasoning_field(candidate):
        return "unsafe_reasoning_field"
    allowed_keys = {"schemaVersion", "operatorRecommendation", "customerReplyDraft", "warnings"}
    if set(candidate) - allowed_keys:
        return "unsupported_field"
    if not isinstance(candidate.get("operatorRecommendation"), str):
        return "schema_failure"
    if not isinstance(candidate.get("customerReplyDraft"), str):
        return "schema_failure"
    warnings = candidate.get("warnings", [])
    if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
        return "schema_failure"
    waiting_prompts = [str(prompt) for prompt in input_pack.get("waitingPrompts") or [] if str(prompt)]
    if waiting_prompts:
        baseline = dict(input_pack.get("baseline") or {})
        baseline_draft = str(baseline.get("customerReplyDraft") or "")
        draft = str(candidate["customerReplyDraft"])
        if baseline_draft in waiting_prompts and draft != baseline_draft:
            return "prompt_preservation_failed"
        for prompt in waiting_prompts:
            if prompt and prompt not in draft:
                return "prompt_preservation_failed"
    return ""


def _task_waiting_prompts(task: dict[str, Any]) -> list[str]:
    prompts: list[str] = []
    last_result = dict(task.get("lastResult") or {})
    checkpoint = dict(task.get("checkpoint") or last_result.get("checkpoint") or {})
    evidence = dict(last_result.get("evidence") or {})
    for source in (checkpoint, evidence, last_result):
        for key in ("pendingPrompt", "pending_prompt", "followup", "followUp", "prompt", "customerReplyDraft"):
            value = source.get(key)
            if isinstance(value, str) and value and value not in prompts:
                prompts.append(value)
    return prompts


def _contains_forbidden_reasoning_field(value: Any) -> bool:
    forbidden = {"chainofthought", "chain_of_thought", "reasoningtrace", "reasoning_trace", "rawthoughts"}
    if isinstance(value, dict):
        return any(str(key).replace("-", "_").lower() in forbidden or _contains_forbidden_reasoning_field(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_reasoning_field(item) for item in value)
    return False


def _compact_command(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": command.get("type"),
        "taskKey": command.get("taskKey"),
        "taskType": command.get("taskType"),
        "workerType": command.get("workerType"),
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _elapsed_ms(started_at: datetime, completed_at: datetime) -> int:
    return max(0, int((completed_at - started_at).total_seconds() * 1000))
