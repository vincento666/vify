class ReactToolPolicy:
    def __init__(
        self,
        *,
        allowed_tools: tuple[str, ...],
        high_risk_tools: tuple[str, ...] = ("submit_refund", "change_booking", "issue_credit"),
    ) -> None:
        self._allowed_tools = set(allowed_tools)
        self._high_risk_tools = set(high_risk_tools)

    def is_allowed(self, tool_name: str) -> bool:
        return tool_name in self._allowed_tools

    def is_high_risk(self, tool_name: str) -> bool:
        return tool_name in self._high_risk_tools
