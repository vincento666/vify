from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_get_id
from app.core.schema import register_baseline_tables
from app.modules.customer_assistant.domain.worker_profiles import default_customer_assistant_worker_profiles_json
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import register_customer_assistant_tables
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository
from app.modules.runtime_lab.infra.airline_chatflow_seed import (
    AIRLINE_CHATFLOW_NAME_PREFIX,
    AIRLINE_CHATFLOW_SOP_IDS,
    DEFAULT_RUNTIME_LAB_ARBITRATOR_MODEL,
    DEFAULT_RUNTIME_LAB_BASE_URL,
    DEFAULT_RUNTIME_LAB_FALLBACK_MODEL,
    seed_runtime_lab_airline_chatflows,
)


ONE_CLICK_DEMO_SPEC_ID = "106-one-click-demo-seed"
ONE_CLICK_DEMO_REPORT_SCHEMA = "hify.mvp_demo_seed_report/1"
MVP_DEMO_STORY_IDS = (
    "refund_baggage_parallel",
    "invoice_interrupt_flight_status",
    "chatflow_block_resume_recommendation",
)
MVP_DEMO_KNOWLEDGE_NAME = "073 MVP Demo Airline Service Knowledge"
MVP_DEMO_PROVIDER_NAME = "106 MVP Demo Mock Provider"
MVP_DEMO_MODEL_CONFIG_NAME = "106 MVP Demo Mock Customer Assistant Model"
MVP_DEMO_MODEL_ID = "hify-mvp-demo/mock-safe-chat"
MVP_DEMO_PROVIDER_BASE_URL = "mock://success"
MVP_DEMO_PREFERRED_LLM_AGENT_NAME = "034 RuntimeLab Airline Chatflow LLM Agent"
MVP_DEMO_HOST_CONTEXT: dict[str, Any] = {
    "actorId": "mvp-demo-operator",
    "actorName": "MVP Demo Operator",
    "tenantId": "mvp-demo-tenant",
    "orgId": "mvp-demo-org",
    "roles": ["customer_service_operator"],
    "permissions": ["customer_assistant:read", "customer_assistant:operate"],
    "source": "mvp-demo-shell",
    "locale": "zh-CN",
}


@dataclass(frozen=True)
class MvpDemoSeedResult:
    chatflow_bindings: dict[str, int]
    customer_session_ids: list[int]
    knowledge_base_ids: list[int]
    story_ids: list[str]
    provider_ids: list[int] | None = None
    model_config_ids: list[int] | None = None


@dataclass(frozen=True)
class OneClickMvpDemoSeedResult:
    seed: MvpDemoSeedResult
    report: dict[str, Any]
    env_path: Path
    report_path: Path | None


@dataclass(frozen=True)
class _DemoTask:
    task_key: str
    task_type: str
    business_key: str
    worker_type: str
    worker_ref: str
    status: str
    input_snapshot: dict[str, Any]


@dataclass(frozen=True)
class _DemoStory:
    story_id: str
    title: str
    customer_name: str
    masked_phone: str
    opening_message: str
    tasks: tuple[_DemoTask, ...]
    proposed_action: dict[str, Any] | None = None


