from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_get_id
from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.repository import WorkflowRepository

register_baseline_tables()

AIRLINE_CHATFLOW_SOP_IDS = (
    "flight_booking",
    "fare_quote",
    "group_booking",
    "ancillary_sales",
    "refund_ticket",
    "change_flight",
    "passenger_info_change",
    "invoice_apply",
    "baggage_service",
    "seat_checkin",
    "flight_status",
    "special_assistance",
    "pet_cabin",
    "irregular_flight",
    "membership_service",
)

AIRLINE_CHATFLOW_NAME_PREFIX = "034 RuntimeLab Airline SOP"
DEFAULT_RUNTIME_LAB_ARBITRATOR_MODEL = "qwen/qwen3.5-9b"
DEFAULT_RUNTIME_LAB_FALLBACK_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_RUNTIME_LAB_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class AirlineSopSeedSpec:
    sop_id: str
    display_name: str
    business_area: str
    fields: tuple[dict[str, Any], ...]
    followup: str
    policy_prompt: str
    confirm_question: str
    final_prompt: str

    @property
    def workflow_name(self) -> str:
        return f"{AIRLINE_CHATFLOW_NAME_PREFIX} - {self.display_name} ({self.sop_id})"


def seed_runtime_lab_airline_chatflows(session: Session) -> dict[str, int]:
    repository = WorkflowRepository(session)
    bindings: dict[str, int] = {}
    for spec in AIRLINE_SOP_SEEDS:
        existing = _find_existing_chatflow(session, spec.workflow_name)
        nodes = _nodes(spec)
        edges = _edges()
        if existing is None:
            row = repository.create(
                {
                    "name": spec.workflow_name,
                    "description": f"Spec 034 runtime-lab official airline Chatflow SOP for {spec.sop_id}",
                    "flow_type": "CHATFLOW",
                    "status": "PUBLISHED",
                },
                nodes,
                edges,
            )
            bindings[spec.sop_id] = int(row["id"])
            continue
        chatflow_id = int(existing["id"])
        repository.update(
            chatflow_id,
            {
                "name": spec.workflow_name,
                "description": f"Spec 034 runtime-lab official airline Chatflow SOP for {spec.sop_id}",
                "status": "PUBLISHED",
            },
            nodes,
            edges,
            flow_type="CHATFLOW",
        )
        bindings[spec.sop_id] = chatflow_id
    return bindings


def seed_runtime_lab_live_agent(
    session: Session,
    *,
    api_key: str,
    base_url: str = DEFAULT_RUNTIME_LAB_BASE_URL,
    model: str = DEFAULT_RUNTIME_LAB_ARBITRATOR_MODEL,
) -> int:
    if not api_key.strip():
        raise ValueError("api_key is required to seed a live RuntimeLab LLM agent")
    provider_id = _upsert_provider(session, base_url=base_url, api_key=api_key)
    model_id = _upsert_model(session, provider_id=provider_id, model=model)
    return _upsert_agent(session, model_id=model_id)


def write_runtime_lab_env(
    path: Path,
    *,
    bindings: Mapping[str, int],
    base_url: str = DEFAULT_RUNTIME_LAB_BASE_URL,
    model: str = DEFAULT_RUNTIME_LAB_ARBITRATOR_MODEL,
    mode: str = "llm",
) -> None:
    updates = {
        "HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS": ",".join(f"{sop_id}:{chatflow_id}" for sop_id, chatflow_id in bindings.items()),
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODE": mode,
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_BASE_URL": base_url,
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODEL": model,
        "HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_FALLBACK_MODEL": DEFAULT_RUNTIME_LAB_FALLBACK_MODEL,
    }
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    next_lines: list[str] = []
    for line in existing_lines:
        if line.startswith("# RuntimeLab 034 airline Chatflow bindings."):
            continue
        key, sep, _value = line.partition("=")
        if sep and key in updates:
            continue
        next_lines.append(line)
    if next_lines and next_lines[-1].strip():
        next_lines.append("")
    next_lines.append("# RuntimeLab 034 airline Chatflow bindings. API keys stay in shell env or provider config.")
    for key, value in updates.items():
        next_lines.append(f"{key}={value}")
    path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")


def _find_existing_chatflow(session: Session, name: str) -> dict[str, Any] | None:
    workflow = Base.metadata.tables["workflow"]
    row = session.execute(
        sa.select(workflow)
        .where(
            workflow.c.name == name,
            workflow.c.flow_type == "CHATFLOW",
            workflow.c.deleted.is_(False),
        )
        .order_by(workflow.c.id.asc())
    ).mappings().first()
    return dict(row) if row else None


