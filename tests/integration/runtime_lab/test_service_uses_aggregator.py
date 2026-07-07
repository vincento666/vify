"""RuntimeLabService wires business context through the aggregator."""

import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.modules.runtime_lab.domain.aggregator import (
    RuntimeLabBusinessContextAggregator,
)
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class ServiceUsesAggregatorTest(unittest.TestCase):
    def test_service_initializes_business_context_aggregator(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))

            self.assertIsInstance(
                service._aggregator,  # noqa: SLF001
                RuntimeLabBusinessContextAggregator,
            )

    def test_legacy_session_business_context_delegate_is_removed(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            stub = MagicMock(spec=RuntimeLabBusinessContextAggregator)
            stub.collect.return_value = {"order_no": "AGG-1"}
            service._aggregator = stub  # type: ignore[assignment]  # noqa: SLF001

            self.assertFalse(hasattr(service, "_session_business_context"))
            self.assertEqual(service._aggregator.collect(42), {"order_no": "AGG-1"})  # noqa: SLF001

    def test_service_accepts_injected_aggregator(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            injected = RuntimeLabBusinessContextAggregator(repository, None)
            service = RuntimeLabService(repository, aggregator=injected)

            self.assertIs(service._aggregator, injected)  # noqa: SLF001


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session(
        "runtime_lab_service_uses_aggregator", register=register_runtime_lab_tables
    ) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