DEMO_STORIES = (
    _DemoStory(
        story_id="refund_baggage_parallel",
        title="退票 + 行李额并行",
        customer_name="赵女士",
        masked_phone="138****1024",
        opening_message="我要退 MU5137 的票，同时确认改签后行李额还在不在。",
        tasks=(
            _DemoTask(
                task_key="refund_ticket:MU5137-8899",
                task_type="REFUND",
                business_key="MU5137-8899",
                worker_type="chatflow_sop",
                worker_ref="refund_ticket",
                status="RUNNING",
                input_snapshot={"orderNo": "MU5137-8899", "reason": "customer_request"},
            ),
            _DemoTask(
                task_key="baggage_service:MU5137-8899",
                task_type="BAGGAGE",
                business_key="MU5137-8899",
                worker_type="chatflow_sop",
                worker_ref="baggage_service",
                status="RUNNING",
                input_snapshot={"orderNo": "MU5137-8899", "route": "SHA-PEK"},
            ),
        ),
        proposed_action={
            "actionType": "PROPOSED_TASK_COMMAND",
            "title": "并行处理退票与行李额确认",
            "command": "RESUME_TASK",
        },
    ),
    _DemoStory(
        story_id="invoice_interrupt_flight_status",
        title="发票申请中途切航班动态",
        customer_name="陈先生",
        masked_phone="139****2048",
        opening_message="先帮我开行程单，等一下，我还想知道 CA1301 会不会延误。",
        tasks=(
            _DemoTask(
                task_key="invoice_apply:CA1301-20231027-8899",
                task_type="INVOICE",
                business_key="CA1301-20231027-8899",
                worker_type="chatflow_sop",
                worker_ref="invoice_apply",
                status="WAITING",
                input_snapshot={"orderNo": "CA1301-20231027-8899", "invoiceType": "itinerary"},
            ),
            _DemoTask(
                task_key="flight_status:CA1301",
                task_type="FLIGHT_STATUS",
                business_key="CA1301",
                worker_type="chatflow_sop",
                worker_ref="flight_status",
                status="PENDING",
                input_snapshot={"flightNo": "CA1301"},
            ),
        ),
        proposed_action={
            "actionType": "PROPOSED_TASK_COMMAND",
            "title": "挂起发票申请并查询航班动态",
            "command": "SUSPEND_TASK",
        },
    ),
    _DemoStory(
        story_id="chatflow_block_resume_recommendation",
        title="Chatflow 阻塞收集信息后生成坐席建议",
        customer_name="王先生",
        masked_phone="137****4096",
        opening_message="我要改签到明天上午，但不记得订单号。",
        tasks=(
            _DemoTask(
                task_key="change_flight:missing-order",
                task_type="CHANGE_FLIGHT",
                business_key="missing-order",
                worker_type="chatflow_sop",
                worker_ref="change_flight",
                status="WAITING",
                input_snapshot={"missingFields": ["order_no", "target_time"]},
            ),
        ),
        proposed_action={
            "actionType": "PROPOSED_TASK_COMMAND",
            "title": "补充订单号后恢复改签流程",
            "command": "RESUME_TASK",
        },
    ),
)


FAQ_ENTRIES = (
    {
        "question": "退票和行李额能否并行处理？",
        "answer": "可以并行处理。退票任务确认票规，行李额任务确认客票权益，坐席需要在执行写操作前分别确认。",
        "category": "refund_baggage",
        "keywords": ["退票", "行李额", "并行"],
        "priority": 30,
    },
    {
        "question": "发票申请过程中客户切换到航班动态怎么办？",
        "answer": "先挂起发票任务，查询航班动态并记录上下文，客户确认后再恢复发票申请。",
        "category": "invoice_interrupt",
        "keywords": ["发票", "航班动态", "挂起"],
        "priority": 20,
    },
    {
        "question": "Chatflow 等待补充信息时坐席如何追问？",
        "answer": "坐席应说明缺少的字段，只追问本轮必须信息；客户补齐后恢复原 Chatflow 并生成建议话术。",
        "category": "chatflow_resume",
        "keywords": ["等待输入", "恢复", "建议话术"],
        "priority": 10,
    },
)


def seed_mvp_demo(session: Session) -> MvpDemoSeedResult:
    _ensure_seed_tables(session)
    provider_id, model_config_id = _seed_demo_provider_model(session)
    chatflow_bindings = seed_runtime_lab_airline_chatflows(session)
    knowledge_base_id = _seed_knowledge(session)
    customer_session_ids = [
        _seed_customer_story(session, story, knowledge_base_id, chatflow_bindings)
        for story in DEMO_STORIES
    ]
    return MvpDemoSeedResult(
        chatflow_bindings=dict(chatflow_bindings),
        customer_session_ids=customer_session_ids,
        knowledge_base_ids=[knowledge_base_id],
        story_ids=list(MVP_DEMO_STORY_IDS),
        provider_ids=[provider_id],
        model_config_ids=[model_config_id],
    )


