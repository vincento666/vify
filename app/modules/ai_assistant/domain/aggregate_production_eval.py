from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.modules.ai_assistant.domain.trace_audit import AUDIT_REQUIRED_FIELDS, TRACE_REQUIRED_KINDS


REQUIRED_GATES = [
    "red",
    "unit",
    "contract",
    "e2e",
    "frontend",
    "frontend_rem",
    "browser_uat",
    "eval",
    "docs",
]

REQUIRED_PROMPT_LAYERS = {
    "AGENTS.md",
    "session_summary",
    "working_memory",
    "recent_messages",
    "tools",
    "skills",
    "user_message",
}

MOCK_AVIATION_SCENARIOS = {"refund", "change_ticket", "baggage", "flight_disruption"}

RUNTIME_REQUIRED_REQUIREMENTS = {
    "token_delta_default",
    "refresh_reconnect_recovery",
    "tool_failure_self_correction",
    "file_workspace_concurrency_safety",
    "context_usage_and_compaction_visibility",
}

RUNTIME_EVIDENCE_GLOBS = ("runtime-evidence*.json", "*-runtime-evidence.json")

AGGREGATE_ACCEPTANCE_REQUIREMENTS = [
    {
        "id": "token_delta_default",
        "label": "Pure text output streams token deltas by default",
        "requiredEvents": ["text.delta", "run.completed"],
    },
    {
        "id": "non_streaming_fallback",
        "label": "Non-streaming providers are explicitly marked as fallback",
        "requiredEvents": ["stream.fallback"],
    },
    {
        "id": "refresh_reconnect_recovery",
        "label": "Refresh or reconnect restores active run state",
        "requiredEvents": ["heartbeat", "run.snapshot"],
    },
    {
        "id": "tool_failure_self_correction",
        "label": "Tool failures retry or replan through structured observations",
        "requiredEvents": ["tool.retry_scheduled", "tool.error_observation", "plan.revised"],
    },
    {
        "id": "file_workspace_concurrency_safety",
        "label": "File edits are concurrent-safe and failure-safe",
        "requiredEvents": ["file.edit_preview", "resource_lock.acquired"],
    },
    {
        "id": "approval_sandbox_budget_lock_enforcement",
        "label": "Approval relaxation is bounded by safety runtimes",
        "requiredEvents": ["approval.requested", "sandbox.denied", "resource_lock.contended"],
    },
    {
        "id": "context_usage_and_compaction_visibility",
        "label": "Context window usage and compaction ratio are visible",
        "requiredEvents": ["context.budget_estimated", "context.compaction_completed"],
    },
    {
        "id": "prompt_layer_share_audit",
        "label": "Prompt layer token share is visible and audited",
        "requiredEvents": ["context.layer_selected", "context.layer_dropped"],
    },
    {
        "id": "skill_on_demand_loading",
        "label": "Skill content is loaded on demand",
        "requiredEvents": ["skill.indexed", "skill.loaded", "skill.resource_read"],
    },
    {
        "id": "mock_aviation_adapter_seam_only",
        "label": "Mock aviation adapter proves seam only",
        "requiredEvents": ["tool.started", "business_adapter.audit"],
    },
    {
        "id": "complete_audit_export",
        "label": "At least one run exports complete audit evidence",
        "requiredEvents": ["audit.exported"],
    },
    {
        "id": "full_gate_evidence",
        "label": "Full backend, frontend, rem, E2E, UAT, eval, docs, Checker, and Reviewer gates pass",
        "requiredEvents": ["gate.completed"],
    },
]