def _nodes(spec: AirlineSopSeedSpec) -> list[dict[str, Any]]:
    return [
        {"node_key": "start", "type": "START", "name": "Start", "config": {}},
        {
            "node_key": "collect",
            "type": "INFORMATION_COLLECTION",
            "name": f"{spec.display_name}信息收集",
            "config": {
                "inputSource": "{{start.sys.query}}",
                "outputVariable": "info",
                "collectionKey": "info",
                "extractorMode": "llm",
                "includeHistory": True,
                "followupTemplate": _history_aware_followup(spec.followup),
                "fields": list(spec.fields),
            },
        },
        {
            "node_key": "policy_llm",
            "type": "LLM",
            "name": f"{spec.display_name}方案生成",
            "config": {
                "systemPrompt": "你是民航客服业务助手。回复要自然、简洁、可执行，不要输出 JSON 或 Markdown。",
                "prompt": spec.policy_prompt,
                "temperature": 0.2,
                "maxTokens": 1200,
                "outputVariable": "policy",
            },
        },
        {
            "node_key": "confirm",
            "type": "QUESTION",
            "name": "用户确认",
            "config": {
                "question": spec.confirm_question,
                "outputVariable": "confirm",
                "answerType": "text",
            },
        },
        {
            "node_key": "final_llm",
            "type": "LLM",
            "name": f"{spec.display_name}结果确认",
            "config": {
                "systemPrompt": "你是民航客服收口助手。按用户确认结果回复，简洁说明是否已提交或仅完成咨询。",
                "prompt": spec.final_prompt,
                "temperature": 0.2,
                "maxTokens": 1200,
                "outputVariable": "answer",
            },
        },
        {
            "node_key": "end",
            "type": "END",
            "name": "End",
            "config": {
                "outputVariable": "final",
                "output": "{{final_llm.answer}}",
            },
        },
    ]


def _edges() -> list[dict[str, Any]]:
    return [
        {"source_node_key": "start", "target_node_key": "collect", "condition": None},
        {"source_node_key": "collect", "target_node_key": "policy_llm", "condition": None},
        {"source_node_key": "policy_llm", "target_node_key": "confirm", "condition": None},
        {"source_node_key": "confirm", "target_node_key": "final_llm", "condition": None},
        {"source_node_key": "final_llm", "target_node_key": "end", "condition": None},
    ]


def _common_order_fields() -> tuple[dict[str, Any], ...]:
    return (
        _field("order_no", "订单号"),
        _field("phone", "手机号"),
        _field("passenger_name", "乘机人姓名"),
    )


def _field(
    name: str,
    description: str,
    *,
    required: bool = True,
    history_mode: str = "",
    extraction_hint: str = "",
) -> dict[str, Any]:
    field = {
        "name": name,
        "type": "string",
        "required": required,
        "description": description,
        "targetScope": "conversation",
        "targetVariable": name,
    }
    if history_mode:
        field["historyMode"] = history_mode
    if extraction_hint:
        field["extractionHint"] = extraction_hint
    return field


def _history_aware_followup(template: str) -> str:
    return template.replace("请补充{{missing_labels}}。", "当前只差{{missing_labels}}。")


def _make_seed(
    sop_id: str,
    display_name: str,
    business_area: str,
    fields: tuple[dict[str, Any], ...],
    followup: str,
    policy_detail: str,
    confirm_question: str,
) -> AirlineSopSeedSpec:
    collected = "，".join(f"{field['description']}={{{{collect.{field['name']}}}}}" for field in fields)
    booking_final_rule = "机票预订确认出票时，必须回复订单编号 CA1301-20231027-8899。" if sop_id == "flight_booking" else ""
    return AirlineSopSeedSpec(
        sop_id=sop_id,
        display_name=display_name,
        business_area=business_area,
        fields=fields,
        followup=followup,
        policy_prompt=(
            f"业务：{display_name}。已收集：{collected}。用户原话：{{{{start.sys.query}}}}。"
            "会话上下文：订单号={{conversation.order_no}}，航线={{conversation.route}}，"
            "原出行时间={{conversation.travel_time}}，乘机人={{conversation.passenger_name}}，手机号={{conversation.phone}}。"
            f"{policy_detail} 请询问用户是否确认继续。"
        ),
        confirm_question=f"{{{{policy_llm.policy}}}}\n{confirm_question}",
        final_prompt=(
            f"业务：{display_name}。方案：{{{{policy_llm.policy}}}}。用户确认回复：{{{{confirm.answer}}}}。"
            f"{booking_final_rule}"
            "如果用户确认办理，请回复已提交或已完成，并给出必要编号；如果用户表示先不办、只是咨询或否定，请明确未提交业务变更。"
        ),
    )


