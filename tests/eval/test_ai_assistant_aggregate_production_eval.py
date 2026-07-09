from __future__ import annotations

import json
from pathlib import Path

from app.modules.ai_assistant.domain.aggregate_production_eval import (
    AGGREGATE_ACCEPTANCE_REQUIREMENTS,
    build_aggregate_evidence_from_artifacts,
    build_aggregate_production_markdown,
    build_aggregate_production_report,
    write_aggregate_production_report,
)


EXPECTED_REQUIREMENT_IDS = [
    "token_delta_default",
    "non_streaming_fallback",
    "refresh_reconnect_recovery",
    "tool_failure_self_correction",
    "file_workspace_concurrency_safety",
    "approval_sandbox_budget_lock_enforcement",
    "context_usage_and_compaction_visibility",
    "prompt_layer_share_audit",
    "skill_on_demand_loading",
    "mock_aviation_adapter_seam_only",
    "complete_audit_export",
    "full_gate_evidence",
]


def test_aggregate_production_eval_requires_all_mvp_acceptance_evidence(tmp_path: Path) -> None:
    evidence = _complete_evidence(tmp_path)
    report = build_aggregate_production_report(evidence, artifact_root=tmp_path)

    assert report["passed"] is True
    assert report["summary"] == {
        "total": 12,
        "passed": 12,
        "failed": 0,
    }
    assert [check["id"] for check in report["checks"]] == EXPECTED_REQUIREMENT_IDS
    assert [item["id"] for item in AGGREGATE_ACCEPTANCE_REQUIREMENTS] == EXPECTED_REQUIREMENT_IDS
    assert report["gateSummary"]["passed"] is True
    assert report["gateSummary"]["requiredGates"] == [
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

    markdown = build_aggregate_production_markdown(report)
    assert "# AI Assistant Aggregate Production Evaluation" in markdown
    assert "| token_delta_default | PASS |" in markdown
    assert "| mock_aviation_adapter_seam_only | PASS |" in markdown


def test_aggregate_production_eval_fails_when_any_required_evidence_is_missing(tmp_path: Path) -> None:
    evidence = _complete_evidence(tmp_path)
    evidence.pop("skill_on_demand_loading")

    report = build_aggregate_production_report(evidence, artifact_root=tmp_path)

    assert report["passed"] is False
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["skill_on_demand_loading"]["passed"] is False
    assert "missing_required_evidence" in checks["skill_on_demand_loading"]["reasons"]


def test_aggregate_production_eval_rejects_real_aviation_rules(tmp_path: Path) -> None:
    evidence = _complete_evidence(tmp_path)
    evidence["mock_aviation_adapter_seam_only"][0]["assertions"]["realAviationRulesApplied"] = True

    report = build_aggregate_production_report(evidence, artifact_root=tmp_path)

    assert report["passed"] is False
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["mock_aviation_adapter_seam_only"]["passed"] is False
    assert "real_aviation_rules_detected" in checks["mock_aviation_adapter_seam_only"]["reasons"]


def test_aggregate_production_eval_rejects_incomplete_audit_export(tmp_path: Path) -> None:
    evidence = _complete_evidence(tmp_path)
    evidence["complete_audit_export"][0]["assertions"]["auditFields"].remove("adapterAudits")

    report = build_aggregate_production_report(evidence, artifact_root=tmp_path)

    assert report["passed"] is False
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["complete_audit_export"]["passed"] is False
    assert "missing_audit_fields" in checks["complete_audit_export"]["reasons"]
    assert "adapterAudits" in checks["complete_audit_export"]["missingAuditFields"]


def test_aggregate_production_eval_assembles_real_artifact_evidence(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts" / "222.10"
    workspace_root = tmp_path / "workspace"
    spec_dir = workspace_root / "specs" / "222-ai-assistant-general-harness-mvp"
    _write_realistic_artifacts(artifact_root)
    _write_realistic_sources(workspace_root)
    _write_runtime_evidence(artifact_root)
    _write_complete_docs(spec_dir)
    _write_complete_audit_export(artifact_root)

    evidence = build_aggregate_evidence_from_artifacts(
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        spec_dir=spec_dir,
    )
    report = build_aggregate_production_report(evidence, artifact_root=artifact_root)

    assert report["passed"] is True
    assert all(check["evidenceCount"] > 0 for check in report["checks"])
    complete_audit = {check["id"]: check for check in report["checks"]}["complete_audit_export"]
    assert complete_audit["artifacts"] == ["aggregate-trace-audit-export.json"]
    full_gate = {check["id"]: check for check in report["checks"]}["full_gate_evidence"]
    assert full_gate["observedGates"] == [
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


def test_aggregate_production_eval_fails_without_real_audit_export_artifact(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts" / "222.10"
    workspace_root = tmp_path / "workspace"
    spec_dir = workspace_root / "specs" / "222-ai-assistant-general-harness-mvp"
    _write_realistic_artifacts(artifact_root)
    _write_realistic_sources(workspace_root)
    _write_runtime_evidence(artifact_root)
    _write_complete_docs(spec_dir)

    evidence = build_aggregate_evidence_from_artifacts(
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        spec_dir=spec_dir,
    )
    report = build_aggregate_production_report(evidence, artifact_root=artifact_root)

    assert report["passed"] is False
    complete_audit = {check["id"]: check for check in report["checks"]}["complete_audit_export"]
    assert complete_audit["passed"] is False
    assert "missing_required_evidence" in complete_audit["reasons"]


def test_aggregate_production_eval_rejects_source_only_runtime_proofs(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts" / "222.10"
    workspace_root = tmp_path / "workspace"
    spec_dir = workspace_root / "specs" / "222-ai-assistant-general-harness-mvp"
    _write_realistic_artifacts(artifact_root)
    _write_realistic_sources(workspace_root)
    _write_complete_docs(spec_dir)
    _write_complete_audit_export(artifact_root)

    evidence = build_aggregate_evidence_from_artifacts(
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        spec_dir=spec_dir,
    )
    report = build_aggregate_production_report(evidence, artifact_root=artifact_root)
    checks = {check["id"]: check for check in report["checks"]}

    for requirement_id in [
        "token_delta_default",
        "refresh_reconnect_recovery",
        "tool_failure_self_correction",
        "file_workspace_concurrency_safety",
        "context_usage_and_compaction_visibility",
    ]:
        assert checks[requirement_id]["passed"] is False
        assert "missing_runtime_evidence" in checks[requirement_id]["reasons"]


def test_aggregate_production_eval_fails_when_docs_gate_is_open(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts" / "222.10"
    workspace_root = tmp_path / "workspace"
    spec_dir = workspace_root / "specs" / "222-ai-assistant-general-harness-mvp"
    _write_realistic_artifacts(artifact_root)
    _write_realistic_sources(workspace_root)
    _write_runtime_evidence(artifact_root)
    _write_incomplete_docs(spec_dir)
    _write_complete_audit_export(artifact_root)

    evidence = build_aggregate_evidence_from_artifacts(
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        spec_dir=spec_dir,
    )
    report = build_aggregate_production_report(evidence, artifact_root=artifact_root)

    assert report["passed"] is False
    full_gate = {check["id"]: check for check in report["checks"]}["full_gate_evidence"]
    assert "docs" in full_gate["missingGates"]


def test_aggregate_production_eval_writes_required_markdown_report(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts" / "222.10"
    workspace_root = tmp_path / "workspace"
    spec_dir = workspace_root / "specs" / "222-ai-assistant-general-harness-mvp"
    _write_realistic_artifacts(artifact_root)
    _write_realistic_sources(workspace_root)
    _write_runtime_evidence(artifact_root)
    _write_complete_docs(spec_dir)
    _write_complete_audit_export(artifact_root)

    report_path = write_aggregate_production_report(
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        spec_dir=spec_dir,
    )

    assert report_path == artifact_root / "aggregate-production-report.md"
    markdown = report_path.read_text(encoding="utf-8")
    assert "- Evidence source: real artifact assembly" in markdown
    assert "| complete_audit_export | PASS | aggregate-trace-audit-export.json |" in markdown
    payload = json.loads((artifact_root / "aggregate-production-report.json").read_text(encoding="utf-8"))
    assert payload["passed"] is True


def _complete_evidence(tmp_path: Path) -> dict[str, list[dict[str, object]]]:
    return {
        "token_delta_default": [
            _evidence(
                tmp_path,
                "streaming.txt",
                events=["text.delta", "run.completed"],
                assertions={"deltaBeforeCompletion": True},
            )
        ],
        "non_streaming_fallback": [
            _evidence(
                tmp_path,
                "streaming.txt",
                events=["stream.fallback"],
                assertions={"fallbackVisible": True},
            )
        ],
        "refresh_reconnect_recovery": [
            _evidence(
                tmp_path,
                "session.txt",
                events=["heartbeat", "run.snapshot"],
                assertions={
                    "lastEventId": True,
                    "afterSequence": True,
                    "restoresPlanProgress": True,
                    "restoresEmittedTokens": True,
                    "restoresPendingApprovals": True,
                    "restoresToolState": True,
                },
            )
        ],
        "tool_failure_self_correction": [
            _evidence(
                tmp_path,
                "tool-runtime.txt",
                events=["tool.retry_scheduled", "tool.error_observation", "plan.revised"],
                assertions={"timeoutRetry": True, "fiveHundredRetry": True, "rateLimitBackoff": True},
            )
        ],
        "file_workspace_concurrency_safety": [
            _evidence(
                tmp_path,
                "file-workspace.txt",
                events=["file.edit_preview", "resource_lock.acquired"],
                assertions={"concurrentWritesBlocked": True, "failedEditKeepsOriginal": True},
            )
        ],
        "approval_sandbox_budget_lock_enforcement": [
            _evidence(
                tmp_path,
                "security.txt",
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
        ],
        "context_usage_and_compaction_visibility": [
            _evidence(
                tmp_path,
                "context.txt",
                events=["context.budget_estimated", "context.compaction_completed"],
                assertions={"usagePercentVisible": True, "compactionRatioVisible": True},
            )
        ],
        "prompt_layer_share_audit": [
            _evidence(
                tmp_path,
                "context.txt",
                events=["context.layer_selected", "context.layer_dropped"],
                assertions={
                    "layerShares": [
                        "AGENTS.md",
                        "session_summary",
                        "working_memory",
                        "recent_messages",
                        "tools",
                        "skills",
                        "user_message",
                    ],
                    "dropReasonsAudited": True,
                },
            )
        ],
        "skill_on_demand_loading": [
            _evidence(
                tmp_path,
                "skill.txt",
                events=["skill.indexed", "skill.loaded", "skill.resource_read"],
                assertions={"startupLoadedSkillBodies": 0, "matchedSkillBodyLoaded": True, "allSkillsInjectedAtStartup": False},
            )
        ],
        "mock_aviation_adapter_seam_only": [
            _evidence(
                tmp_path,
                "mock-aviation.txt",
                events=["tool.started", "business_adapter.audit"],
                assertions={
                    "adapterName": "mock_aviation",
                    "mockOnly": True,
                    "realAviationRulesApplied": False,
                    "scenarios": ["refund", "change_ticket", "baggage", "flight_disruption"],
                },
            )
        ],
        "complete_audit_export": [
            _evidence(
                tmp_path,
                "audit.txt",
                events=["audit.exported"],
                assertions={
                    "traceSpanKinds": [
                        "run",
                        "model",
                        "tool",
                        "approval",
                        "stream",
                        "retry",
                        "fallback",
                        "skill",
                        "file_edit",
                        "resource_lock",
                        "context_budget",
                        "business_adapter",
                    ],
                    "auditFields": [
                        "prompt.layers",
                        "prompt.contextBudget",
                        "prompt.compactionSnapshot",
                        "plan",
                        "toolCalls",
                        "retries",
                        "fallbacks",
                        "approvals",
                        "tokenCost",
                        "fileDiffs",
                        "adapterAudits",
                        "contextBudget",
                        "compactionSnapshot",
                        "finalResult",
                    ],
                },
            )
        ],
        "full_gate_evidence": [
            _evidence(
                tmp_path,
                "gates.txt",
                events=["gate.completed"],
                assertions={
                    "gates": [
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
                },
            )
        ],
    }


def _write_realistic_artifacts(artifact_root: Path) -> None:
    artifact_root.mkdir(parents=True, exist_ok=True)
    files = {
        "red.txt": "ModuleNotFoundError: No module named 'app.modules.ai_assistant.domain.aggregate_production_eval'\n",
        "unit.txt": "71 passed, 4 subtests passed in 3.26s\n",
        "contract.txt": "47 passed, 1 warning in 53.69s\n",
        "e2e.txt": "10 passed, 1 skipped, 1 warning in 13.21s\n",
        "eval.txt": "7 passed in 0.02s\n",
        "frontend-focused.txt": "5 passed, 45 tests passed\n",
        "frontend-rem.txt": "1 passed\n",
        "frontend.txt": "99 test files passed, 430 tests passed\n",
        "ruff.txt": "All checks passed!\n",
        "py_compile.txt": "",
        "mypy-focused.txt": "Success: no issues found in 2 source files\n",
        "diff-check.txt": "",
        "uat.md": "# UAT\n\nAI Assistant shell detected: PASS.\nPlan/task surface detected: PASS.\nContext-budget surface detected: PASS.\nVerdict: PASS\n",
    }
    for name, content in files.items():
        (artifact_root / name).write_text(content, encoding="utf-8")
    screenshots = artifact_root / "screenshots"
    screenshots.mkdir()
    (screenshots / "uat-ai-assistant-page-viewport.png").write_bytes(b"png")


def _write_realistic_sources(workspace_root: Path) -> None:
    snippets = {
        "tests/contract/test_ai_assistant_streaming_api.py": (
            "text.delta model.call_completed stream.fallback provider_non_streaming "
            "Last-Event-ID afterSequence heartbeat run snapshot"
        ),
        "tests/contract/test_ai_assistant_session_runtime_api.py": (
            "checkpoint approvalQueue WAITING_APPROVAL write_workspace_file"
        ),
        "tests/unit/ai_assistant/test_tool_runtime.py": (
            "timeout rate limit tool.retry_scheduled tool.error_observation"
        ),
        "tests/contract/test_ai_assistant_tool_runtime_api.py": (
            "tool.error_observation plan.revised simulated 5xx"
        ),
        "tests/unit/ai_assistant/test_file_workspace.py": (
            "ThreadPoolExecutor PRECONDITION_FAILED rollbackSnapshot diffPreview"
        ),
        "tests/unit/ai_assistant/test_permission_policy_runtime.py": (
            "always_approve budgetLimit PermissionDecision.DENY"
        ),
        "tests/unit/ai_assistant/test_sandbox_runtime.py": "sandbox.evaluated denies_non_node",
        "tests/unit/ai_assistant/test_resource_lock.py": "CONTENDED concurrent_write_acquire",
        "tests/unit/ai_assistant/test_context_budget.py": (
            "usagePercent rawUsagePercent savedPercent recent_messages user_message "
            "dropReasons sharePercent"
        ),
        "tests/unit/ai_assistant/test_memory_context.py": (
            "AGENTS.md session_summary working_memory"
        ),
        "tests/unit/ai_assistant/test_skill_runtime.py": (
            "content_loaded skill.loaded skill.resource_read BODY_SECRET"
        ),
        "tests/eval/test_ai_assistant_mock_aviation_adapter_eval.py": (
            "mock_aviation mockOnly realAviationRulesApplied refund change_ticket baggage flight_disruption"
        ),
    }
    for path, content in snippets.items():
        file_path = workspace_root / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def _write_runtime_evidence(artifact_root: Path) -> None:
    runtime_evidence = {
        "version": 1,
        "source": "runtime-evidence-fixture",
        "requirements": {
            "token_delta_default": [
                {
                    "status": "PASS",
                    "events": ["text.delta", "run.completed"],
                    "assertions": {"deltaBeforeCompletion": True},
                }
            ],
            "refresh_reconnect_recovery": [
                {
                    "status": "PASS",
                    "events": ["heartbeat", "run.snapshot"],
                    "assertions": {
                        "lastEventId": True,
                        "afterSequence": True,
                        "restoresPlanProgress": True,
                        "restoresEmittedTokens": True,
                        "restoresPendingApprovals": True,
                        "restoresToolState": True,
                    },
                }
            ],
            "tool_failure_self_correction": [
                {
                    "status": "PASS",
                    "events": ["tool.retry_scheduled", "tool.error_observation", "plan.revised"],
                    "assertions": {
                        "timeoutRetry": True,
                        "fiveHundredRetry": True,
                        "rateLimitBackoff": True,
                    },
                }
            ],
            "file_workspace_concurrency_safety": [
                {
                    "status": "PASS",
                    "events": ["file.edit_preview", "resource_lock.acquired"],
                    "assertions": {
                        "concurrentWritesBlocked": True,
                        "failedEditKeepsOriginal": True,
                    },
                }
            ],
            "context_usage_and_compaction_visibility": [
                {
                    "status": "PASS",
                    "events": ["context.budget_estimated", "context.compaction_completed"],
                    "assertions": {
                        "usagePercentVisible": True,
                        "compactionRatioVisible": True,
                    },
                }
            ],
        },
    }
    (artifact_root / "runtime-evidence-fixture.json").write_text(
        json.dumps(runtime_evidence),
        encoding="utf-8",
    )


def _write_complete_docs(spec_dir: Path) -> None:
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text("222.10 Aggregate Production Evaluation: complete\n", encoding="utf-8")
    (spec_dir / "tasks.md").write_text(
        "- [x] Prove token-level realtime output by default.\n"
        "- [x] Prove explicit fallback for non-streaming providers.\n"
        "- [x] Prove refresh/reconnect recovery.\n"
        "- [x] Prove tool timeout/5xx/rate-limit self-correction.\n"
        "- [x] Prove safe concurrent file writes.\n"
        "- [x] Prove approval, sandbox, budget, and resource-lock enforcement.\n"
        "- [x] Prove context window usage percentage and compaction ratio are visible.\n"
        "- [x] Prove prompt layer token share is visible and audited.\n"
        "- [x] Prove on-demand skill loading.\n"
        "- [x] Prove mock aviation adapter seam only.\n"
        "- [x] Export complete audit evidence for at least one aggregate run.\n"
        "- [x] Run full backend, frontend, rem, E2E, Browser UAT, eval, and docs gates.\n",
        encoding="utf-8",
    )


def _write_incomplete_docs(spec_dir: Path) -> None:
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text("222.10 Aggregate Production Evaluation: pending\n", encoding="utf-8")
    (spec_dir / "tasks.md").write_text("- [ ] Prove token-level realtime output by default.\n", encoding="utf-8")


def _write_complete_audit_export(artifact_root: Path) -> None:
    export = {
        "trace": {
            "spans": [
                {"kind": kind}
                for kind in [
                    "run",
                    "model",
                    "tool",
                    "approval",
                    "stream",
                    "retry",
                    "fallback",
                    "skill",
                    "file_edit",
                    "resource_lock",
                    "context_budget",
                    "business_adapter",
                ]
            ]
        },
        "audit": {
            "prompt": {"layers": [], "contextBudget": {}, "compactionSnapshot": {}},
            "plan": {},
            "toolCalls": [],
            "retries": [],
            "fallbacks": [],
            "approvals": [],
            "tokenCost": {},
            "fileDiffs": [],
            "adapterAudits": [],
            "contextBudget": {},
            "compactionSnapshot": {},
            "finalResult": "done",
        },
    }
    (artifact_root / "aggregate-trace-audit-export.json").write_text(json.dumps(export), encoding="utf-8")


def _evidence(
    tmp_path: Path,
    artifact: str,
    *,
    events: list[str],
    assertions: dict[str, object],
) -> dict[str, object]:
    artifact_path = tmp_path / artifact
    artifact_path.write_text("PASS\n", encoding="utf-8")
    return {
        "status": "PASS",
        "artifact": artifact,
        "events": events,
        "assertions": assertions,
    }
