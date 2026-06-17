SUPPORTED_CUSTOMER_ASSISTANT_RISK_POLICY_REFS = frozenset(
    {
        "manual_confirm",
        "manual_confirm_high_risk",
        "read_only",
    }
)


def is_supported_risk_policy_ref(policy_ref: str) -> bool:
    return str(policy_ref or "").strip() in SUPPORTED_CUSTOMER_ASSISTANT_RISK_POLICY_REFS


def supported_risk_policy_refs() -> tuple[str, ...]:
    return tuple(sorted(SUPPORTED_CUSTOMER_ASSISTANT_RISK_POLICY_REFS))
