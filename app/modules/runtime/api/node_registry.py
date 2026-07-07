from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


NodeRunStatus = Literal["durable", "virtual"]
RuntimeEventStatus = Literal["node_event", "run_event"]
CompatibilityStatus = Literal["native", "virtual", "reused"]


@dataclass(frozen=True)
class NodeExecutorRegistryEntry:
    node_type: str
    label: str
    executor: str
    compatibility_status: CompatibilityStatus
    node_run_status: NodeRunStatus
    runtime_event: RuntimeEventStatus
    dag_context_isolated: bool
    chatflow_support: str
    workflow_support: str
    side_effect: str
    protection: str
    notes: str = ""


FIRST_CLASS_NODE_TYPES = (
    "START",
    "MESSAGE",
    "QUESTION",
    "HUMAN_INPUT",
    "LLM",
    "CODE",
    "TEXT_PROCESS",
    "JSON_PARSE",
    "VARIABLE_ASSIGN",
    "VARIABLE_AGGREGATION",
    "CONDITION",
    "INTENT_RECOGNITION",
    "INFORMATION_COLLECTION",
    "KNOWLEDGE",
    "API_CALL",
    "TOOL_CALL",
    "EXECUTE_WORKFLOW",
    "TRANSFER_TO_HUMAN",
    "AGENT_CALL",
    "END",
)


NODE_EXECUTOR_REGISTRY: dict[str, NodeExecutorRegistryEntry] = {
    "START": NodeExecutorRegistryEntry(
        node_type="START",
        label="Start",
        executor="RuntimeV2 input context virtual executor",
        compatibility_status="virtual",
        node_run_status="virtual",
        runtime_event="run_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="none",
        protection="run-level idempotency key",
        notes="Runtime v2 treats START as input context and records workflow_run_started.",
    ),
    "MESSAGE": NodeExecutorRegistryEntry(
        node_type="MESSAGE",
        label="Message",
        executor="MessageNodeExecutor / inline RuntimeV2 message path",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="message output",
        protection="sideEffectProtection idempotency key plus node-run output evidence",
    ),
    "QUESTION": NodeExecutorRegistryEntry(
        node_type="QUESTION",
        label="Question",
        executor="QuestionNodeExecutor / RuntimeV2 checkpoint path",
        compatibility_status="native",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="waiting checkpoint",
        protection="checkpoint event link plus resume idempotency key",
    ),
    "HUMAN_INPUT": NodeExecutorRegistryEntry(
        node_type="HUMAN_INPUT",
        label="Human input",
        executor="HumanInputNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="waiting checkpoint",
        protection="checkpoint event link plus resume idempotency key",
    ),
    "LLM": NodeExecutorRegistryEntry(
        node_type="LLM",
        label="LLM",
        executor="LlmNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="model call",
        protection="node-run evidence; provider retry semantics stay external",
    ),
    "CODE": NodeExecutorRegistryEntry(
        node_type="CODE",
        label="Code",
        executor="CodeNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="sandboxed compute",
        protection="restricted sandbox and node-run evidence",
    ),
    "TEXT_PROCESS": NodeExecutorRegistryEntry(
        node_type="TEXT_PROCESS",
        label="Text process",
        executor="TextProcessNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="none",
        protection="pure transform",
    ),
    "JSON_PARSE": NodeExecutorRegistryEntry(
        node_type="JSON_PARSE",
        label="JSON parse",
        executor="JsonParseNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="none",
        protection="pure transform",
    ),
    "VARIABLE_ASSIGN": NodeExecutorRegistryEntry(
        node_type="VARIABLE_ASSIGN",
        label="Variable assign",
        executor="VariableAssignNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="runtime variable write",
        protection="sideEffectProtection execution record plus ExecutionContext branch clone",
    ),
    "VARIABLE_AGGREGATION": NodeExecutorRegistryEntry(
        node_type="VARIABLE_AGGREGATION",
        label="Variable aggregation",
        executor="VariableAggregationNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="none",
        protection="pure transform from selected upstream outputs",
    ),
    "CONDITION": NodeExecutorRegistryEntry(
        node_type="CONDITION",
        label="Branch condition",
        executor="ConditionNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="branch selection",
        protection="selected port evidence in downstream selection state",
    ),
    "INTENT_RECOGNITION": NodeExecutorRegistryEntry(
        node_type="INTENT_RECOGNITION",
        label="Intent recognition",
        executor="IntentRecognitionNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="optional model call; branch selection",
        protection="selected port evidence in downstream selection state",
    ),
    "INFORMATION_COLLECTION": NodeExecutorRegistryEntry(
        node_type="INFORMATION_COLLECTION",
        label="Information collection",
        executor="InformationCollectionNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="waiting checkpoint and optional conversation variable write",
        protection="checkpoint event link plus resume idempotency key",
    ),
    "KNOWLEDGE": NodeExecutorRegistryEntry(
        node_type="KNOWLEDGE",
        label="Knowledge",
        executor="KnowledgeNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="knowledge search",
        protection="read-only facade call plus node-run evidence",
    ),
    "API_CALL": NodeExecutorRegistryEntry(
        node_type="API_CALL",
        label="API call",
        executor="ApiCallNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="external API call",
        protection="sideEffectProtection idempotency key in API Resource adapter evidence; raw URL mode rejected",
    ),
    "TOOL_CALL": NodeExecutorRegistryEntry(
        node_type="TOOL_CALL",
        label="Tool call",
        executor="ToolCallNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="MCP/API tool call",
        protection="sideEffectProtection idempotency key plus resource policy, allowWrite, retry evidence, and sanitized input",
    ),
    "EXECUTE_WORKFLOW": NodeExecutorRegistryEntry(
        node_type="EXECUTE_WORKFLOW",
        label="Execute Workflow",
        executor="ExecuteWorkflowNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="nested workflow run",
        protection="sideEffectProtection idempotency key plus nested run evidence and recursion guard",
    ),
    "TRANSFER_TO_HUMAN": NodeExecutorRegistryEntry(
        node_type="TRANSFER_TO_HUMAN",
        label="Transfer to human",
        executor="RuntimeV2 checkpointed transfer path / TransferToHumanNodeExecutor",
        compatibility_status="native",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="product-difference: chatflow only",
        side_effect="handoff request",
        protection="sideEffectProtection proposed action with runtime-v2 handoff id and checkpoint",
    ),
    "AGENT_CALL": NodeExecutorRegistryEntry(
        node_type="AGENT_CALL",
        label="Agent call",
        executor="AgentCallNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="agent invocation",
        protection="timeout, recursion guard, and node-run evidence",
    ),
    "END": NodeExecutorRegistryEntry(
        node_type="END",
        label="End",
        executor="EndNodeExecutor",
        compatibility_status="reused",
        node_run_status="durable",
        runtime_event="node_event",
        dag_context_isolated=True,
        chatflow_support="yes",
        workflow_support="yes",
        side_effect="run final output",
        protection="final-output resolver and node-run evidence",
    ),
}


