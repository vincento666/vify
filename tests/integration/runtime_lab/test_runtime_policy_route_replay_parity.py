import unittest
from collections.abc import Generator
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.faq_gate import RuntimeAirlineFaqGate
from app.modules.runtime_lab.domain.rag_gate import FakeRagAnswerGenerator, RagAnswerGate
from app.modules.runtime_lab.domain.route_replay import replay_runtime_route
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables
from tests.contract.test_runtime_policy_profile_api import _profile_payload
from tests.integration.runtime_lab.test_runtime_lab_rag_policy import (
    _KnowledgeHit,
    _RagFirstClassifier,
    _RecordingKnowledgeFacade,
)
from tests.support.mysql import mysql8_unittest_database


class RuntimePolicyRouteReplayParityTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(
            self,
            "runtime_policy_route_replay_parity",
            register=register_runtime_policy_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_shared_decision_matches_mysql_handle_command_matrix(self) -> None:
        with self._factory() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(
                repository,
                faq_answer_gate=RuntimeAirlineFaqGate(),
            )
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            self._assert_command_parity(service, repository, session_id, "我要退票", "START_SOP")
            self._assert_command_parity(service, repository, session_id, "我要改签", "SUSPEND_AND_START")
            self._assert_command_parity(
                service,
                repository,
                session_id,
                "我要订机票",
                "REJECT_SWITCH_SUSPENDED_LIMIT",
            )

            faq_session_id = int(service.create_session()["id"])
            self._assert_command_parity(
                service,
                repository,
                faq_session_id,
                "儿童票可以退吗",
                "ANSWER_FAQ",
            )
            handoff_session_id = int(service.create_session()["id"])
            self._assert_command_parity(
                service,
                repository,
                handoff_session_id,
                "我要人工客服",
                "HANDOFF_TO_HUMAN",
            )

            rag_service = RuntimeLabService(
                repository,
                rag_answer_gate=RagAnswerGate(
                    _RecordingKnowledgeFacade(
                        [
                            _KnowledgeHit(
                                source_type="DOCUMENT_CHUNK",
                                match_type="VECTOR",
                                score=0.94,
                                title="航班延误险条款",
                                content="航班延误超过 4 小时，可提交保险理赔申请。",
                                document_id=7,
                                chunk_id=70,
                                chunk_index=0,
                            )
                        ]
                    ),
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
                classifier=_RagFirstClassifier(),
            )
            rag_session_id = int(rag_service.create_session()["id"])
            self._assert_command_parity(
                rag_service,
                repository,
                rag_session_id,
                "我要退票，航班延误超过 4 小时保险怎么赔？",
                "ANSWER_RAG",
            )

    def test_candidate_profile_snapshot_is_separate_from_current_active_public_profile(self) -> None:
        baseline = _profile_payload("228.2 active public baseline")
        baseline["status"] = "active"
        baseline["bindings"] = {
            **baseline["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }
        candidate = _profile_payload("228.2 draft candidate")
        candidate["thresholds"] = {
            **candidate["thresholds"],
            "candidateSourceWeights": {
                "explicit_signal": 0.2,
                "mock_semantic_recall": 0.2,
                "sop_hybrid_recall": 0.2,
            },
        }

        with TestClient(app) as client:
            active_profile = client.post("/api/v1/runtime-policy/profiles", json=baseline)
            candidate_profile = client.post("/api/v1/runtime-policy/profiles", json=candidate)
            candidate_id = candidate_profile.json()["data"]["id"]
            runtime_session = client.post("/api/v1/runtime-lab/sessions")
            session_id = runtime_session.json()["data"]["id"]
            message = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票", "idempotencyKey": "2282-parity"},
            )
            replayed = client.post(f"/api/v1/runtime-policy/profiles/{candidate_id}/replay/golden-matrix")

        self.assertEqual(active_profile.status_code, 200)
        self.assertEqual(candidate_profile.status_code, 200)
        self.assertEqual(message.status_code, 200)
        public_decision = message.json()["data"]["routeDecision"]
        self.assertEqual(public_decision["action"], "START_SOP")
        self.assertEqual(replayed.status_code, 200)
        replay = replayed.json()["data"]
        refund_case = next(case for case in replay["result"]["cases"] if case["id"] == "sop-start")
        self.assertEqual(replay["profileId"], candidate_id)
        self.assertEqual(replay["inputSnapshot"]["profileId"], candidate_id)
        self.assertEqual(refund_case["actual"]["action"], "CLARIFY")
        self.assertNotEqual(refund_case["actual"]["action"], public_decision["action"])
        self.assertFalse(replay["passed"])

    def test_historical_replay_uses_pre_route_context_and_preserves_comparison(self) -> None:
        baseline = _profile_payload("228.2 historical baseline")
        baseline["status"] = "active"
        baseline["bindings"] = {
            **baseline["bindings"],
            "tenantId": "",
            "botId": "",
            "channel": "",
            "sopGroup": "",
        }
        candidate = _profile_payload("228.2 historical candidate")
        candidate["thresholds"] = {
            **candidate["thresholds"],
            "candidateSourceWeights": {
                "explicit_signal": 0.2,
                "mock_semantic_recall": 0.2,
                "sop_hybrid_recall": 0.2,
            },
        }

        with TestClient(app) as client:
            baseline_response = client.post("/api/v1/runtime-policy/profiles", json=baseline)
            baseline_id = baseline_response.json()["data"]["id"]
            candidate_response = client.post("/api/v1/runtime-policy/profiles", json=candidate)
            candidate_id = candidate_response.json()["data"]["id"]
            session_ids = [
                client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
                for _ in range(3)
            ]
            with self._factory() as session:
                repository = RuntimeLabRepository(session)
                repository.create_task(session_ids[1], "refund_ticket", status="RUNNING")
                repository.create_task(session_ids[2], "refund_ticket", status="SUSPENDED")
                repository.create_task(session_ids[2], "invoice_apply", status="RUNNING")
            messages = (
                (session_ids[0], "我要退票", "2282-history-no-active"),
                (session_ids[1], "我要改签", "2282-history-active"),
                (session_ids[2], "我要订机票", "2282-history-suspended"),
            )
            for session_id, message, key in messages:
                response = client.post(
                    f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                    json={"message": message, "idempotencyKey": key},
                )
                self.assertEqual(response.status_code, 200)
            baseline_replays = [
                client.post(
                    f"/api/v1/runtime-policy/profiles/{baseline_id}/replay/decision-logs",
                    json={"sessionId": session_id},
                ).json()["data"]
                for session_id in session_ids
            ]
            candidate_replay = client.post(
                f"/api/v1/runtime-policy/profiles/{candidate_id}/replay/decision-logs",
                json={"sessionId": session_ids[0]},
            ).json()["data"]
            logs = [
                client.get(
                    f"/api/v1/runtime-policy/sessions/{session_id}/decision-logs"
                ).json()["data"]["list"][0]
                for session_id in session_ids
            ]

        self.assertTrue(
            all(replay["passed"] for replay in baseline_replays),
            baseline_replays,
        )
        self.assertTrue(all(replay["result"]["changedDecisionCount"] == 0 for replay in baseline_replays))
        contexts = [log["routeEvidence"]["routeContextSnapshot"] for log in logs]
        self.assertEqual(contexts[0]["snapshotVersion"], "runtime-route-context/v1")
        self.assertIsNone(contexts[0]["activeTask"])
        self.assertEqual(contexts[1]["activeTask"]["sop_id"], "refund_ticket")
        self.assertEqual(contexts[2]["activeTask"]["sop_id"], "invoice_apply")
        self.assertEqual(contexts[2]["suspendedTasks"][0]["sop_id"], "refund_ticket")
        self.assertFalse(candidate_replay["passed"])
        self.assertEqual(candidate_replay["result"]["changedDecisionCount"], 1)

    def test_public_replay_fails_closed_when_shared_decision_faults(self) -> None:
        candidate = _profile_payload("228.2 shared fault")

        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=candidate)
            candidate_id = created.json()["data"]["id"]
            with patch.object(
                RuntimeLabService,
                "preview_route",
                side_effect=RuntimeError("shared route decision fault"),
            ):
                replayed = client.post(
                    f"/api/v1/runtime-policy/profiles/{candidate_id}/replay/golden-matrix"
                )
            listed = client.get(
                "/api/v1/runtime-policy/evaluation-runs",
                params={"profileId": candidate_id},
            )

        self.assertEqual(replayed.status_code, 500)
        self.assertEqual(
            replayed.json(),
            {"code": 500, "message": "Internal Server Error", "data": None},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 0)

    def _assert_command_parity(
        self,
        service: RuntimeLabService,
        repository: RuntimeLabRepository,
        session_id: int,
        message: str,
        expected_action: str,
    ) -> None:
        active_task = repository.get_active_task(session_id)
        suspended_tasks = repository.list_tasks(session_id, statuses={"SUSPENDED"})
        replayed = replay_runtime_route(
            service,
            {
                "turns": [{"role": "user", "message": message}],
                "initialRouteContext": {
                    "sessionId": session_id,
                    "activeTask": active_task,
                    "suspendedTasks": suspended_tasks,
                },
                "enabledIntentIds": None,
            },
        )
        command = service.handle_command(session_id, message)
        public_decision = command.payload["routeDecision"]

        self.assertEqual(replayed["action"], expected_action)
        self.assertEqual(public_decision["action"], replayed["action"])
        self.assertEqual(public_decision["targetSopId"], replayed["targetSopId"])
        public_candidate_ids = [
            candidate["candidate_id"]
            for candidate in public_decision["candidates"]
        ]
        self.assertEqual(public_candidate_ids, replayed["recalledCandidateIds"])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
