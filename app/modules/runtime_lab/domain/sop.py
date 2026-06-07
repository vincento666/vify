from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class SopStep:
    step_id: str
    prompt: str
    interruptible: bool
    node_type: str = "QUESTION"


@dataclass(frozen=True)
class SopManifest:
    sop_id: str
    display_name: str
    trigger_keywords: tuple[str, ...]
    strong_trigger_keywords: tuple[str, ...]
    steps: tuple[SopStep, ...]
    interruptible_steps: tuple[str, ...]
    resume_prompt: str


@dataclass(frozen=True)
class SopTurnResult:
    sop_id: str
    current_step: str
    reply: str
    pending_prompt: str
    collected: dict[str, Any]
    completed: bool
    checkpoint: dict[str, Any]


class MockSopAdapter:
    def __init__(self, manifests: dict[str, SopManifest] | None = None) -> None:
        self._manifests = manifests or mock_sop_manifests()

    def start(self, sop_id: str) -> SopTurnResult:
        manifest = self._manifest(sop_id)
        prompt = self._step(manifest, "collect_order_no").prompt
        reply = f"已开始{manifest.display_name}，{prompt}"
        return self._result(manifest, "collect_order_no", reply, prompt, {}, completed=False)

    def continue_task(
        self,
        sop_id: str,
        current_step: str,
        message: str,
        collected: dict[str, Any] | None = None,
    ) -> SopTurnResult:
        manifest = self._manifest(sop_id)
        saved = dict(collected or {})
        text = message.strip()
        if current_step == "collect_order_no":
            saved.update(_parse_business_variables(text))
            saved.setdefault("order_no", text)
            saved["last_user_message"] = text
            saved["node_trace"] = _node_trace(manifest)
            prompt = self._step(manifest, "confirm").prompt
            order_no = saved.get("order_no") or text
            phone_note = f"，手机号 {saved['phone']}" if saved.get("phone") else ""
            reply = f"已记录订单号 {order_no}{phone_note}。{_policy_note(manifest)}{prompt}"
            return self._result(manifest, "confirm", reply, prompt, saved, completed=False)
        if current_step == "confirm":
            prompt = self._step(manifest, "confirm").prompt
            if _is_confirm(text):
                reply = f"{manifest.display_name}已完成。"
                return self._result(manifest, "completed", reply, "", saved, completed=True)
            reply = f"当前需要确认。{prompt}"
            return self._result(manifest, "confirm", reply, prompt, saved, completed=False)
        return self._result(manifest, "completed", f"{manifest.display_name}已完成。", "", saved, completed=True)

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        manifest = self._manifest(sop_id)
        return step_id in manifest.interruptible_steps

    def _manifest(self, sop_id: str) -> SopManifest:
        manifest = self._manifests.get(sop_id)
        if manifest is None:
            raise KeyError(f"Unknown mock SOP: {sop_id}")
        return manifest

    def _step(self, manifest: SopManifest, step_id: str) -> SopStep:
        for step in manifest.steps:
            if step.step_id == step_id:
                return step
        raise KeyError(f"Unknown mock SOP step: {manifest.sop_id}.{step_id}")

    def _result(
        self,
        manifest: SopManifest,
        current_step: str,
        reply: str,
        pending_prompt: str,
        collected: dict[str, Any],
        completed: bool,
    ) -> SopTurnResult:
        checkpoint_status = "COMPLETED" if completed else "ACTIVE"
        checkpoint = {
            "sop_id": manifest.sop_id,
            "current_step": current_step,
            "pending_prompt": pending_prompt,
            "collected": dict(collected),
            "status": checkpoint_status,
        }
        return SopTurnResult(
            sop_id=manifest.sop_id,
            current_step=current_step,
            reply=reply,
            pending_prompt=pending_prompt,
            collected=dict(collected),
            completed=completed,
            checkpoint=checkpoint,
        )