NODE_CAPABILITY_SCHEMAS: dict[str, tuple[str, ...]] = {
    "START": ("run.start", "input.context"),
    "MESSAGE": ("message.output", "side_effect.idempotency"),
    "QUESTION": ("checkpoint.wait", "checkpoint.resume"),
    "HUMAN_INPUT": ("checkpoint.wait", "checkpoint.resume"),
    "LLM": ("model.call", "node_run.evidence"),
    "CODE": ("sandbox.compute", "node_run.evidence"),
    "TEXT_PROCESS": ("text.transform", "node_run.evidence"),
    "JSON_PARSE": ("json.parse", "node_run.evidence"),
    "VARIABLE_ASSIGN": ("runtime_variable.write", "side_effect.execution_record"),
    "VARIABLE_AGGREGATION": ("runtime_variable.aggregate", "selected_upstream.outputs"),
    "CONDITION": ("branch.select", "port.default", "selection_state"),
    "INTENT_RECOGNITION": ("intent.route", "branch.select", "selection_state"),
    "INFORMATION_COLLECTION": ("checkpoint.wait", "checkpoint.resume", "conversation_variable.write"),
    "KNOWLEDGE": ("knowledge.search", "node_run.evidence"),
    "API_CALL": ("api_resource.call", "side_effect.idempotency"),
    "TOOL_CALL": ("tool_resource.call", "side_effect.idempotency", "resource_policy.allow_write"),
    "EXECUTE_WORKFLOW": ("subworkflow.run", "side_effect.idempotency", "recursion_guard"),
    "TRANSFER_TO_HUMAN": ("handoff.proposed_action", "checkpoint.wait", "side_effect.idempotency"),
    "AGENT_CALL": ("agent.call", "recursion_guard", "node_run.evidence"),
    "END": ("final_output.resolve", "node_run.evidence"),
}


NODE_CAPABILITY_PRODUCT_DIFFERENCES: dict[str, str] = {
    "TRANSFER_TO_HUMAN": "Chatflow-only handoff request; Workflow intentionally has no conversation handoff target.",
}


NODE_CAPABILITY_WORKFLOW_OVERRIDES: dict[str, tuple[str, ...]] = {
    "TRANSFER_TO_HUMAN": ("product_difference.not_available",),
}


def _capability_schema_for(node_type: str, flow_type: str) -> tuple[str, ...]:
    if flow_type == "WORKFLOW" and node_type in NODE_CAPABILITY_WORKFLOW_OVERRIDES:
        return NODE_CAPABILITY_WORKFLOW_OVERRIDES[node_type]
    return NODE_CAPABILITY_SCHEMAS[node_type]


def node_compatibility_matrix() -> dict[str, dict[str, object]]:
    matrix: dict[str, dict[str, object]] = {}
    for node_type, entry in NODE_EXECUTOR_REGISTRY.items():
        data = asdict(entry)
        chatflow_schema = _capability_schema_for(node_type, "CHATFLOW")
        workflow_schema = _capability_schema_for(node_type, "WORKFLOW")
        data["chatflowCapabilitySchema"] = list(chatflow_schema)
        data["workflowCapabilitySchema"] = list(workflow_schema)
        data["chatflowOnlyCapabilities"] = [item for item in chatflow_schema if item not in workflow_schema]
        data["workflowOnlyCapabilities"] = [item for item in workflow_schema if item not in chatflow_schema]
        data["productDifference"] = NODE_CAPABILITY_PRODUCT_DIFFERENCES.get(node_type, "")
        matrix[node_type] = data
    return matrix
