from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class CustomerAssistantWorkerProfile:
    profile_id: str
    task_key: str
    task_type: str
    worker_type: str
    worker_ref: str
    model_policy_ref: str = "default"
    prompt_ref: str = "default"
    tool_refs: tuple[str, ...] = ()
    risk_policy_ref: str = "manual_confirm"
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "profileId": self.profile_id,
            "taskKey": self.task_key,
            "taskType": self.task_type,
            "workerType": self.worker_type,
            "workerRef": self.worker_ref,
            "modelPolicyRef": self.model_policy_ref,
            "promptRef": self.prompt_ref,
            "toolRefs": list(self.tool_refs),
            "riskPolicyRef": self.risk_policy_ref,
            "enabled": self.enabled,
        }


class CustomerAssistantWorkerProfileCatalog:
    def __init__(self, profiles: list[CustomerAssistantWorkerProfile] | tuple[CustomerAssistantWorkerProfile, ...]) -> None:
        self._profiles = tuple(profile for profile in profiles if profile.enabled)

    @classmethod
    def default(cls) -> CustomerAssistantWorkerProfileCatalog:
        return cls(default_customer_assistant_worker_profiles())

    @classmethod
    def from_json(cls, raw: str | None) -> CustomerAssistantWorkerProfileCatalog:
        text = (raw or "").strip()
        if not text:
            return cls.default()
        parsed = json.loads(text)
        items = parsed.get("profiles") if isinstance(parsed, dict) else parsed
        if not isinstance(items, list):
            return cls.default()
        profiles = [_profile_from_mapping(item) for item in items if isinstance(item, dict)]
        return cls(profiles or list(default_customer_assistant_worker_profiles()))

    def resolve(self, task_key: str) -> CustomerAssistantWorkerProfile | None:
        for profile in self._profiles:
            if _task_key_matches_profile(task_key, profile):
                return profile
        return None

    def list_profiles(self) -> list[dict[str, Any]]:
        return [profile.to_dict() for profile in self._profiles]


def default_customer_assistant_worker_profiles() -> tuple[CustomerAssistantWorkerProfile, ...]:
    return (
        CustomerAssistantWorkerProfile(
            profile_id="refund_ticket_chatflow",
            task_key="refund_ticket",
            task_type="REFUND",
            worker_type="chatflow_sop",
            worker_ref="refund_ticket",
            model_policy_ref="customer_assistant_chatflow_default",
            prompt_ref="refund_ticket_sop_prompt",
            tool_refs=("refund_policy_lookup",),
            risk_policy_ref="manual_confirm",
        ),
        CustomerAssistantWorkerProfile(
            profile_id="baggage_allowance_stub",
            task_key="baggage_qa",
            task_type="QA",
            worker_type="stub_qa",
            worker_ref="baggage_allowance",
            model_policy_ref="fake_stub_qa_model",
            prompt_ref="baggage_allowance_prompt",
            tool_refs=(),
            risk_policy_ref="read_only",
        ),
        CustomerAssistantWorkerProfile(
            profile_id="refund_status_react",
            task_key="refund_status",
            task_type="refund_status",
            worker_type="react_worker",
            worker_ref="refund_status_react",
            model_policy_ref="fake_react_worker_model",
            prompt_ref="refund_status_react_prompt",
            tool_refs=("lookup_order", "submit_refund"),
            risk_policy_ref="manual_confirm_high_risk",
        ),
    )


def default_customer_assistant_worker_profiles_json() -> str:
    payload = {"profiles": [profile.to_dict() for profile in default_customer_assistant_worker_profiles()]}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _profile_from_mapping(item: dict[str, Any]) -> CustomerAssistantWorkerProfile:
    return CustomerAssistantWorkerProfile(
        profile_id=str(item.get("profileId") or item.get("profile_id") or item.get("taskKey") or item.get("task_key")),
        task_key=str(item.get("taskKey") or item.get("task_key") or ""),
        task_type=str(item.get("taskType") or item.get("task_type") or ""),
        worker_type=str(item.get("workerType") or item.get("worker_type") or ""),
        worker_ref=str(item.get("workerRef") or item.get("worker_ref") or ""),
        model_policy_ref=str(item.get("modelPolicyRef") or item.get("model_policy_ref") or "default"),
        prompt_ref=str(item.get("promptRef") or item.get("prompt_ref") or "default"),
        tool_refs=tuple(str(tool) for tool in list(item.get("toolRefs") or item.get("tool_refs") or [])),
        risk_policy_ref=str(item.get("riskPolicyRef") or item.get("risk_policy_ref") or "manual_confirm"),
        enabled=bool(item.get("enabled", True)),
    )


def _task_key_matches_profile(task_key: str, profile: CustomerAssistantWorkerProfile) -> bool:
    return task_key == profile.task_key or task_key.startswith(f"{profile.task_key}:")