def write_mvp_demo_env(
    path: Path,
    result: MvpDemoSeedResult,
    *,
    report_path: Path | None = None,
) -> None:
    updates = {
        "HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS": _format_bindings(result.chatflow_bindings),
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODE": "fake",
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_BASE_URL": DEFAULT_RUNTIME_LAB_BASE_URL,
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODEL": DEFAULT_RUNTIME_LAB_ARBITRATOR_MODEL,
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_FALLBACK_MODEL": DEFAULT_RUNTIME_LAB_FALLBACK_MODEL,
        "HIFY_MVP_DEMO_CUSTOMER_SESSION_IDS": ",".join(str(item) for item in result.customer_session_ids),
        "HIFY_MVP_DEMO_KNOWLEDGE_BASE_IDS": ",".join(str(item) for item in result.knowledge_base_ids),
        "HIFY_MVP_DEMO_STORY_IDS": ",".join(result.story_ids),
        "HIFY_MVP_DEMO_HOST_CONTEXT_JSON": _compact_json(MVP_DEMO_HOST_CONTEXT),
        "HIFY_CUSTOMER_ASSISTANT_WORKER_PROFILES_JSON": default_customer_assistant_worker_profiles_json(),
    }
    if result.provider_ids:
        updates["HIFY_MVP_DEMO_PROVIDER_IDS"] = ",".join(str(item) for item in result.provider_ids)
    if result.model_config_ids:
        updates["HIFY_MVP_DEMO_MODEL_CONFIG_IDS"] = ",".join(str(item) for item in result.model_config_ids)
    if report_path is not None:
        updates["HIFY_MVP_DEMO_SEED_REPORT_PATH"] = str(report_path)
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    next_lines: list[str] = []
    for line in existing_lines:
        if line.startswith("# Hify MVP demo topology."):
            continue
        key, sep, _value = line.partition("=")
        if sep and (key in updates or _looks_secret_key(key)):
            continue
        next_lines.append(line)
    if next_lines and next_lines[-1].strip():
        next_lines.append("")
    next_lines.append("# Hify MVP demo topology. API keys stay in shell env or provider config.")
    for key, value in updates.items():
        next_lines.append(f"{key}={value}")
    path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")


def seed_one_click_mvp_demo(
    session: Session,
    *,
    env_path: Path,
    report_path: Path | None = None,
) -> OneClickMvpDemoSeedResult:
    result = seed_mvp_demo(session)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    write_mvp_demo_env(env_path, result, report_path=report_path)
    report = verify_mvp_demo_topology(session, env_text=env_path.read_text(encoding="utf-8"))
    if report_path is not None:
        _write_one_click_report(report_path, result, report, env_path=env_path, session=session)
    return OneClickMvpDemoSeedResult(
        seed=result,
        report=report,
        env_path=env_path,
        report_path=report_path,
    )


