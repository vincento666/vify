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
    if policy_ref == "manual_confirm_lookup_tools":
        return ReactToolPolicy(
            allowed_tools=allowed_tools,
            manual_confirm_tools=("lookup_order",),
        )
    return ReactToolPolicy(allowed_tools=allowed_tools)
