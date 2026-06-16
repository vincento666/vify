import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.demo.mvp_seed import seed_mvp_demo


class CustomerAssistantOperatorAdvisoryKnowledgeTest(unittest.TestCase):
    def test_seeded_operator_advice_uses_knowledge_context(self) -> None:
        with _seeded_session() as session:
            seed = seed_mvp_demo(session)
            service = CustomerAssistantService(CustomerAssistantRepository(session))
            session_id = seed.customer_session_ids[0]

            result = service.handle_turn(
                session_id,
                "退票和行李额可以并行处理吗？",
                idempotency_key="operator-knowledge-refund-baggage",
                actor="operator",
            )
            events = service.list_events(session_id)["list"]

        self.assertIn("可以并行处理", result["operatorRecommendation"])
        self.assertIn("退票和行李额", result["operatorRecommendation"])
        self.assertIn("执行写操作前分别确认", result["operatorRecommendation"])
        self.assertFalse(any("Knowledge snippets unavailable" in warning for warning in result["warnings"]))
        packed = next(event for event in events if event["type"] == "operator_advisory_context_packed")
        self.assertGreaterEqual(packed["payload"]["knowledgeSnippetCount"], 1)


def _seeded_session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "customer_assistant_operator_advisory_knowledge.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session
