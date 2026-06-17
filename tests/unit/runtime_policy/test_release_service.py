import unittest

from app.core.errors import BizError
from app.modules.runtime_policy.domain.governance import RuntimePolicyReleaseService
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables
from tests.contract.test_runtime_policy_profile_api import _profile_payload
from tests.support.mysql import mysql8_unittest_database


class RuntimePolicyReleaseServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(
            self,
            "runtime_policy_release_unit",
            register=register_runtime_policy_tables,
        )
        assert self._database.session_factory is not None
        self._factory = self._database.session_factory

    def test_activate_requires_approval_even_after_evaluation_passes(self) -> None:
        with self._factory() as session:
            repository = RuntimePolicyRepository(session)
            profile = repository.create_profile(_profile_values("042.3 candidate"))
            _create_passed_runs(repository, profile)
            service = RuntimePolicyReleaseService(repository)

            with self.assertRaises(BizError):
                service.activate_profile(int(profile["id"]), activated_by="ops")

    def test_approve_canary_activate_switches_active_profile(self) -> None:
        with self._factory() as session:
            repository = RuntimePolicyRepository(session)
            baseline = repository.create_profile(_profile_values("042.3 active", status="active"))
            candidate = repository.create_profile(_profile_values("042.3 candidate"))
            _create_passed_runs(repository, candidate)
            service = RuntimePolicyReleaseService(repository)

            approved = service.approve_profile(int(candidate["id"]), approved_by="ops")
            canary = service.canary_profile(int(candidate["id"]), canary_percent=25)
            activated = service.activate_profile(int(candidate["id"]), activated_by="ops")

            self.assertEqual(approved["status"], "approved")
            self.assertEqual(canary["status"], "canary")
            self.assertEqual(canary["canaryPercent"], 25)
            self.assertEqual(activated["status"], "active")
            self.assertEqual(activated["previousActiveProfileId"], baseline["id"])
            self.assertEqual(repository.get_profile(int(candidate["id"]))["status"], "active")
            self.assertEqual(repository.get_profile(int(baseline["id"]))["status"], "archived")

    def test_rollback_restores_previous_active_profile_and_records_audit(self) -> None:
        with self._factory() as session:
            repository = RuntimePolicyRepository(session)
            baseline = repository.create_profile(_profile_values("042.4 previous", status="active"))
            candidate = repository.create_profile(_profile_values("042.4 candidate"))
            _create_passed_runs(repository, candidate)
            service = RuntimePolicyReleaseService(repository)
            service.approve_profile(int(candidate["id"]), approved_by="ops")
            activated = service.activate_profile(int(candidate["id"]), activated_by="ops")

            rolled_back = service.rollback_release(
                int(activated["id"]),
                rolled_back_by="ops",
                reason="bad route mix",
            )

            self.assertEqual(rolled_back["status"], "rolled_back")
            self.assertEqual(rolled_back["rolledBackBy"], "ops")
            self.assertEqual(rolled_back["rollbackReason"], "bad route mix")
            self.assertEqual(repository.get_profile(int(baseline["id"]))["status"], "active")
            self.assertEqual(repository.get_profile(int(candidate["id"]))["status"], "archived")
            self.assertEqual(
                [event["eventType"] for event in rolled_back["auditEvents"]],
                ["release_approved", "release_activated", "release_rolled_back"],
            )

    def test_release_transitions_emit_audit_events(self) -> None:
        with self._factory() as session:
            repository = RuntimePolicyRepository(session)
            repository.create_profile(_profile_values("042.4 active", status="active"))
            candidate = repository.create_profile(_profile_values("042.4 candidate"))
            _create_passed_runs(repository, candidate)
            service = RuntimePolicyReleaseService(repository)

            approved = service.approve_profile(int(candidate["id"]), approved_by="ops")
            canary = service.canary_profile(int(candidate["id"]), canary_percent=15)
            activated = service.activate_profile(int(candidate["id"]), activated_by="ops")

            self.assertEqual(
                [event["eventType"] for event in approved["auditEvents"]],
                ["release_approved"],
            )
            self.assertEqual(
                [event["eventType"] for event in canary["auditEvents"]],
                ["release_approved", "release_canary"],
            )
            self.assertEqual(
                [event["eventType"] for event in activated["auditEvents"]],
                ["release_approved", "release_canary", "release_activated"],
            )


def _profile_values(name: str, *, status: str = "draft") -> dict[str, object]:
    payload = _profile_payload(name)
    payload["status"] = status
    return {
        "name": payload["name"],
        "description": payload["description"],
        "status": payload["status"],
        "mode": payload["mode"],
        "bindings": payload["bindings"],
        "thresholds": payload["thresholds"],
        "classifier": payload["classifier"],
        "faq": payload["faq"],
        "rag": payload["rag"],
        "fallback_agent": payload["fallbackAgent"],
        "handoff": payload["handoff"],
        "audit": payload["audit"],
    }


def _create_passed_runs(repository: RuntimePolicyRepository, profile: dict[str, object]) -> None:
    for run_type in ("validation", "golden_matrix", "decision_log_replay"):
        repository.create_evaluation_run(
            {
                "profile_id": profile["id"],
                "profile_version": profile["version"],
                "run_type": run_type,
                "status": "passed",
                "input_snapshot": {},
                "result": {"passed": True, "failureReasons": []},
                "metrics": {},
                "risk_deltas": {"unsupportedActionCount": 0},
                "failure_reasons": [],
                "guardrails": {},
            }
        )


if __name__ == "__main__":
    unittest.main()