AIRLINE_SOP_SEEDS = (
    _make_seed(
        "flight_booking",
        "机票预订",
        "SALES",
        (
            _field("route", "出发到达城市"),
            _field("travel_time", "出行时间"),
            _field("passenger_name", "乘机人姓名"),
            _field("phone", "手机号"),
        ),
        "我先帮你进入机票预订。{{collected_notice}}请补充{{missing_labels}}。",
        "给出一个可出票航班建议，默认推荐 CA1301，09:05 起飞，12:20 到达，含税价 860 元。",
        "是否确认预订并出票？",
    ),
    _make_seed(
        "fare_quote",
        "票价咨询",
        "SALES",
        (_field("route", "出发到达城市"), _field("travel_time", "出行时间")),
        "我先帮你查票价。{{collected_notice}}请补充{{missing_labels}}。",
        "给出经济舱价格区间、退改规则提醒和价格有效期。",
        "是否需要继续转入订票？",
    ),
    _make_seed(
        "group_booking",
        "团队订票",
        "SALES",
        (_field("route", "出发到达城市"), _field("travel_time", "出行时间"), _field("passenger_count", "出行人数")),
        "我先帮你登记团队订票需求。{{collected_notice}}请补充{{missing_labels}}。",
        "说明团队票报价、名单提交和出票时限。",
        "是否提交团队询价？",
    ),
    _make_seed(
        "ancillary_sales",
        "增值服务",
        "SALES",
        (*_common_order_fields(), _field("service_items", "增值服务项目")),
        "我先帮你看可加购服务。{{collected_notice}}请补充{{missing_labels}}。",
        "说明餐食、行李、保险、贵宾厅等服务可用性和费用。",
        "是否确认加购？",
    ),
    _make_seed(
        "refund_ticket",
        "退票办理",
        "REFUND",
        _common_order_fields(),
        "可以，我帮你看退票规则。{{collected_notice}}请补充{{missing_labels}}。",
        "说明预计可退金额、手续费、到账周期和是否影响其他航段。",
        "是否继续提交退票？",
    ),
    _make_seed(
        "change_flight",
        "改签办理",
        "CHANGE",
        (
            *_common_order_fields(),
            _field(
                "target_time",
                "期望改签时间",
                history_mode="current_turn_only",
                extraction_hint="只从当前用户消息中明确的改到、改成、换到、调整到等新时间抽取，不要使用原出行时间。",
            ),
        ),
        "我先帮你看改签方案。{{collected_notice}}请补充{{missing_labels}}。",
        "给出可改签航班、差价和手续费说明。",
        "是否确认改签？",
    ),
    _make_seed(
        "passenger_info_change",
        "资料修改",
        "CHANGE",
        (*_common_order_fields(), _field("change_detail", "需要修改的资料")),
        "我先帮你核对资料修改。{{collected_notice}}请补充{{missing_labels}}。",
        "说明可修改范围、证件校验要求和是否需要重新出票。",
        "是否确认提交资料修改？",
    ),
    _make_seed(
        "invoice_apply",
        "发票申请",
        "CONSULTATION",
        (*_common_order_fields(), _field("invoice_title", "发票抬头")),
        "我先帮你申请发票。{{collected_notice}}请补充{{missing_labels}}。",
        "说明电子发票/行程单开具方式和发送时效。",
        "是否确认开票？",
    ),
    _make_seed(
        "baggage_service",
        "行李服务",
        "CONSULTATION",
        (*_common_order_fields(), _field("baggage_need", "行李需求")),
        "我先帮你查行李服务。{{collected_notice}}请补充{{missing_labels}}。",
        "说明免费额度、超额行李购买价格和特殊行李限制。",
        "是否确认加购或登记行李服务？",
    ),
    _make_seed(
        "seat_checkin",
        "值机选座",
        "CONSULTATION",
        (*_common_order_fields(), _field("seat_preference", "座位偏好")),
        "我先帮你办理值机选座。{{collected_notice}}请补充{{missing_labels}}。",
        "说明可选座位、值机开放时间和登机牌获取方式。",
        "是否确认选座？",
    ),
    _make_seed(
        "flight_status",
        "航班动态",
        "CONSULTATION",
        (_field("flight_no", "航班号"),),
        "可以，我先帮你查航班动态。{{collected_notice}}请补充{{missing_labels}}。",
        "说明计划起飞/到达时间、当前延误风险和到机场建议。",
        "是否需要继续关注该航班动态？",
    ),
    _make_seed(
        "special_assistance",
        "特殊协助",
        "CONSULTATION",
        (*_common_order_fields(), _field("assistance_need", "特殊协助需求")),
        "我先帮你申请特殊协助。{{collected_notice}}请补充{{missing_labels}}。",
        "说明轮椅、无障碍协助、老人儿童服务和提前申请时限。",
        "是否确认提交特殊协助申请？",
    ),
    _make_seed(
        "pet_cabin",
        "宠物乘机",
        "CONSULTATION",
        (*_common_order_fields(), _field("pet_info", "宠物信息")),
        "我先帮你核对宠物乘机要求。{{collected_notice}}请补充{{missing_labels}}。",
        "说明宠物客舱/托运条件、证件、航空箱和申请时限。",
        "是否继续提交宠物乘机申请？",
    ),
    _make_seed(
        "irregular_flight",
        "异常航班",
        "CONSULTATION",
        (*_common_order_fields(), _field("issue_detail", "异常情况")),
        "我先帮你处理异常航班。{{collected_notice}}请补充{{missing_labels}}。",
        "说明非自愿退改、签转、补偿或保障方案。",
        "是否按该异常航班方案继续处理？",
    ),
    _make_seed(
        "membership_service",
        "会员里程",
        "CONSULTATION",
        (*_common_order_fields(), _field("member_no", "会员号")),
        "我先帮你处理会员里程。{{collected_notice}}请补充{{missing_labels}}。",
        "说明里程补登、到账周期和所需凭证。",
        "是否提交会员里程处理？",
    ),
)


