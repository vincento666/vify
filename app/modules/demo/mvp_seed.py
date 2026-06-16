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


MVP_DEMO_STORY_IDS = (
    "refund_baggage_parallel",
    "invoice_interrupt_flight_status",
    "chatflow_block_resume_recommendation",
)
MVP_DEMO_KNOWLEDGE_NAME = "073 MVP Demo Airline Service Knowledge"
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
                worker_type="stub_qa",
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
    )


def write_mvp_demo_env(path: Path, result: MvpDemoSeedResult) -> None:
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
        "hostContext": host_context_report,
        "security": security_report,
    }


def _ensure_seed_tables(session: Session) -> None:
    register_baseline_tables()
    register_customer_assistant_tables()
    bind = session.get_bind()
    if bind is not None:
        Base.metadata.create_all(bind=bind)


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