def mock_sop_manifests() -> dict[str, SopManifest]:
    return {
        "refund_ticket": SopManifest(
            sop_id="refund_ticket",
            display_name="退票",
            trigger_keywords=("退票", "退款", "退机票", "取消行程", "票款", "退费", "退掉航班", "退掉", "不飞"),
            strong_trigger_keywords=("退票", "我要退票", "退款", "取消行程", "退掉"),
            steps=_deep_steps("policy_branch"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的退票流程？",
        ),
        "change_flight": SopManifest(
            sop_id="change_flight",
            display_name="改签",
            trigger_keywords=("改签", "改航班", "换航班", "改日期", "改时间", "调整航班", "同舱位"),
            strong_trigger_keywords=("我要改签", "换航班", "调整航班"),
            steps=_deep_steps("fare_branch"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的改签流程？",
        ),
        "invoice_apply": SopManifest(
            sop_id="invoice_apply",
            display_name="发票申请",
            trigger_keywords=("发票", "开票", "报销凭证", "行程单", "电子票据", "抬头", "税号"),
            strong_trigger_keywords=("发票", "开票", "申请发票", "行程单", "报销凭证"),
            steps=_deep_steps("invoice_intent", branch_node_type="INTENT_RECOGNITION"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的发票申请流程？",
        ),
        "baggage_service": SopManifest(
            sop_id="baggage_service",
            display_name="行李服务",
            trigger_keywords=("行李", "托运行李", "加行李", "行李额", "超重行李", "运动器材", "随身行李"),
            strong_trigger_keywords=("行李服务", "托运行李", "加行李", "购买行李额", "超重"),
            steps=_deep_steps("baggage_branch"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的行李服务流程？",
        ),
        "seat_checkin": SopManifest(
            sop_id="seat_checkin",
            display_name="值机选座",
            trigger_keywords=("值机", "选座", "座位", "靠窗", "登机牌", "过道", "安全出口"),
            strong_trigger_keywords=("值机", "选座", "我要值机", "我要选座"),
            interruptible_steps=("collect_order_no",),
            steps=_deep_steps("seat_branch"),
            resume_prompt="是否继续刚才的值机选座流程？",
        ),
        "flight_status": SopManifest(
            sop_id="flight_status",
            display_name="航班动态",
            trigger_keywords=("航班动态", "航班状态", "有没有取消", "是否延误", "起飞时间", "到达时间", "登机口"),
            strong_trigger_keywords=("航班动态", "航班状态", "查航班", "有没有取消", "是否延误"),
            steps=_deep_steps("status_branch"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的航班动态查询？",
        ),
        "special_assistance": SopManifest(
            sop_id="special_assistance",
            display_name="特殊协助",
            trigger_keywords=("轮椅", "特殊协助", "特殊旅客", "特殊服务", "无障碍", "老人", "孕妇", "优先登机"),
            strong_trigger_keywords=("轮椅", "特殊协助", "特殊旅客", "特殊服务", "无障碍"),
            steps=_deep_steps("assist_branch", branch_node_type="INTENT_RECOGNITION"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的特殊协助申请？",
        ),
        "pet_cabin": SopManifest(
            sop_id="pet_cabin",
            display_name="宠物乘机",
            trigger_keywords=("宠物", "猫", "小狗", "宠物托运", "客舱", "航空箱", "疫苗证明"),
            strong_trigger_keywords=("宠物", "宠物托运", "宠物乘机", "猫", "小狗"),
            steps=_deep_steps("pet_branch"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的宠物乘机服务？",
        ),
        "irregular_flight": SopManifest(
            sop_id="irregular_flight",
            display_name="异常航班",
            trigger_keywords=("不正常航班", "异常航班", "航班取消", "航班延误", "延误四小时", "备降", "签转", "保障方案", "非自愿"),
            strong_trigger_keywords=("不正常航班", "异常航班", "航班取消", "航班延误", "延误四小时", "备降", "签转", "保障方案", "非自愿"),
            steps=_deep_steps("irregular_branch", branch_node_type="INTENT_RECOGNITION"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的异常航班协助？",
        ),
        "membership_service": SopManifest(
            sop_id="membership_service",
            display_name="会员里程",
            trigger_keywords=("会员", "里程", "积分", "常旅客", "补登", "补登里程", "升舱券", "会员等级"),
            strong_trigger_keywords=("会员", "里程", "积分", "常旅客", "补登里程"),
            steps=_deep_steps("member_branch"),
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的会员里程服务？",
        ),
    }


def _deep_steps(branch_step_id: str, branch_node_type: str = "CONDITION") -> tuple[SopStep, ...]:
    return (
        SopStep("collect_order_no", "请提供订单号、手机号和乘机人信息。", True, "INFORMATION_COLLECTION"),
        SopStep("parse_variables", "解析订单、手机号、旅客姓名和航班线索。", True, "VARIABLE_PARSE"),
        SopStep("policy_llm", "生成民航客服政策解释。", True, "LLM"),
        SopStep("business_api", "模拟调用民航订单/航班/会员 API。", True, "API_CALL"),
        SopStep(branch_step_id, "根据业务类型分支。", True, branch_node_type),
        SopStep("aggregate_context", "聚合会话变量和业务查询结果。", True, "VARIABLE_AGGREGATION"),
        SopStep("confirm", "请回复 confirm 或 确认 完成办理。", False, "QUESTION"),
        SopStep("completed", "", False, "END"),
    )


def _parse_business_variables(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    order_match = re.search(r"(?:订单号|订单|PNR|票号|编码)\s*[:：]?\s*([A-Z0-9][A-Z0-9-]{3,})", text, re.I)
    if order_match is None:
        order_match = re.search(r"\b([A-Z]{1,4}-?\d{2,})\b", text, re.I)
    if order_match is not None:
        parsed["order_no"] = order_match.group(1).upper()
    phone_match = re.search(r"(1[3-9]\d{9})", text)
    if phone_match is not None:
        parsed["phone"] = phone_match.group(1)
    passenger_match = re.search(r"乘机人\s*([\u4e00-\u9fa5A-Za-z]{2,12})", text)
    if passenger_match is not None:
        parsed["passenger_name"] = passenger_match.group(1)
    return parsed


def _node_trace(manifest: SopManifest) -> list[str]:
    return [step.node_type for step in manifest.steps if step.step_id not in {"completed"}]


def _policy_note(manifest: SopManifest) -> str:
    return f"已完成{manifest.display_name}政策说明、业务查询和变量聚合。"


def _is_confirm(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "confirm" or "确认" in normalized
