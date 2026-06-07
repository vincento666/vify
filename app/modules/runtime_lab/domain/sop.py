from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SopStep:
    step_id: str
    prompt: str
    interruptible: bool


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
            saved["order_no"] = text
            prompt = self._step(manifest, "confirm").prompt
            reply = f"已记录订单号 {text}。{prompt}"
            return self._result(manifest, "confirm", reply, prompt, saved, completed=False)
        if current_step == "confirm":
            prompt = self._step(manifest, "confirm").prompt
            if text.lower() == "confirm" or text == "确认":
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
    steps = (
        SopStep("collect_order_no", "请提供订单号。", True),
        SopStep("confirm", "请回复 confirm 或 确认 完成办理。", False),
        SopStep("completed", "", False),
    )
    return {
        "refund_ticket": SopManifest(
            sop_id="refund_ticket",
            display_name="退票",
            trigger_keywords=("退票", "退款", "退机票"),
            strong_trigger_keywords=("退票", "我要退票", "退款"),
            steps=steps,
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的退票流程？",
        ),
        "change_flight": SopManifest(
            sop_id="change_flight",
            display_name="改签",
            trigger_keywords=("改签", "改航班", "换航班"),
            strong_trigger_keywords=("改签", "我要改签", "换航班"),
            steps=steps,
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的改签流程？",
        ),
        "invoice_apply": SopManifest(
            sop_id="invoice_apply",
            display_name="发票申请",
            trigger_keywords=("发票", "开票", "报销凭证", "行程单", "电子票据"),
            strong_trigger_keywords=("发票", "开票", "申请发票", "行程单"),
            steps=steps,
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的发票申请流程？",
        ),
        "baggage_service": SopManifest(
            sop_id="baggage_service",
            display_name="行李服务",
            trigger_keywords=("行李", "托运行李", "加行李", "行李额", "超重行李"),
            strong_trigger_keywords=("行李服务", "托运行李", "加行李", "购买行李额"),
            steps=steps,
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的行李服务流程？",
        ),
        "seat_checkin": SopManifest(
            sop_id="seat_checkin",
            display_name="值机选座",
            trigger_keywords=("值机", "选座", "座位", "靠窗", "登机牌"),
            strong_trigger_keywords=("值机", "选座", "我要值机", "我要选座"),
            steps=steps,
            interruptible_steps=("collect_order_no",),
            resume_prompt="是否继续刚才的值机选座流程？",
        ),
    }
