import os
import time
import unittest

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.schema import register_baseline_tables
from app.modules.provider.infra.repository import ProviderRepository


MYSQL8_TEST_DATABASE_URL = os.getenv("HIFY_MYSQL8_TEST_DATABASE_URL")


@unittest.skipUnless(MYSQL8_TEST_DATABASE_URL, "set HIFY_MYSQL8_TEST_DATABASE_URL for MySQL8 integration")
class Mysql8RepositoryWriteCompatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        register_baseline_tables()
        cls.engine = sa.create_engine(MYSQL8_TEST_DATABASE_URL, future=True)
        cls.Session = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        tables = [
            Base.metadata.tables["provider"],
            Base.metadata.tables["model_config"],
            Base.metadata.tables["provider_health"],
        ]
        Base.metadata.create_all(bind=cls.engine, tables=tables)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_provider_create_returns_row_and_makes_it_retrievable(self) -> None:
        provider_name = f"mysql8-provider-{time.time_ns()}"

        with self.Session() as session:
            repository = ProviderRepository(session)
            created = repository.create(
                {
                    "name": provider_name,
                    "type": "OPENAI",
                    "base_url": "https://api.example.com/v1",
                    "auth_config": {"api_key": "sk-test"},
                    "description": "mysql8 write compat",
                }
            )
            fetched = repository.get(int(created["id"]))

        self.assertEqual(provider_name, created["name"])
        self.assertIsNotNone(fetched)
        self.assertEqual(provider_name, fetched["name"])
        self.assertTrue(fetched["enabled"])


if __name__ == "__main__":
    unittest.main()