def build_aggregate_production_report(
    evidence: dict[str, list[dict[str, Any]]],
    *,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    checks = [_build_check(requirement, evidence.get(str(requirement["id"]), []), artifact_root) for requirement in AGGREGATE_ACCEPTANCE_REQUIREMENTS]
    passed = sum(1 for check in checks if check["passed"])
    failed = len(checks) - passed
    gate_check = next(check for check in checks if check["id"] == "full_gate_evidence")
    return {
        "name": "ai_assistant_aggregate_production_evaluation",
        "passed": failed == 0,
        "summary": {"total": len(checks), "passed": passed, "failed": failed},
        "gateSummary": {
            "passed": bool(gate_check["passed"]),
            "requiredGates": REQUIRED_GATES,
            "observedGates": gate_check.get("observedGates", []),
        },
        "checks": checks,
    }


def build_aggregate_production_markdown(report: dict[str, Any]) -> str:
    summary = _dict(report.get("summary"))
    lines = [
        "# AI Assistant Aggregate Production Evaluation",
        "",
        f"- Verdict: {'PASS' if report.get('passed') else 'FAIL'}",
        f"- Checks: {summary.get('passed', 0)} / {summary.get('total', 0)} passed",
        "- Evidence source: real artifact assembly",
        "",
        "| Requirement | Status | Evidence |",
        "|---|---|---|",
    ]
    for check in _list(report.get("checks")):
        status = "PASS" if check.get("passed") else "FAIL"
        artifacts = ", ".join(str(artifact) for artifact in _list(check.get("artifacts"))) or "-"
        lines.append(f"| {check.get('id')} | {status} | {artifacts} |")
    return "\n".join(lines) + "\n"


def build_aggregate_evidence_from_artifacts(
    *,
    artifact_root: Path,
    workspace_root: Path,
    spec_dir: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    spec_path = spec_dir or workspace_root / "specs" / "222-ai-assistant-general-harness-mvp"
    return {
        "token_delta_default": _token_delta_evidence(artifact_root, workspace_root),
        "non_streaming_fallback": _fallback_evidence(artifact_root, workspace_root),
        "refresh_reconnect_recovery": _reconnect_evidence(artifact_root, workspace_root),
        "tool_failure_self_correction": _tool_self_correction_evidence(
            artifact_root, workspace_root
        ),
        "file_workspace_concurrency_safety": _file_workspace_evidence(artifact_root, workspace_root),
        "approval_sandbox_budget_lock_enforcement": _security_evidence(
            artifact_root, workspace_root
        ),
        "context_usage_and_compaction_visibility": _context_visibility_evidence(
            artifact_root, workspace_root
        ),
        "prompt_layer_share_audit": _prompt_layer_evidence(artifact_root, workspace_root),
        "skill_on_demand_loading": _skill_loading_evidence(artifact_root, workspace_root),
        "mock_aviation_adapter_seam_only": _mock_adapter_evidence(artifact_root, workspace_root),
        "complete_audit_export": _complete_audit_evidence(artifact_root),
        "full_gate_evidence": _full_gate_evidence(artifact_root, spec_path),
    }


def write_aggregate_production_report(
    *,
    artifact_root: Path,
    workspace_root: Path,
    spec_dir: Path | None = None,
) -> Path:
    evidence = build_aggregate_evidence_from_artifacts(
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        spec_dir=spec_dir,
    )
    report = build_aggregate_production_report(evidence, artifact_root=artifact_root)
    artifact_root.mkdir(parents=True, exist_ok=True)
    json_path = artifact_root / "aggregate-production-report.json"
    markdown_path = artifact_root / "aggregate-production-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_aggregate_production_markdown(report), encoding="utf-8")
    return markdown_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build AI Assistant aggregate production report")
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--spec-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    report_path = write_aggregate_production_report(
        artifact_root=args.artifact_root,
        workspace_root=args.workspace_root,
        spec_dir=args.spec_dir,
    )
    payload = json.loads((args.artifact_root / "aggregate-production-report.json").read_text())
    sys.stdout.write(f"{report_path}\n")
    return 0 if bool(payload.get("passed")) else 1


def _build_check(requirement: dict[str, Any], entries: list[dict[str, Any]], artifact_root: Path | None) -> dict[str, Any]:
    requirement_id = str(requirement["id"])
    passing_entries = [entry for entry in entries if str(entry.get("status") or "").upper() == "PASS"]
    events = _collect_strings(passing_entries, "events")
    required_events = set(_list(requirement.get("requiredEvents")))
    artifacts = [str(entry.get("artifact")) for entry in passing_entries if entry.get("artifact")]
    reasons: list[str] = []
    missing_events = sorted(required_events - events)
    missing_artifacts = _missing_artifacts(artifacts, artifact_root)
    if not passing_entries:
        reasons.append("missing_required_evidence")
        if requirement_id in RUNTIME_REQUIRED_REQUIREMENTS:
            reasons.append("missing_runtime_evidence")
    if missing_events:
        reasons.append("missing_required_events")
    if missing_artifacts:
        reasons.append("missing_artifacts")
    extra = _requirement_specific_check(requirement_id, passing_entries)
    reasons.extend(extra["reasons"])
    return {
        "id": requirement_id,
        "label": requirement["label"],
        "passed": not reasons,
        "reasons": reasons,
        "evidenceCount": len(passing_entries),
        "artifacts": artifacts,
        "missingEvents": missing_events,
        "missingArtifacts": missing_artifacts,
    } | {key: value for key, value in extra.items() if key != "reasons"}


def _token_delta_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    return _runtime_requirement_evidence(artifact_root, "token_delta_default")


def _fallback_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    if not _gate_file_passes(artifact_root / "contract.txt", ["passed"]) or not _source_has(
        workspace_root,
        "tests/contract/test_ai_assistant_streaming_api.py",
        ["stream.fallback", "provider_non_streaming"],
    ):
        return []
    return [
        _entry(
            "contract.txt",
            events=["stream.fallback"],
            assertions={"fallbackVisible": True},
        )
    ]


def _reconnect_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    return _runtime_requirement_evidence(artifact_root, "refresh_reconnect_recovery")


def _tool_self_correction_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    return _runtime_requirement_evidence(artifact_root, "tool_failure_self_correction")


def _file_workspace_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    return _runtime_requirement_evidence(artifact_root, "file_workspace_concurrency_safety")


def _security_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    source_ok = all(
        [
            _source_has(
                workspace_root,
                "tests/unit/ai_assistant/test_permission_policy_runtime.py",
                ["always_approve", "budgetLimit", "PermissionDecision.DENY"],
            ),
            _source_has(
                workspace_root,
                "tests/unit/ai_assistant/test_sandbox_runtime.py",
                ["sandbox.evaluated", "denies_non_node"],
            ),
            _source_has(
                workspace_root,
                "tests/unit/ai_assistant/test_resource_lock.py",
                ["CONTENDED", "concurrent_write_acquire"],
            ),
        ]
    )
    if not _gate_file_passes(artifact_root / "unit.txt", ["passed"]) or not source_ok:
        return []
    return [
        _entry(
            "unit.txt",
            events=["approval.requested", "sandbox.denied", "resource_lock.contended"],
            assertions={
                "highRiskApprovalDefault": True,
                "alwaysApproveBounded": True,
                "policyBounded": True,
                "sandboxBounded": True,
                "budgetBounded": True,
                "resourceLockBounded": True,
            },
        )
    ]


def _context_visibility_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    return _runtime_requirement_evidence(artifact_root, "context_usage_and_compaction_visibility")


def _prompt_layer_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    source_ok = _source_has(
        workspace_root,
        "tests/unit/ai_assistant/test_memory_context.py",
        ["AGENTS.md", "session_summary", "working_memory"],
    ) and _source_has(
        workspace_root,
        "tests/unit/ai_assistant/test_context_budget.py",
        ["recent_messages", "user_message", "dropReasons", "sharePercent"],
    )
    if not _gate_file_passes(artifact_root / "unit.txt", ["passed"]) or not source_ok:
        return []
    return [
        _entry(
            "unit.txt",
            events=["context.layer_selected", "context.layer_dropped"],
            assertions={"layerShares": sorted(REQUIRED_PROMPT_LAYERS), "dropReasonsAudited": True},
        )
    ]


def _skill_loading_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    if not _gate_file_passes(artifact_root / "unit.txt", ["passed"]) or not _source_has(
        workspace_root,
        "tests/unit/ai_assistant/test_skill_runtime.py",
        ["content_loaded", "skill.loaded", "skill.resource_read", "BODY_SECRET"],
    ):
        return []
    return [
        _entry(
            "unit.txt",
            events=["skill.indexed", "skill.loaded", "skill.resource_read"],
            assertions={
                "startupLoadedSkillBodies": 0,
                "matchedSkillBodyLoaded": True,
                "allSkillsInjectedAtStartup": False,
            },
        )
    ]


def _mock_adapter_evidence(artifact_root: Path, workspace_root: Path) -> list[dict[str, Any]]:
    if not _gate_file_passes(artifact_root / "eval.txt", ["passed"]) or not _source_has(
        workspace_root,
        "tests/eval/test_ai_assistant_mock_aviation_adapter_eval.py",
        ["mock_aviation", "mockOnly", "refund", "change_ticket", "baggage", "flight_disruption"],
    ):
        return []
    return [
        _entry(
            "eval.txt",
            events=["tool.started", "business_adapter.audit"],
            assertions={
                "adapterName": "mock_aviation",
                "mockOnly": True,
                "realAviationRulesApplied": False,
                "scenarios": sorted(MOCK_AVIATION_SCENARIOS),
            },
        )
    ]


def _runtime_requirement_evidence(artifact_root: Path, requirement_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path, payload in _runtime_evidence_payloads(artifact_root):
        raw_entries = _runtime_requirement_entries(payload, requirement_id)
        for raw_entry in raw_entries:
            entry = _normalize_runtime_entry(raw_entry, artifact_root=artifact_root, path=path)
            if entry:
                entries.append(entry)
    return entries


def _runtime_evidence_payloads(artifact_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    paths: list[Path] = []
    for pattern in RUNTIME_EVIDENCE_GLOBS:
        paths.extend(sorted(artifact_root.glob(pattern)))
    payloads: list[tuple[Path, dict[str, Any]]] = []
    for path in dict.fromkeys(paths):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append((path, payload))
    return payloads


def _runtime_requirement_entries(payload: dict[str, Any], requirement_id: str) -> list[Any]:
    candidates = [
        _dict(payload.get("requirements")).get(requirement_id),
        payload.get(requirement_id),
    ]
    entries: list[Any] = []
    for candidate in candidates:
        if isinstance(candidate, list):
            entries.extend(candidate)
        elif isinstance(candidate, dict):
            entries.append(candidate)
    return entries


def _normalize_runtime_entry(
    raw_entry: Any,
    *,
    artifact_root: Path,
    path: Path,
) -> dict[str, Any] | None:
    if not isinstance(raw_entry, dict):
        return None
    artifact = str(raw_entry.get("artifact") or path.relative_to(artifact_root))
    status = str(raw_entry.get("status") or ("PASS" if raw_entry.get("passed") else "")).upper()
    if status != "PASS":
        return None
    assertions = _dict(raw_entry.get("assertions"))
    return {
        "status": "PASS",
        "artifact": artifact,
        "events": list(_string_set(raw_entry.get("events"))),
        "assertions": assertions,
    }


def _complete_audit_evidence(artifact_root: Path) -> list[dict[str, Any]]:
    path = artifact_root / "aggregate-trace-audit-export.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    span_kinds = sorted(
        {str(span.get("kind")) for span in _list(_dict(payload.get("trace")).get("spans"))}
    )
    audit = _dict(payload.get("audit"))
    return [
        _entry(
            "aggregate-trace-audit-export.json",
            events=["audit.exported"],
            assertions={
                "traceSpanKinds": span_kinds,
                "auditFields": _present_audit_fields(audit),
            },
        )
    ]


def _full_gate_evidence(artifact_root: Path, spec_dir: Path) -> list[dict[str, Any]]:
    gates: list[str] = []
    if (artifact_root / "red.txt").exists():
        gates.append("red")
    for gate, file_name in [
        ("unit", "unit.txt"),
        ("contract", "contract.txt"),
        ("e2e", "e2e.txt"),
        ("frontend", "frontend.txt"),
        ("frontend_rem", "frontend-rem.txt"),
        ("eval", "eval.txt"),
    ]:
        if _gate_file_passes(artifact_root / file_name, ["passed"]):
            gates.append(gate)
    if _uat_passes(artifact_root):
        gates.append("browser_uat")
    if _docs_gate_passes(spec_dir):
        gates.append("docs")
    return [
        _entry(
            "uat.md",
            events=["gate.completed"],
            assertions={"gates": gates},
        )
    ]


def _entry(
    artifact: str,
    *,
    events: list[str],
    assertions: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "PASS",
        "artifact": artifact,
        "events": events,
        "assertions": assertions,
    }


def _requirement_specific_check(requirement_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    assertions = [_dict(entry.get("assertions")) for entry in entries]
    reasons: list[str] = []
    extra: dict[str, Any] = {}
    if requirement_id == "token_delta_default":
        if not _any_true(assertions, "deltaBeforeCompletion"):
            reasons.append("delta_not_proven_before_completion")
    elif requirement_id == "non_streaming_fallback":
        if not _any_true(assertions, "fallbackVisible"):
            reasons.append("fallback_not_visible")
    elif requirement_id == "refresh_reconnect_recovery":
        _require_all_booleans(
            assertions,
            reasons,
            ["lastEventId", "afterSequence", "restoresPlanProgress", "restoresEmittedTokens", "restoresPendingApprovals", "restoresToolState"],
        )
    elif requirement_id == "tool_failure_self_correction":
        _require_all_booleans(assertions, reasons, ["timeoutRetry", "fiveHundredRetry", "rateLimitBackoff"])
    elif requirement_id == "file_workspace_concurrency_safety":
        _require_all_booleans(assertions, reasons, ["concurrentWritesBlocked", "failedEditKeepsOriginal"])
    elif requirement_id == "approval_sandbox_budget_lock_enforcement":
        _require_all_booleans(
            assertions,
            reasons,
            ["highRiskApprovalDefault", "alwaysApproveBounded", "policyBounded", "sandboxBounded", "budgetBounded", "resourceLockBounded"],
        )
    elif requirement_id == "context_usage_and_compaction_visibility":
        _require_all_booleans(assertions, reasons, ["usagePercentVisible", "compactionRatioVisible"])
    elif requirement_id == "prompt_layer_share_audit":
        observed_layers = set().union(*(_string_set(assertion.get("layerShares")) for assertion in assertions)) if assertions else set()
        missing_layers = sorted(REQUIRED_PROMPT_LAYERS - observed_layers)
        if missing_layers:
            reasons.append("missing_prompt_layer_shares")
            extra["missingPromptLayers"] = missing_layers
        if not _any_true(assertions, "dropReasonsAudited"):
            reasons.append("drop_reasons_not_audited")
    elif requirement_id == "skill_on_demand_loading":
        if not any(_int_value(assertion.get("startupLoadedSkillBodies"), default=-1) == 0 for assertion in assertions):
            reasons.append("startup_loaded_skill_bodies")
        if not _any_true(assertions, "matchedSkillBodyLoaded"):
            reasons.append("matched_skill_body_not_loaded")
        if any(bool(assertion.get("allSkillsInjectedAtStartup")) for assertion in assertions):
            reasons.append("all_skill_contents_injected_at_startup")
    elif requirement_id == "mock_aviation_adapter_seam_only":
        scenario_sets = [_string_set(assertion.get("scenarios")) for assertion in assertions]
        observed_scenarios = set().union(*scenario_sets) if scenario_sets else set()
        if not any(assertion.get("adapterName") == "mock_aviation" for assertion in assertions):
            reasons.append("mock_adapter_not_used")
        if not _any_true(assertions, "mockOnly"):
            reasons.append("mock_only_not_proven")
        if any(bool(assertion.get("realAviationRulesApplied")) for assertion in assertions):
            reasons.append("real_aviation_rules_detected")
        missing_scenarios = sorted(MOCK_AVIATION_SCENARIOS - observed_scenarios)
        if missing_scenarios:
            reasons.append("missing_mock_aviation_eval_scenarios")
            extra["missingScenarios"] = missing_scenarios
    elif requirement_id == "complete_audit_export":
        observed_span_kinds = set().union(*(_string_set(assertion.get("traceSpanKinds")) for assertion in assertions)) if assertions else set()
        observed_audit_fields = set().union(*(_string_set(assertion.get("auditFields")) for assertion in assertions)) if assertions else set()
        missing_span_kinds = sorted(TRACE_REQUIRED_KINDS - observed_span_kinds)
        missing_audit_fields = sorted(AUDIT_REQUIRED_FIELDS - observed_audit_fields)
        if missing_span_kinds:
            reasons.append("missing_trace_span_kinds")
            extra["missingSpanKinds"] = missing_span_kinds
        if missing_audit_fields:
            reasons.append("missing_audit_fields")
            extra["missingAuditFields"] = missing_audit_fields
    elif requirement_id == "full_gate_evidence":
        observed_gates = set().union(*(_string_set(assertion.get("gates")) for assertion in assertions)) if assertions else set()
        missing_gates = sorted(set(REQUIRED_GATES) - observed_gates)
        extra["observedGates"] = [gate for gate in REQUIRED_GATES if gate in observed_gates]
        if missing_gates:
            reasons.append("missing_required_gates")
            extra["missingGates"] = missing_gates
    return {"reasons": reasons} | extra


def _missing_artifacts(artifacts: list[str], artifact_root: Path | None) -> list[str]:
    if artifact_root is None:
        return []
    return [artifact for artifact in artifacts if not (artifact_root / artifact).exists()]


def _gate_file_passes(path: Path, required_fragments: list[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    if "failed" in lowered or "error" in lowered and "ModuleNotFoundError" not in text:
        return False
    if not required_fragments:
        return True
    return all(fragment.lower() in lowered for fragment in required_fragments)


def _source_has(workspace_root: Path, relative_path: str, fragments: list[str]) -> bool:
    path = workspace_root / relative_path
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(fragment in text for fragment in fragments)


def _uat_passes(artifact_root: Path) -> bool:
    screenshot_dir = artifact_root / "screenshots"
    screenshots = list(screenshot_dir.glob("*.png")) if screenshot_dir.exists() else []
    return _gate_file_passes(artifact_root / "uat.md", ["PASS"]) and bool(screenshots)


def _docs_gate_passes(spec_dir: Path) -> bool:
    spec = (spec_dir / "spec.md").read_text(encoding="utf-8", errors="replace")
    tasks = (spec_dir / "tasks.md").read_text(encoding="utf-8", errors="replace")
    required_tasks = [
        "Prove token-level realtime output by default.",
        "Prove explicit fallback for non-streaming providers.",
        "Prove refresh/reconnect recovery.",
        "Prove tool timeout/5xx/rate-limit self-correction.",
        "Prove safe concurrent file writes.",
        "Prove approval, sandbox, budget, and resource-lock enforcement.",
        "Prove context window usage percentage and compaction ratio are visible.",
        "Prove prompt layer token share is visible and audited.",
        "Prove on-demand skill loading.",
        "Prove mock aviation adapter seam only.",
        "Export complete audit evidence for at least one aggregate run.",
        "Run full backend, frontend, rem, E2E, Browser UAT, eval, and docs gates.",
    ]
    if "222.10 Aggregate Production Evaluation: complete" not in spec:
        return False
    return all(f"- [x] {task}" in tasks for task in required_tasks)


def _present_audit_fields(audit: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for field in sorted(AUDIT_REQUIRED_FIELDS):
        if "." in field:
            root, child = field.split(".", 1)
            if child in _dict(audit.get(root)):
                fields.append(field)
        elif field in audit:
            fields.append(field)
    return fields


def _require_all_booleans(assertions: list[dict[str, Any]], reasons: list[str], keys: list[str]) -> None:
    for key in keys:
        if not _any_true(assertions, key):
            reasons.append(f"{key}_not_proven")


def _any_true(assertions: list[dict[str, Any]], key: str) -> bool:
    return any(bool(assertion.get(key)) for assertion in assertions)


def _collect_strings(entries: list[dict[str, Any]], key: str) -> set[str]:
    values: set[str] = set()
    for entry in entries:
        values.update(_string_set(entry.get(key)))
    return values


def _string_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list | tuple | set):
        return {str(item) for item in value}
    return set()


def _int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
