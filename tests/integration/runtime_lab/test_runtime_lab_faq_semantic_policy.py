import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.domain.faq_gate import FaqSemanticAnswerGate
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabFaqSemanticPolicyTest(unittest.TestCase):
    def test_paraphrased_faq_answers_before_sop_arbitration(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                [
                    _KnowledgeHit(
                        source_type="FAQ",
                        match_type="VECTOR",
                        score=0.93,
                        title="儿童票退票规则",
                        answer="儿童票如未使用可按客票规则申请退票。",
                        faq_id=37,
                    ),
                    _KnowledgeHit(
                        source_type="FAQ",
                        match_type="VECTOR",
                        score=0.70,
                        title="婴儿票退票规则",
                        answer="婴儿票退票以客票规则为准。",
                        faq_id=38,
                    ),
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                faq_semantic_gate=FaqSemanticAnswerGate(facade, knowledge_base_ids=[33], rerank=True),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "儿童机票能不能返钱？")

            self.assertEqual(turn.reply, "儿童票如未使用可按客票规则申请退票。")
            self.assertEqual(turn.route_decision.action, "ANSWER_FAQ")
            self.assertEqual(turn.route_decision.faq_answer["sourceLayer"], "faq_semantic")
            self.assertEqual(turn.route_decision.faq_answer["reasonCode"], "SEMANTIC_HIGH_CONFIDENCE")
            self.assertIsNone(turn.active_task)
            self.assertIsNotNone(turn.route_decision.classifier_request)
            self.assertEqual(turn.route_decision.policy_gate["stage"], "post_classifier")
            self.assertEqual(facade.calls[0]["retrieval_mode"], "faq")
            self.assertTrue(facade.calls[0]["rerank"])

    def test_low_margin_semantic_faq_clarifies_without_sop_arbitration(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                [
                    _KnowledgeHit(
                        source_type="FAQ",
                        match_type="VECTOR",
                        score=0.88,
                        title="儿童票退票规则",
                        answer="儿童票如未使用可按客票规则申请退票。",
                        faq_id=37,
                    ),
                    _KnowledgeHit(
                        source_type="FAQ",
                        match_type="VECTOR",
                        score=0.84,
                        title="儿童票改签规则",
                        answer="儿童票改签按客票规则办理。",
                        faq_id=39,
                    ),
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                faq_semantic_gate=FaqSemanticAnswerGate(facade, knowledge_base_ids=[33], rerank=True),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "儿童机票规则怎么算？")

            self.assertEqual(turn.route_decision.action, "CLARIFY")
            self.assertEqual(turn.route_decision.faq_answer["sourceLayer"], "faq_semantic")
            self.assertEqual(turn.route_decision.faq_answer["reasonCode"], "SEMANTIC_LOW_MARGIN")
            self.assertFalse(turn.route_decision.faq_answer["mutatesSopState"])
            self.assertIsNotNone(turn.route_decision.classifier_request)
            self.assertEqual(turn.route_decision.policy_gate["stage"], "post_classifier")

    def test_active_sop_semantic_faq_with_slot_payload_clarifies_without_task_mutation(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                {
                    "儿童机票能不能返钱？订单TK-100": [
                        _KnowledgeHit(
                            source_type="FAQ",
                            match_type="VECTOR",
                            score=0.94,
                            title="儿童票退票规则",
                            answer="儿童票如未使用可按客票规则申请退票。",
                            faq_id=37,
                        ),
                        _KnowledgeHit(
                            source_type="FAQ",
                            match_type="VECTOR",
                            score=0.71,
                            title="婴儿票退票规则",
                            answer="婴儿票退票以客票规则为准。",
                            faq_id=38,
                        ),
                    ],
                }
            )
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(
                repository,
                faq_semantic_gate=FaqSemanticAnswerGate(facade, knowledge_base_ids=[33], rerank=True),
            )
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            started = service.handle_message(session_id, "我要退票")
            before = dict(started.active_task)
            clarified = service.handle_message(session_id, "儿童机票能不能返钱？订单TK-100")
            after_checkpoint = repository.get_latest_checkpoint(int(before["id"]))

            self.assertEqual(clarified.route_decision.action, "CLARIFY")
            self.assertEqual(clarified.route_decision.faq_answer["sourceLayer"], "faq_semantic")
            self.assertEqual(clarified.route_decision.faq_answer["reasonCode"], "SEMANTIC_ACTIVE_AMBIGUOUS")
            self.assertEqual(clarified.active_task["id"], before["id"])
            self.assertEqual(clarified.active_task["current_step"], before["current_step"])
            self.assertEqual(clarified.active_task["checkpoint_id"], before["checkpoint_id"])
            self.assertEqual(after_checkpoint["id"], before["checkpoint_id"])
            self.assertNotIn("TASK_CONTINUED", [event["event_type"] for event in clarified.events])


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_faq_semantic_policy.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_runtime_lab_tables()
    tables = [
        Base.metadata.tables["runtime_lab_session"],
        Base.metadata.tables["runtime_lab_task"],
        Base.metadata.tables["runtime_lab_checkpoint"],
        Base.metadata.tables["runtime_lab_event"],
        Base.metadata.tables["runtime_lab_command"],
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


class _KnowledgeHit:
    def __init__(
        self,
        *,
        source_type: str,
        match_type: str,
        score: float,
        title: str,
        answer: str,
        faq_id: int,
    ) -> None:
        self.source_type = source_type
        self.match_type = match_type
        self.score = score
        self.title = title
        self.answer = answer
        self.faq_id = faq_id


class _RecordingKnowledgeFacade:
    def __init__(self, hits: list[_KnowledgeHit] | dict[str, list[_KnowledgeHit]]) -> None:
        self._hits = hits
        self.calls: list[dict[str, object]] = []

    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list[_KnowledgeHit]:
        self.calls.append(
            {
                "knowledge_base_id": knowledge_base_id,
                "query": query,
                "top_k": top_k,
                "retrieval_mode": retrieval_mode,
                "score_threshold": score_threshold,
                "rerank": rerank,
            }
        )
        if isinstance(self._hits, dict):
            return self._hits.get(query, [])
        return self._hits
