import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.schema import register_baseline_tables
from app.modules.customer_assistant.eval.chatflow_readiness import (
    check_chatflow_data_readiness,
)


class CustomerAssistantPromotionReadinessTest(unittest.TestCase):
    def test_missing_chatflow_binding_is_readiness_failure_unless_mock_fallback_is_explicit(self) -> None:
        with _session() as session:
            missing = check_chatflow_data_readiness(
                session,
                required_sop_chatflow_ids={"refund_ticket": 404},
                allow_fallback_mock=False,
            )
            fallback = check_chatflow_data_readiness(
                session,
                required_sop_chatflow_ids={"refund_ticket": 404},
                allow_fallback_mock=True,
            )

        self.assertEqual(missing.status, "missing_seed_data")
        self.assertEqual(missing.missing_sop_keys, ["refund_ticket"])
        self.assertEqual(missing.missing_chatflow_ids, [404])
        self.assertEqual(fallback.status, "mock_fallback")
        self.assertEqual(fallback.strategy, "explicit_fallback_mock")


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "promotion_readiness.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_baseline_tables()
    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["workflow"]])
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


if __name__ == "__main__":
    unittest.main()
