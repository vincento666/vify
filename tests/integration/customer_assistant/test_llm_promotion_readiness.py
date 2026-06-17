from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
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


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("promotion_readiness", register=register_baseline_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
