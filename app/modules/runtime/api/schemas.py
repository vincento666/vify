from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PortType = Literal["default", "branch", "error"]
BranchSelectionMode = Literal["single", "multi"]
SelectionState = Literal[
    "pending",
    "selected",
    "skipped",
    "running",
    "waiting",
    "completed",
    "failed",
    "cancelled",
]
FinalOutputStrategy = Literal[
    "end_node_first",
    "answer_mapping",
    "priority_reply",
    "side_effect_summary",
    "no_reply_summary",
]
RuntimeOwnerType = Literal["CHATFLOW", "WORKFLOW"]


class EdgeSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_node_key: str = Field(alias="sourceNodeKey", min_length=1)
    source_port_key: str = Field(default="default", alias="sourcePortKey", min_length=1)
    target_node_key: str = Field(alias="targetNodeKey", min_length=1)
    target_port_key: str = Field(default="input", alias="targetPortKey", min_length=1)
    branch_group_key: str | None = Field(default=None, alias="branchGroupKey")
    condition: str | None = None
    side_effect_terminal: bool = Field(default=False, alias="sideEffectTerminal")


class PortSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    node_key: str = Field(alias="nodeKey", min_length=1)
    port_key: str = Field(alias="portKey", min_length=1)
    port_type: PortType = Field(default="default", alias="portType")
    branch_group_key: str | None = Field(default=None, alias="branchGroupKey")
    allow_fan_out: bool = Field(default=False, alias="allowFanOut")


class BranchGroupSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    branch_group_key: str = Field(alias="branchGroupKey", min_length=1)
    node_key: str = Field(alias="nodeKey", min_length=1)
    selection_mode: BranchSelectionMode = Field(default="single", alias="selectionMode")
    selected_port_keys: list[str] = Field(default_factory=list, alias="selectedPortKeys")
    skipped_port_keys: list[str] = Field(default_factory=list, alias="skippedPortKeys")


class NodeSelectionState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    node_key: str = Field(alias="nodeKey", min_length=1)
    state: SelectionState
    selected_upstream_node_keys: list[str] = Field(
        default_factory=list,
        alias="selectedUpstreamNodeKeys",
    )
    skipped_upstream_node_keys: list[str] = Field(
        default_factory=list,
        alias="skippedUpstreamNodeKeys",
    )
    reason: str = ""


class FinalOutputRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    owner_type: RuntimeOwnerType = Field(alias="ownerType")
    strategy: FinalOutputStrategy
    requires_visible_output: bool = Field(alias="requiresVisibleOutput")
    allows_side_effect_only: bool = Field(alias="allowsSideEffectOnly")
    candidate_node_keys: list[str] = Field(default_factory=list, alias="candidateNodeKeys")
