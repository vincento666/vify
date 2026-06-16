from dataclasses import dataclass


@dataclass(frozen=True)
class ReactWorkerConfig:
    worker_ref: str
    task_type: str
    allowed_tools: tuple[str, ...]
    max_iterations: int
    timeout_ms: int
    tool_policy_ref: str = "customer_assistant_react_default"
    model_policy_ref: str = "fake_react_worker_model"
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


def default_react_worker_registry() -> ReactWorkerRegistry:
    return ReactWorkerRegistry(
        [
            ReactWorkerConfig(
                worker_ref="refund_status_react",
                task_type="refund_status",
                allowed_tools=("lookup_order", "submit_refund"),
                max_iterations=3,
                timeout_ms=3000,
            )
        ]
    )