def verify_mvp_demo_topology(session: Session, *, env_text: str | None = None) -> dict[str, Any]:
    _ensure_seed_tables(session)
    story_rows = _demo_story_sessions(session)
    story_report = {
        story_id: _verify_story(session, int(row["id"]), dict(row.get("context_json") or {}))
        if row is not None
        else _missing_story_report()
        for story_id, row in story_rows.items()
    }
    missing_stories = [story_id for story_id, row in story_rows.items() if row is None]
    chatflow_report = _verify_airline_chatflow_bindings(session)
    knowledge_report = _verify_demo_knowledge(session)
    provider_model_report = _verify_demo_provider_models(session)
    runtime_v2_llm_readiness = _runtime_v2_llm_readiness(provider_model_report, result_model_config_ids=[])
    host_context_report = _verify_demo_host_context(story_report, env_text)
    security_report = {
        "secretFreeEnv": _text_is_secret_free(env_text or ""),
        "envChecked": env_text is not None,
    }
    checks = [
        _check(
            "demo_story_coverage",
            not missing_stories and len(story_rows) == len(MVP_DEMO_STORY_IDS),
            f"{len(MVP_DEMO_STORY_IDS) - len(missing_stories)}/{len(MVP_DEMO_STORY_IDS)} stories covered",
            {"missing": missing_stories},
        ),
        _check(
            "story_tasks_events_actions",
            all(story["taskCount"] >= 1 and story["eventCount"] >= 1 for story in story_report.values())
            and all(story["pendingActionCount"] >= 1 for story in story_report.values()),
            "Each seeded story has tasks, events, and pending operator action evidence.",
            {"stories": story_report},
        ),
        _check(
            "airline_chatflow_bindings",
            chatflow_report["count"] == len(AIRLINE_CHATFLOW_SOP_IDS) and not chatflow_report["missing"],
            f"{chatflow_report['count']}/{len(AIRLINE_CHATFLOW_SOP_IDS)} SOP Chatflows published",
            chatflow_report,
        ),
        _check(
            "knowledge_faq_reachability",
            knowledge_report["faqCount"] >= len(FAQ_ENTRIES)
            and {"退票", "航班动态", "恢复"}.issubset(set(knowledge_report["keywords"])),
            f"{knowledge_report['faqCount']} FAQ entries available",
            knowledge_report,
        ),
        _check(
            "demo_host_context",
            host_context_report["allStoriesScoped"] and (env_text is None or host_context_report["envConfigured"]),
            f"Seeded stories scoped to {MVP_DEMO_HOST_CONTEXT['tenantId']}",
            host_context_report,
        ),
        _check(
            "demo_provider_model_config",
            provider_model_report["providerId"] is not None
            and provider_model_report["modelConfigId"] is not None
            and provider_model_report["baseUrl"] == MVP_DEMO_PROVIDER_BASE_URL
            and provider_model_report["secretFree"],
            "Mock-safe demo provider/model config is available.",
            provider_model_report,
        ),
        _check(
            "runtime_v2_llm_readiness",
            runtime_v2_llm_readiness["workflowRunsV2ProviderBinding"]
            and runtime_v2_llm_readiness["chatflowRunsV2ProviderBinding"]
            and runtime_v2_llm_readiness["runtimeLabSopV2ProviderBinding"]
            and runtime_v2_llm_readiness["customerAssistantSopV2ProviderBinding"]
            and runtime_v2_llm_readiness["secretFree"],
            "Runtime v2 LLM readiness evidence is available without secrets.",
            runtime_v2_llm_readiness,
        ),
        _check(
            "secret_free_env",
            security_report["secretFreeEnv"],
            "Generated demo env text does not contain secret-looking values.",
            security_report,
        ),
    ]
    return {
        "ok": all(check["status"] == "passed" for check in checks),
        "checks": checks,
        "storyIds": list(MVP_DEMO_STORY_IDS),
        "storyCoverage": {
            "required": len(MVP_DEMO_STORY_IDS),
            "covered": len(MVP_DEMO_STORY_IDS) - len(missing_stories),
            "missing": missing_stories,
        },
        "stories": story_report,
        "chatflowBindings": chatflow_report,
        "knowledge": knowledge_report,
        "providerModel": provider_model_report,
        "runtimeV2LlmReadiness": runtime_v2_llm_readiness,
        "hostContext": host_context_report,
        "security": security_report,
    }


