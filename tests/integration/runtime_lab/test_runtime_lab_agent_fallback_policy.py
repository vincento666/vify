import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.domain.agent_fallback import (
    AgentOutputPolicy,
    FallbackAgentOutput,
    FallbackAgentRequest,
)
from app.modules.runtime_lab.domain.rag_gate import FakeRagAnswerGenerator, RagAnswerGate
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabAgentFallbackPolicyTest(unittest.TestCase):
    def test_unresolved_query_reaches_agent_fallback_without_task_mutation(self) -> None:
        with _session() as session:
            agent = _ScriptedFallbackAgent(
                [
                    FallbackAgentOutput(
                        response_type="answer",
                        answer="我先帮您整理机场交通诉求，建议再核对机场官方班次。",
                        confidence=0.74,
                    )
                ]
            )
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(
                repository,
                fallback_agent=agent,
                agent_output_policy=AgentOutputPolicy(),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "机场大巴末班车几点")

            self.assertEqual(turn.route_decision.action, "AGENT_FALLBACK")
            self.assertIn("机场交通", turn.reply)
            self.assertEqual(turn.route_decision.agent_answer["sourceLayer"], "agent_policy")
            self.assertEqual(turn.route_decision.agent_answer["reasonCode"], "AGENT_ANSWER")
            self.assertFalse(turn.route_decision.agent_answer["mutatesSopState"])
            self.assertIsNone(turn.active_task)
            self.assertEqual(turn.suspended_tasks, [])
            self.assertNotIn("TASK_STARTED", [event["event_type"] for event in turn.events])

    def test_low_confidence_rag_defers_to_agent_fallback_when_available(self) -> None:
        with _session() as session:
            agent = _ScriptedFallbackAgent(
                [
                    FallbackAgentOutput(
                        response_type="answer",
                        answer="我先按通用咨询处理，建议再核对机场官方公告。",
                        confidence=0.68,
                    )
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                rag_answer_gate=RagAnswerGate(
                    _LowConfidenceKnowledgeFacade(),
                    knowledge_base_ids=[33],
                    generator=FakeRagAnswerGenerator(),
                    rerank=True,
                ),
                fallback_agent=agent,
                agent_output_policy=AgentOutputPolicy(),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "机场大巴末班车几点")

            self.assertEqual(turn.route_decision.action, "AGENT_FALLBACK")
            self.assertEqual(turn.route_decision.agent_answer["sourceLayer"], "agent_policy")
            self.assertEqual(turn.route_decision.agent_answer["reasonCode"], "AGENT_ANSWER")
            self.assertFalse(turn.route_decision.agent_answer["mutatesSopState"])
            self.assertEqual(len(agent.requests), 1)
            self.assertIn("RAG_LOW_CONFIDENCE", str(turn.route_decision.policy_gate))

    def test_agent_side_effect_proposal_is_rejected_without_task_mutation(self) -> None:
        with _session() as session:
            agent = _ScriptedFallbackAgent(
                [
                    FallbackAgentOutput(
                        response_type="answer",
                        answer="我直接帮您启动退票。",
                        confidence=0.8,
                        proposed_actions=["START_SOP"],
                    )
                ]
            )
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(
                repository,
                fallback_agent=agent,
                agent_output_policy=AgentOutputPolicy(),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "机场巴士末班车怎么查")

            self.assertEqual(turn.route_decision.action, "CLARIFY")
            self.assertEqual(turn.route_decision.agent_answer["reasonCode"], "AGENT_UNSUPPORTED_SIDE_EFFECT")
            self.assertIsNone(turn.active_task)
            self.assertEqual(repository.list_tasks(int(runtime_session["id"])), [])

    def test_agent_handoff_recommendation_goes_through_handoff_control_plane(self) -> None:
        with _session() as session:
            agent = _ScriptedFallbackAgent(
                [
                    FallbackAgentOutput(
                        response_type="handoff_recommendation",
                        answer="建议转人工处理。",
                        handoff_reason="Agent judged request requires human service",
                        confidence=0.88,
                    )
                ]
            )
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                fallback_agent=agent,
                agent_output_policy=AgentOutputPolicy(),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "航司系统赔付争议材料很多需要进一步判断")

            self.assertEqual(turn.route_decision.action, "HANDOFF_TO_HUMAN")
            self.assertEqual(turn.route_decision.handoff["sourceLayer"], "agent_policy")
            self.assertEqual(turn.route_decision.handoff["reasonCode"], "AGENT_RECOMMENDED_HANDOFF")
            self.assertIn("HANDOFF_DECIDED", [event["event_type"] for event in turn.events])
            self.assertIn("HANDOFF_REQUESTED", [event["event_type"] for event in turn.events])

    def test_repeated_agent_clarification_escalates_to_handoff_preserving_active_task(self) -> None:
        with _session() as session:
            agent = _ScriptedFallbackAgent(
                [
                    FallbackAgentOutput(
                        response_type="clarification",
                        clarification_question="请补充您遇到的具体问题。",
                        confidence=0.51,
                    ),
                    FallbackAgentOutput(
                        response_type="clarification",
                        clarification_question="请再说明需要查询还是办理。",
                        confidence=0.51,
                    ),
                    FallbackAgentOutput(
                        response_type="clarification",
                        clarification_question="仍无法确认诉求。",
                        confidence=0.51,
                    ),
                ]
            )
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(
                repository,
                fallback_agent=agent,
                agent_output_policy=AgentOutputPolicy(max_clarification_attempts=2),
            )
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])
            started = service.handle_message(session_id, "我要退票")

            first = service.handle_message(session_id, "外星权益")
            second = service.handle_message(session_id, "还是那个")
            third = service.handle_message(session_id, "不知道")

            self.assertEqual(first.route_decision.action, "CLARIFY")
            self.assertEqual(second.route_decision.action, "CLARIFY")
            self.assertEqual(third.route_decision.action, "HANDOFF_TO_HUMAN")
            self.assertEqual(third.route_decision.handoff["reasonCode"], "CLARIFICATION_FAILED")
            self.assertEqual(third.active_task["id"], started.active_task["id"])
            self.assertEqual(third.active_task["current_step"], started.active_task["current_step"])
            self.assertEqual(third.active_task["checkpoint_id"], started.active_task["checkpoint_id"])
            self.assertEqual(
                [event["event_type"] for event in third.events].count("AGENT_CLARIFICATION_ASKED"),
                2,
            )


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_agent_fallback_policy.db"
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


class _ScriptedFallbackAgent:
    def __init__(self, outputs: list[FallbackAgentOutput]) -> None:
        self._outputs = list(outputs)
        self.requests: list[FallbackAgentRequest] = []

    def run(self, request: FallbackAgentRequest) -> FallbackAgentOutput:
        self.requests.append(request)
        if self._outputs:
            return self._outputs.pop(0)
        return FallbackAgentOutput(
            response_type="answer",
            answer=f"已收到：{request.message}",
            confidence=0.6,
        )


class _LowConfidenceKnowledgeFacade:
    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list["_KnowledgeHit"]:
        del knowledge_base_id, query, top_k, retrieval_mode, score_threshold, rerank
        return [
            _KnowledgeHit(
                source_type="DOCUMENT_CHUNK",
                match_type="VECTOR",
                score=0.02,
                title="航班延误险条款",
                content="航班延误超过 4 小时，可提交保险理赔申请。",
                document_id=7,
                chunk_id=70,
                chunk_index=0,
            )
        ]


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
