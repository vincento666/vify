SUPPORTED_CUSTOMER_ASSISTANT_TOOL_POLICY_REFS = frozenset(
    {
        "customer_assistant_worker_tool_default",
        "customer_assistant_react_default",
        "strict-read-before-write",
        "manual_confirm_lookup_tools",
        "refund_policy_tools",
        "read_only_knowledge_tools",
    }
)
_DEFAULT_BEHAVIOR_POLICY_REFS = SUPPORTED_CUSTOMER_ASSISTANT_TOOL_POLICY_REFS - {"manual_confirm_lookup_tools"}


class UnsupportedReactToolPolicyError(ValueError):
    pass


class ReactToolPolicy:
    def __init__(
        self,
        *,
        allowed_tools: tuple[str, ...],
        high_risk_tools: tuple[str, ...] = ("submit_refund", "change_booking", "issue_credit"),
        manual_confirm_tools: tuple[str, ...] = (),
    ) -> None:
        self._allowed_tools = set(allowed_tools)
        self._high_risk_tools = set(high_risk_tools)
        self._manual_confirm_tools = set(manual_confirm_tools)

    def is_allowed(self, tool_name: str) -> bool:
        return tool_name in self._allowed_tools

    def is_high_risk(self, tool_name: str) -> bool:
        return tool_name in self._high_risk_tools

    def requires_manual_confirmation(self, tool_name: str) -> bool:
        return tool_name in self._manual_confirm_tools


def react_tool_policy_for_ref(*, policy_ref: str, allowed_tools: tuple[str, ...]) -> ReactToolPolicy:
    normalized_ref = str(policy_ref or "").strip()
    if normalized_ref == "manual_confirm_lookup_tools":
        return ReactToolPolicy(
            allowed_tools=allowed_tools,
            manual_confirm_tools=("lookup_order",),
        )
    if normalized_ref in _DEFAULT_BEHAVIOR_POLICY_REFS:
        return ReactToolPolicy(allowed_tools=allowed_tools)
    raise UnsupportedReactToolPolicyError(
        f"Unsupported toolPolicyRef: {policy_ref}. Supported tool policies: {', '.join(supported_tool_policy_refs())}"
    )


def is_supported_tool_policy_ref(policy_ref: str) -> bool:
    return str(policy_ref or "").strip() in SUPPORTED_CUSTOMER_ASSISTANT_TOOL_POLICY_REFS


def supported_tool_policy_refs() -> tuple[str, ...]:
    return tuple(sorted(SUPPORTED_CUSTOMER_ASSISTANT_TOOL_POLICY_REFS))
