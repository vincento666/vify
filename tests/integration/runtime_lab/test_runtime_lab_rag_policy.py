import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.domain.rag_gate import FakeRagAnswerGenerator, RagAnswerGate
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabRagPolicyTest(unittest.TestCase):
    def test_long_tail_document_question_returns_cited_rag_answer(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                [
                    _KnowledgeHit(
                        source_type="DOCUMENT_CHUNK",
                        match_type="VECTOR",
                        score=0.91,
                        title="航班延误险条款",
                        content="航班延误超过 4 小时，可提交保险理赔申请。",
                        document_id=7,
                        chunk_id=70,
                        chunk_index=0,
                    )
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                rag_answer_gate=RagAnswerGate(
                    facade,
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "航班延误超过 4 小时保险怎么赔？")

            self.assertEqual(turn.route_decision.action, "ANSWER_RAG")
            self.assertIn("航班延误超过 4 小时", turn.reply)
            rag_answer = turn.route_decision.rag_answer
            self.assertEqual(rag_answer["sourceLayer"], "rag_policy")
            self.assertEqual(rag_answer["reasonCode"], "RAG_HIGH_CONFIDENCE")
            self.assertFalse(rag_answer["mutatesSopState"])
            self.assertEqual(rag_answer["citations"][0]["sourceId"], "chunk:70")
            self.assertEqual(rag_answer["retrievalEvidence"]["retrievalMode"], "hybrid")
            self.assertTrue(rag_answer["retrievalEvidence"]["rerankUsed"])
            self.assertIsNone(turn.route_decision.classifier_request)
            self.assertEqual(facade.calls[0]["retrieval_mode"], "hybrid")

    def test_low_confidence_rag_retrieval_clarifies_without_generation(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                [
                    _KnowledgeHit(
                        source_type="DOCUMENT_CHUNK",
                        match_type="VECTOR",
                        score=0.42,
                        title="航班延误险条款",
                        content="航班延误超过 4 小时，可提交保险理赔申请。",
                        document_id=7,
                        chunk_id=70,
                        chunk_index=0,
                    )
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                rag_answer_gate=RagAnswerGate(
                    facade,
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "这个保险怎么赔？")

            self.assertEqual(turn.route_decision.action, "CLARIFY")
            self.assertEqual(turn.route_decision.rag_answer["reasonCode"], "RAG_LOW_CONFIDENCE")
            self.assertFalse(turn.route_decision.rag_answer["mutatesSopState"])
            self.assertEqual(turn.route_decision.rag_answer["generationEvidence"]["mode"], "not_run")

    def test_sop_intent_with_low_confidence_rag_starts_sop(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                [
                    _KnowledgeHit(
                        source_type="DOCUMENT_CHUNK",
                        match_type="VECTOR",
                        score=0.016,
                        title="航班延误险条款",
                        content="航班延误超过 4 小时，可提交保险理赔申请。",
                        document_id=7,
                        chunk_id=70,
                        chunk_index=0,
                    )
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                rag_answer_gate=RagAnswerGate(
                    facade,
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "我要退票")

            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "refund_ticket")

    def test_low_raw_hybrid_rank_with_strong_text_overlap_answers(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                [
                    _KnowledgeHit(
                        source_type="DOCUMENT_CHUNK",
                        match_type="VECTOR",
                        score=0.016,
                        title="航班延误险条款",
                        content="航班 延误 超过 4 小时 保险 理赔：旅客可提交延误证明、登机牌、保单和身份证明材料申请赔付。",
                        document_id=7,
                        chunk_id=70,
                        chunk_index=0,
                    )
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                rag_answer_gate=RagAnswerGate(
                    facade,
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "航班延误超过4小时保险怎么赔？")

            self.assertEqual(turn.route_decision.action, "ANSWER_RAG")
            self.assertEqual(turn.route_decision.rag_answer["reasonCode"], "RAG_HIGH_CONFIDENCE")
            self.assertGreaterEqual(turn.route_decision.rag_answer["confidence"], 0.7)
            self.assertEqual(turn.route_decision.rag_answer["citations"][0]["sourceId"], "chunk:70")
            self.assertEqual(
                turn.route_decision.rag_answer["retrievalEvidence"]["topChunks"][0]["score"],
                0.016,
            )

    def test_active_sop_slot_payload_bypasses_low_confidence_rag(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                {
                    "订单TK-100": [
                        _KnowledgeHit(
                            source_type="DOCUMENT_CHUNK",
                            match_type="VECTOR",
                            score=0.016,
                            title="航班延误险条款",
                            content="航班延误超过 4 小时，可提交保险理赔申请。",
                            document_id=7,
                            chunk_id=70,
                            chunk_index=0,
                        )
                    ],
                }
            )
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(
                repository,
                rag_answer_gate=RagAnswerGate(
                    facade,
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
            )
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])
            started = service.handle_message(session_id, "我要退票")

            continued = service.handle_message(session_id, "订单TK-100")

            self.assertEqual(continued.route_decision.action, "CONTINUE_ACTIVE_SOP")
            self.assertEqual(continued.active_task["id"], started.active_task["id"])
            self.assertIn("TASK_CONTINUED", [event["event_type"] for event in continued.events])

    def test_active_sop_rag_question_with_slot_payload_clarifies_without_task_mutation(self) -> None:
        with _session() as session:
            facade = _RecordingKnowledgeFacade(
                {
                    "航班延误保险怎么赔？订单TK-100": [
                        _KnowledgeHit(
                            source_type="DOCUMENT_CHUNK",
                            match_type="VECTOR",
                            score=0.92,
                            title="航班延误险条款",
                            content="航班延误超过 4 小时，可提交保险理赔申请。",
                            document_id=7,
                            chunk_id=70,
                            chunk_index=0,
                        )
                    ],
                }
            )
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(
                repository,
                rag_answer_gate=RagAnswerGate(
                    facade,
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
            )
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            started = service.handle_message(session_id, "我要退票")
            before = dict(started.active_task)
            clarified = service.handle_message(session_id, "航班延误保险怎么赔？订单TK-100")
            after_checkpoint = repository.get_latest_checkpoint(int(before["id"]))

            self.assertEqual(clarified.route_decision.action, "CLARIFY")
            self.assertEqual(clarified.route_decision.rag_answer["reasonCode"], "RAG_ACTIVE_AMBIGUOUS")
            self.assertEqual(clarified.active_task["id"], before["id"])
            self.assertEqual(clarified.active_task["current_step"], before["current_step"])
            self.assertEqual(clarified.active_task["checkpoint_id"], before["checkpoint_id"])
            self.assertEqual(after_checkpoint["id"], before["checkpoint_id"])
            self.assertNotIn("TASK_CONTINUED", [event["event_type"] for event in clarified.events])


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_rag_policy.db"
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
        content: str,
        document_id: int,
        chunk_id: int,
        chunk_index: int,
    ) -> None:
        self.source_type = source_type
        self.match_type = match_type
        self.score = score
        self.title = title
        self.content = content
        self.document_id = document_id
        self.chunk_id = chunk_id
        self.chunk_index = chunk_index


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
