from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReactWorkerConfig:
    worker_ref: str
    task_type: str
    allowed_tools: tuple[str, ...]
    max_iterations: int
    timeout_ms: int
    tool_policy_ref: str = "customer_assistant_react_default"
    model_policy_ref: str = "fake_react_worker_model"
    prompt_ref: str = "refund_status_react_prompt"
    risk_policy_ref: str = "manual_confirm_high_risk"
    output_schema_ref: str = "customer_assistant_worker_result_v1"
    worker_type: str = "react_worker"


class ReactWorkerRegistry:
    def __init__(self, configs: list[ReactWorkerConfig] | tuple[ReactWorkerConfig, ...]) -> None:
        self._configs = tuple(configs)

    def lookup(self, task_type: str, worker_ref: str) -> ReactWorkerConfig | None:
        for config in self._configs:
            if config.task_type == task_type and config.worker_ref == worker_ref:
                return config
        return None


def react_worker_registry_from_profiles(
    profiles: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> ReactWorkerRegistry:
    configs = list(_default_react_worker_configs())
    for profile in profiles:
        if str(profile.get("workerType") or profile.get("worker_type") or "") != "react_worker":
            continue
        config = ReactWorkerConfig(
            worker_ref=str(profile.get("workerRef") or profile.get("worker_ref") or ""),
            task_type=str(profile.get("taskType") or profile.get("task_type") or ""),
            allowed_tools=tuple(str(tool) for tool in list(profile.get("toolRefs") or profile.get("tool_refs") or [])),
            max_iterations=3,
            timeout_ms=3000,
            tool_policy_ref=str(profile.get("toolPolicyRef") or profile.get("tool_policy_ref") or "customer_assistant_react_default"),
            model_policy_ref=str(profile.get("modelPolicyRef") or profile.get("model_policy_ref") or "default"),
            prompt_ref=str(profile.get("promptRef") or profile.get("prompt_ref") or "default"),
            risk_policy_ref=str(profile.get("riskPolicyRef") or profile.get("risk_policy_ref") or "manual_confirm"),
        )
        configs = _replace_config(configs, config)
    return ReactWorkerRegistry(configs)


def default_react_worker_registry() -> ReactWorkerRegistry:
    return ReactWorkerRegistry(_default_react_worker_configs())


def _default_react_worker_configs() -> tuple[ReactWorkerConfig, ...]:
    return (
        ReactWorkerConfig(
            worker_ref="refund_status_react",
            task_type="refund_status",
            allowed_tools=("lookup_order", "submit_refund"),
            max_iterations=3,
            timeout_ms=3000,
        ),
    )


def _replace_config(configs: list[ReactWorkerConfig], override: ReactWorkerConfig) -> list[ReactWorkerConfig]:
    replaced = False
    next_configs: list[ReactWorkerConfig] = []
    for config in configs:
        if config.task_type == override.task_type and config.worker_ref == override.worker_ref:
            next_configs.append(override)
            replaced = True
        else:
            next_configs.append(config)
    if not replaced:
        next_configs.append(override)
    return next_configs