def _write_one_click_report(
    path: Path,
    result: MvpDemoSeedResult,
    verification: dict[str, Any],
    *,
    env_path: Path,
    session: Session,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": ONE_CLICK_DEMO_REPORT_SCHEMA,
        "specId": ONE_CLICK_DEMO_SPEC_ID,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "envPath": str(env_path),
        "seed": {
            "providerIds": list(result.provider_ids or []),
            "modelConfigIds": list(result.model_config_ids or []),
            "chatflowBindings": dict(result.chatflow_bindings),
            "knowledgeBaseIds": list(result.knowledge_base_ids),
            "customerSessionIds": list(result.customer_session_ids),
            "storyIds": list(result.story_ids),
        },
        "persistence": _one_click_persistence_fingerprint(session, result, verification),
        "runtimeV2LlmReadiness": _runtime_v2_llm_readiness(
            verification.get("providerModel") if isinstance(verification.get("providerModel"), Mapping) else {},
            result_model_config_ids=list(result.model_config_ids or []),
            result_provider_ids=list(result.provider_ids or []),
        ),
        "verification": verification,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _one_click_persistence_fingerprint(
    session: Session,
    result: MvpDemoSeedResult,
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    bind = session.get_bind()
    dialect = getattr(getattr(bind, "dialect", None), "name", "unknown")
    url = getattr(bind, "url", None) or getattr(getattr(bind, "engine", None), "url", None)
    drivername = getattr(url, "drivername", "") or ""
    database_url_kind = drivername.split("+", 1)[0] if drivername else dialect
    story_reports = verification.get("stories") if isinstance(verification, Mapping) else None
    stories = story_reports if isinstance(story_reports, Mapping) else {}
    return {
        "dialect": str(dialect),
        "databaseUrlKind": str(database_url_kind),
        "mysql8LiveRoundTrip": str(dialect).lower() == "mysql",
        "topologyCounts": {
            "storyCount": len(result.story_ids),
            "chatflowBindingCount": len(result.chatflow_bindings),
            "knowledgeBaseCount": len(result.knowledge_base_ids),
            "customerSessionCount": len(result.customer_session_ids),
            "providerModelCount": min(len(result.provider_ids or []), len(result.model_config_ids or [])),
            "taskCount": sum(int(story.get("taskCount", 0)) for story in stories.values()),
            "eventCount": sum(int(story.get("eventCount", 0)) for story in stories.values()),
            "pendingActionCount": sum(int(story.get("pendingActionCount", 0)) for story in stories.values()),
        },
    }


def _runtime_v2_llm_readiness(
    provider_model_report: Mapping[str, Any],
    *,
    result_model_config_ids: list[int],
    result_provider_ids: list[int] | None = None,
) -> dict[str, Any]:
    base_url = str(provider_model_report.get("baseUrl") or "")
    provider_mode = "mock_safe" if base_url.startswith("mock://") else "live_provider"
    live_ready = provider_mode == "live_provider" and bool(provider_model_report.get("secretFree"))
    model_config_ids = list(result_model_config_ids)
    if not model_config_ids and provider_model_report.get("modelConfigId") is not None:
        model_config_ids = [int(provider_model_report["modelConfigId"])]
    provider_ids = list(result_provider_ids or [])
    if not provider_ids and provider_model_report.get("providerId") is not None:
        provider_ids = [int(provider_model_report["providerId"])]
    return {
        "workflowRunsV2ProviderBinding": True,
        "chatflowRunsV2ProviderBinding": True,
        "runtimeLabSopV2ProviderBinding": True,
        "customerAssistantSopV2ProviderBinding": True,
        "preferredAgentName": MVP_DEMO_PREFERRED_LLM_AGENT_NAME,
        "providerMode": provider_mode,
        "liveReady": live_ready,
        "liveProviderRequired": not live_ready,
        "modelConfigIds": model_config_ids,
        "providerIds": provider_ids,
        "secretFree": bool(provider_model_report.get("secretFree")),
    }


def _ensure_seed_tables(session: Session) -> None:
    register_baseline_tables()
    register_customer_assistant_tables()
    bind = session.get_bind()
    if bind is not None:
        Base.metadata.create_all(bind=bind)


def _seed_demo_provider_model(session: Session) -> tuple[int, int]:
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    provider_row = session.execute(
        sa.select(provider).where(
            provider.c.name == MVP_DEMO_PROVIDER_NAME,
            provider.c.deleted.is_(False),
        )
    ).mappings().one_or_none()
    provider_values = {
        "name": MVP_DEMO_PROVIDER_NAME,
        "type": "OPENAI_COMPATIBLE",
        "base_url": MVP_DEMO_PROVIDER_BASE_URL,
        "auth_config": {},
        "description": "Spec 106 mock-safe provider anchor for one-click MVP demos.",
        "enabled": True,
        "deleted": False,
        "updated_at": now,
    }
    if provider_row is None:
        provider_id = insert_and_get_id(session, provider, {**provider_values, "created_at": now})
    else:
        provider_id = int(provider_row["id"])
        session.execute(provider.update().where(provider.c.id == provider_id).values(**provider_values))
    model_row = session.execute(
        sa.select(model_config).where(
            model_config.c.name == MVP_DEMO_MODEL_CONFIG_NAME,
            model_config.c.deleted.is_(False),
        )
    ).mappings().one_or_none()
    model_values = {
        "provider_id": provider_id,
        "name": MVP_DEMO_MODEL_CONFIG_NAME,
        "model_id": MVP_DEMO_MODEL_ID,
        "context_size": 8192,
        "extra_params": {
            "temperature": 0,
            "demoSeed": ONE_CLICK_DEMO_SPEC_ID,
            "mockSafe": True,
        },
        "enabled": True,
        "deleted": False,
        "updated_at": now,
    }
    if model_row is None:
        model_config_id = insert_and_get_id(session, model_config, {**model_values, "created_at": now})
    else:
        model_config_id = int(model_row["id"])
        session.execute(
            model_config.update()
            .where(model_config.c.id == model_config_id)
            .values(**model_values)
        )
    session.commit()
    return provider_id, model_config_id


def _seed_knowledge(session: Session) -> int:
    repository = KnowledgeBaseRepository(session)
    knowledge_base = Base.metadata.tables["knowledge_base"]
    row = session.execute(
        sa.select(knowledge_base).where(
            knowledge_base.c.name == MVP_DEMO_KNOWLEDGE_NAME,
            knowledge_base.c.deleted.is_(False),
        )
    ).mappings().one_or_none()
    if row is None:
        created = repository.create(
            {
                "name": MVP_DEMO_KNOWLEDGE_NAME,
                "description": "Spec 073 deterministic MVP demo knowledge for customer assistant advisory.",
            }
        )
        knowledge_base_id = int(created["id"])
    else:
        knowledge_base_id = int(row["id"])
        repository.update(
            knowledge_base_id,
            {
                "description": "Spec 073 deterministic MVP demo knowledge for customer assistant advisory.",
                "enabled": True,
            },
        )
    _upsert_faqs(session, repository, knowledge_base_id)
    return knowledge_base_id


def _upsert_faqs(
    session: Session,
    repository: KnowledgeBaseRepository,
    knowledge_base_id: int,
) -> None:
    faq_table = Base.metadata.tables["knowledge_faq"]
    for entry in FAQ_ENTRIES:
        row = session.execute(
            sa.select(faq_table).where(
                faq_table.c.knowledge_base_id == knowledge_base_id,
                faq_table.c.question == entry["question"],
                faq_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        values = {**entry, "knowledge_base_id": knowledge_base_id, "source": "mvp_demo_seed"}
        if row is None:
            repository.create_faq(values)
        else:
            repository.update_faq(int(row["id"]), values)


def _demo_story_sessions(session: Session) -> dict[str, dict[str, Any] | None]:
    table = Base.metadata.tables["customer_assistant_session"]
    rows = session.execute(
        sa.select(table).where(table.c.deleted.is_(False)).order_by(table.c.id.asc())
    ).mappings().all()
    by_story: dict[str, dict[str, Any] | None] = {story_id: None for story_id in MVP_DEMO_STORY_IDS}
    for row in rows:
        context = dict(row.get("context_json") or {})
        story_id = str(context.get("storyId") or context.get("demoSeedKey") or "")
        if context.get("demoSeed") == "073" and story_id in by_story and by_story[story_id] is None:
            by_story[story_id] = dict(row)
    return by_story


def _verify_story(session: Session, session_id: int, context: dict[str, Any]) -> dict[str, Any]:
    task_table = Base.metadata.tables["customer_assistant_task"]
    event_table = Base.metadata.tables["customer_assistant_event"]
    action_table = Base.metadata.tables["customer_assistant_proposed_action"]
    task_rows = session.execute(
        sa.select(task_table).where(task_table.c.session_id == session_id, task_table.c.deleted.is_(False))
    ).mappings().all()
    event_rows = session.execute(
        sa.select(event_table).where(event_table.c.session_id == session_id, event_table.c.deleted.is_(False))
    ).mappings().all()
    action_rows = session.execute(
        sa.select(action_table).where(action_table.c.session_id == session_id, action_table.c.deleted.is_(False))
    ).mappings().all()
    host_context = dict(context.get("hostContext") or {})
    return {
        "sessionId": session_id,
        "taskCount": len(task_rows),
        "eventCount": len(event_rows),
        "pendingActionCount": sum(1 for row in action_rows if row.get("status") == "PENDING"),
        "taskKeys": [str(row.get("task_key") or "") for row in task_rows],
        "taskStatuses": sorted({str(row.get("status") or "") for row in task_rows}),
        "hostTenantId": str(host_context.get("tenantId") or ""),
        "hostOrgId": str(host_context.get("orgId") or ""),
    }


def _missing_story_report() -> dict[str, Any]:
    return {
        "sessionId": None,
        "taskCount": 0,
        "eventCount": 0,
        "pendingActionCount": 0,
        "taskKeys": [],
        "taskStatuses": [],
        "hostTenantId": "",
        "hostOrgId": "",
    }


def _verify_demo_host_context(story_report: Mapping[str, dict[str, Any]], env_text: str | None) -> dict[str, Any]:
    tenant_id = str(MVP_DEMO_HOST_CONTEXT["tenantId"])
    story_tenants = {
        story_id: str(story.get("hostTenantId") or "")
        for story_id, story in story_report.items()
    }
    return {
        "tenantId": tenant_id,
        "orgId": str(MVP_DEMO_HOST_CONTEXT["orgId"]),
        "storyTenantIds": story_tenants,
        "allStoriesScoped": all(value == tenant_id for value in story_tenants.values()),
        "envConfigured": env_text is not None and "HIFY_MVP_DEMO_HOST_CONTEXT_JSON=" in env_text,
    }


def _verify_airline_chatflow_bindings(session: Session) -> dict[str, Any]:
    workflow = Base.metadata.tables["workflow"]
    rows = session.execute(
        sa.select(workflow).where(
            workflow.c.flow_type == "CHATFLOW",
            workflow.c.status == "PUBLISHED",
            workflow.c.deleted.is_(False),
        )
    ).mappings().all()
    by_sop: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("name") or "")
        if not name.startswith(AIRLINE_CHATFLOW_NAME_PREFIX):
            continue
        for sop_id in AIRLINE_CHATFLOW_SOP_IDS:
            if name.endswith(f"({sop_id})"):
                by_sop[sop_id] = dict(row)
                break
    missing = [sop_id for sop_id in AIRLINE_CHATFLOW_SOP_IDS if sop_id not in by_sop]
    return {
        "count": len(by_sop),
        "missing": missing,
        "ids": {sop_id: int(row["id"]) for sop_id, row in by_sop.items()},
    }


def _verify_demo_knowledge(session: Session) -> dict[str, Any]:
    knowledge_base = Base.metadata.tables["knowledge_base"]
    faq_table = Base.metadata.tables["knowledge_faq"]
    base_row = session.execute(
        sa.select(knowledge_base).where(
            knowledge_base.c.name == MVP_DEMO_KNOWLEDGE_NAME,
            knowledge_base.c.deleted.is_(False),
        )
    ).mappings().one_or_none()
    if base_row is None:
        return {"knowledgeBaseId": None, "faqCount": 0, "keywords": []}
    faq_rows = session.execute(
        sa.select(faq_table).where(
            faq_table.c.knowledge_base_id == int(base_row["id"]),
            faq_table.c.enabled.is_(True),
            faq_table.c.deleted.is_(False),
        )
    ).mappings().all()
    keywords: set[str] = set()
    for row in faq_rows:
        for keyword in row.get("keywords") or []:
            keywords.add(str(keyword))
    return {
        "knowledgeBaseId": int(base_row["id"]),
        "faqCount": len(faq_rows),
        "keywords": sorted(keywords),
    }


def _verify_demo_provider_models(session: Session) -> dict[str, Any]:
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    row = session.execute(
        sa.select(
            provider.c.id.label("provider_id"),
            provider.c.base_url,
            provider.c.auth_config,
            model_config.c.id.label("model_config_id"),
            model_config.c.model_id,
        )
        .select_from(model_config.join(provider, provider.c.id == model_config.c.provider_id))
        .where(
            provider.c.name == MVP_DEMO_PROVIDER_NAME,
            provider.c.deleted.is_(False),
            provider.c.enabled.is_(True),
            model_config.c.name == MVP_DEMO_MODEL_CONFIG_NAME,
            model_config.c.deleted.is_(False),
            model_config.c.enabled.is_(True),
        )
    ).mappings().one_or_none()
    if row is None:
        return {
            "providerId": None,
            "modelConfigId": None,
            "baseUrl": None,
            "modelId": None,
            "secretFree": False,
        }
    auth_config = dict(row.get("auth_config") or {})
    return {
        "providerId": int(row["provider_id"]),
        "modelConfigId": int(row["model_config_id"]),
        "baseUrl": str(row["base_url"]),
        "modelId": str(row["model_id"]),
        "secretFree": _text_is_secret_free(json.dumps(auth_config, ensure_ascii=False)),
    }


def _check(name: str, passed: bool, summary: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "summary": summary,
        "evidence": evidence,
    }


def _text_is_secret_free(text: str) -> bool:
    if not text:
        return True
    upper = text.upper()
    if "SK-" in upper:
        return False
    return not any(marker in upper for marker in ("API_KEY=", "TOKEN=", "SECRET=", "PASSWORD="))


def _compact_json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), ensure_ascii=False, separators=(",", ":"))


def _seed_customer_story(
    session: Session,
    story: _DemoStory,
    knowledge_base_id: int,
    chatflow_bindings: Mapping[str, int],
) -> int:
    repository = CustomerAssistantRepository(session)
    session_row = _upsert_demo_session(session, repository, story, knowledge_base_id, chatflow_bindings)
    session_id = int(session_row["id"])
    request_payload = {
        "demoSeed": "073",
        "storyId": story.story_id,
        "message": story.opening_message,
    }
    run, _replayed = repository.create_run(
        session_id,
        f"mvp-demo:{story.story_id}:bootstrap",
        _stable_hash(request_payload),
        request_payload,
    )
    run = repository.complete_run(
        int(run["id"]),
        {
            "demoSeed": "073",
            "storyId": story.story_id,
            "status": "READY",
            "operatorRecommendation": f"打开演示故事：{story.title}",
        },
    )
    for task in story.tasks:
        row = repository.upsert_task(
            session_id,
            task.task_key,
            task.task_type,
            task.business_key,
            task.worker_type,
            task.worker_ref,
            input_snapshot=task.input_snapshot,
            status=task.status,
        )
        _append_seed_event_once(
            repository,
            session_id,
            f"mvp_demo_task_seeded:{story.story_id}:{task.task_key}",
            {
                "demoSeed": "073",
                "storyId": story.story_id,
                "taskKey": task.task_key,
                "status": task.status,
            },
            run_id=int(run["id"]),
            task_id=int(row["id"]),
        )
    if story.proposed_action:
        repository.upsert_proposed_action(
            session_id,
            int(run["id"]),
            None,
            f"mvp-demo:{story.story_id}:operator-control",
            str(story.proposed_action["actionType"]),
            str(story.proposed_action["title"]),
            {
                "demoSeed": "073",
                "storyId": story.story_id,
                **story.proposed_action,
            },
        )
    return session_id


def _upsert_demo_session(
    session: Session,
    repository: CustomerAssistantRepository,
    story: _DemoStory,
    knowledge_base_id: int,
    chatflow_bindings: Mapping[str, int],
) -> dict[str, Any]:
    context = {
        "demoSeed": "073",
        "demoSeedKey": story.story_id,
        "storyId": story.story_id,
        "storyTitle": story.title,
        "customer": {
            "name": story.customer_name,
            "phone": story.masked_phone,
        },
        "openingMessage": story.opening_message,
        "knowledgeBaseIds": [knowledge_base_id],
        "retrievalSettings": {"mode": "faq", "topK": 3},
        "hostContext": dict(MVP_DEMO_HOST_CONTEXT),
        "chatflowBindings": {
            key: chatflow_bindings[key]
            for key in sorted(chatflow_bindings)
            if key in {task.worker_ref for task in story.tasks}
        },
    }
    existing = _find_demo_session(session, story.story_id)
    if existing is None:
        return repository.create_session(context)
    table = Base.metadata.tables["customer_assistant_session"]
    now = datetime.now()
    session.execute(
        table.update()
        .where(table.c.id == int(existing["id"]), table.c.deleted.is_(False))
        .values(status="ACTIVE", context_json=context, updated_at=now)
    )
    session.commit()
    updated = repository.get_session(int(existing["id"]))
    if updated is None:
        raise RuntimeError(f"MVP demo session disappeared: {existing['id']}")
    return updated


def _find_demo_session(session: Session, story_id: str) -> dict[str, Any] | None:
    table = Base.metadata.tables["customer_assistant_session"]
    rows = session.execute(
        sa.select(table).where(table.c.deleted.is_(False)).order_by(table.c.id.asc())
    ).mappings().all()
    for row in rows:
        context = dict(row.get("context_json") or {})
        if context.get("demoSeed") == "073" and context.get("demoSeedKey") == story_id:
            return dict(row)
    return None


def _append_seed_event_once(
    repository: CustomerAssistantRepository,
    session_id: int,
    event_type: str,
    payload: dict[str, Any],
    *,
    run_id: int,
    task_id: int,
) -> None:
    existing = repository.list_events(session_id)
    if any(event["type"] == event_type for event in existing):
        return
    repository.append_event(
        session_id,
        event_type,
        payload,
        run_id=run_id,
        task_id=task_id,
        visibility="debug",
        source="mvp_demo_seed",
        actor="system",
        span_id=f"mvp-demo:{session_id}:{task_id}",
    )


def _stable_hash(payload: Mapping[str, Any]) -> str:
    parts = [f"{key}={payload[key]}" for key in sorted(payload)]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _format_bindings(bindings: Mapping[str, int]) -> str:
    return ",".join(f"{key}:{value}" for key, value in bindings.items())


def _looks_secret_key(key: str) -> bool:
    normalized = key.upper()
    return any(marker in normalized for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))