def _upsert_provider(session: Session, *, base_url: str, api_key: str) -> int:
    provider = Base.metadata.tables["provider"]
    now = datetime.now()
    name = "034 RuntimeLab OpenRouter Provider"
    existing = session.execute(
        sa.select(provider).where(provider.c.name == name, provider.c.deleted.is_(False))
    ).mappings().first()
    values = {
        "name": name,
        "type": "OPENAI_COMPATIBLE",
        "base_url": base_url,
        "auth_config": {"api_key": api_key},
        "description": "Spec 034 runtime-lab live provider for airline Chatflow SOPs",
        "enabled": True,
        "deleted": False,
        "updated_at": now,
    }
    if existing:
        provider_id = int(existing["id"])
        session.execute(provider.update().where(provider.c.id == provider_id).values(**values))
        session.commit()
        return provider_id
    provider_id = insert_and_get_id(session, provider, {**values, "created_at": now})
    session.commit()
    return provider_id


def _upsert_model(session: Session, *, provider_id: int, model: str) -> int:
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    name = "034 RuntimeLab Airline qwen"
    existing = session.execute(
        sa.select(model_config).where(model_config.c.name == name, model_config.c.deleted.is_(False))
    ).mappings().first()
    values = {
        "provider_id": provider_id,
        "name": name,
        "model_id": model,
        "context_size": 8192,
        "extra_params": {
            "temperature": 0,
            "reasoning": {"effort": "none", "exclude": True},
            "fallbackModel": DEFAULT_RUNTIME_LAB_FALLBACK_MODEL,
        },
        "enabled": True,
        "deleted": False,
        "updated_at": now,
    }
    if existing:
        model_id = int(existing["id"])
        session.execute(model_config.update().where(model_config.c.id == model_id).values(**values))
        session.commit()
        return model_id
    model_id = insert_and_get_id(session, model_config, {**values, "created_at": now})
    session.commit()
    return model_id


def _upsert_agent(session: Session, *, model_id: int) -> int:
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    name = "034 RuntimeLab Airline Chatflow LLM Agent"
    existing = session.execute(
        sa.select(agent).where(agent.c.name == name, agent.c.deleted.is_(False))
    ).mappings().first()
    values = {
        "name": name,
        "description": "Default live LLM agent for Spec 034 RuntimeLab airline Chatflow SOPs",
        "system_prompt": "",
        "model_config_id": model_id,
        "temperature": 0,
        "max_tokens": 1200,
        "max_context_turns": 6,
        "enabled": True,
        "deleted": False,
        "updated_at": now,
    }
    if existing:
        agent_id = int(existing["id"])
        session.execute(agent.update().where(agent.c.id == agent_id).values(**values))
        session.commit()
        return agent_id
    agent_id = insert_and_get_id(session, agent, {**values, "created_at": now})
    session.commit()
    return agent_id
