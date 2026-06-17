from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry


@dataclass(frozen=True)
class ScheduledToolInvocation:
    tool_name: str
    tool_input: dict[str, Any]


@dataclass(frozen=True)
class ToolScheduleBatch:
    batch_id: int
    execution_mode: str
    items: list[ScheduledToolInvocation]
    read_resources: list[str]
    write_resources: list[str]
    lock_mode: str
    resource_lock_reason: str
    parallel_eligible: bool
    item_metadata: list[dict[str, Any]]


@dataclass(frozen=True)
class ToolSchedulePlan:
    batches: list[ToolScheduleBatch]


class ToolScheduler:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def plan(
        self,
        invocations: list[ScheduledToolInvocation],
        *,
        context: dict[str, Any] | None = None,
    ) -> ToolSchedulePlan:
        read_batch: list[ScheduledToolInvocation] = []
        batches: list[ToolScheduleBatch] = []
        next_batch_id = 1
        resolved_context = context or {}

        for invocation in invocations:
            manifest = self._registry.get_manifest(invocation.tool_name)
            read_resources = _resolve_resources(manifest.read_resources, invocation.tool_input, resolved_context)
            write_resources = _resolve_resources(manifest.write_resources, invocation.tool_input, resolved_context)
            if manifest.risk_level == RiskLevel.READ and not write_resources:
                read_batch.append(invocation)
                continue
            if read_batch:
                batches.append(
                    _read_batch(next_batch_id, read_batch, self._registry, resolved_context)
                )
                next_batch_id += 1
                read_batch = []
            lock_mode = "SERIAL" if _has_unresolved_resource([*read_resources, *write_resources]) else "WRITE"
            batches.append(
                ToolScheduleBatch(
                    batch_id=next_batch_id,
                    execution_mode="SERIAL" if lock_mode == "SERIAL" else "WRITE_EXCLUSIVE",
                    items=[invocation],
                    read_resources=read_resources,
                    write_resources=write_resources,
                    lock_mode=lock_mode,
                    resource_lock_reason=(
                        "unresolved_resource_template"
                        if lock_mode == "SERIAL"
                        else "write_resource_lock"
                    ),
                    parallel_eligible=False,
                    item_metadata=[
                        _item_metadata(
                            batch_id=next_batch_id,
                            scheduler_position=1,
                            lock_mode=lock_mode,
                            read_resources=read_resources,
                            write_resources=write_resources,
                            resource_lock_reason=(
                                "unresolved_resource_template"
                                if lock_mode == "SERIAL"
                                else "write_resource_lock"
                            ),
                            parallel_eligible=False,
                        )
                    ],
                )
            )
            next_batch_id += 1

        if read_batch:
            batches.append(_read_batch(next_batch_id, read_batch, self._registry, resolved_context))

        return ToolSchedulePlan(batches=batches)


def _read_batch(
    batch_id: int,
    items: list[ScheduledToolInvocation],
    registry: ToolRegistry,
    context: dict[str, Any],
) -> ToolScheduleBatch:
    read_resources: list[str] = []
    item_metadata: list[dict[str, Any]] = []
    scheduler_position = 1
    for item in items:
        manifest = registry.get_manifest(item.tool_name)
        item_read_resources = _resolve_resources(manifest.read_resources, item.tool_input, context)
        for resource in item_read_resources:
            if resource not in read_resources:
                read_resources.append(resource)
        item_metadata.append(
            _item_metadata(
                batch_id=batch_id,
                scheduler_position=scheduler_position,
                lock_mode="READ",
                read_resources=item_read_resources,
                write_resources=[],
                resource_lock_reason="compatible_read_only",
                parallel_eligible=True,
            )
        )
        scheduler_position += 1
    return ToolScheduleBatch(
        batch_id=batch_id,
        execution_mode="READ_PARALLEL",
        items=list(items),
        read_resources=read_resources,
        write_resources=[],
        lock_mode="READ",
        resource_lock_reason="compatible_read_only",
        parallel_eligible=True,
        item_metadata=item_metadata,
    )


def _resolve_resources(
    templates: list[str],
    tool_input: dict[str, Any],
    context: dict[str, Any],
) -> list[str]:
    values = _SafeFormatMap()
    values.update({key: str(value) for key, value in context.items()})
    values.update({key: str(value) for key, value in tool_input.items()})
    return [template.format_map(values) for template in templates]


class _SafeFormatMap(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _has_unresolved_resource(resources: list[str]) -> bool:
    return any("{" in resource or "}" in resource for resource in resources)


def _item_metadata(
    *,
    batch_id: int,
    scheduler_position: int,
    lock_mode: str,
    read_resources: list[str],
    write_resources: list[str],
    resource_lock_reason: str,
    parallel_eligible: bool,
) -> dict[str, Any]:
    return {
        "schedulerBatchId": batch_id,
        "schedulerPosition": scheduler_position,
        "lockMode": lock_mode,
        "readResourceKeys": read_resources,
        "writeResourceKeys": write_resources,
        "resourceLockReason": resource_lock_reason,
        "parallelEligible": parallel_eligible,
    }
