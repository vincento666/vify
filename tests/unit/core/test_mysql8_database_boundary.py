import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
import sqlalchemy as sa

from app.core.config import Settings
from app.core.database import make_engine
from app.core.database_url_policy import assert_mysql8_connection


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MYSQL_URL = "mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4"


class Mysql8DatabaseBoundaryTest(unittest.TestCase):
    def test_settings_default_database_is_mysql8_not_sqlite(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.database_url, DEFAULT_MYSQL_URL)

    def test_settings_rejects_sqlite_database_url(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, database_url="sqlite:///./hify.db")

    def test_engine_factory_rejects_sqlite_database_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "SQLite is not allowed"):
            make_engine("sqlite:///./hify.db")

    def test_connection_validator_rejects_mysql_before_version_8(self) -> None:
        class _Dialect:
            name = "mysql"
            server_version_info = (5, 7, 44)

        class _Bind:
            dialect = _Dialect()

        with self.assertRaisesRegex(ValueError, "MySQL8 is required"):
            assert_mysql8_connection(_Bind())

    def test_connection_validator_rejects_non_mysql_bind(self) -> None:
        engine = sa.create_engine("sqlite:///:memory:", future=True)
        try:
            with self.assertRaisesRegex(ValueError, "SQLite is not allowed"):
                assert_mysql8_connection(engine)
        finally:
            engine.dispose()

    def test_alembic_default_url_is_mysql8(self) -> None:
        content = (PROJECT_ROOT / "alembic.ini").read_text(encoding="utf-8")

        self.assertIn(f"sqlalchemy.url = {DEFAULT_MYSQL_URL}", content)
        self.assertNotIn("sqlalchemy.url = sqlite", content)

    def test_product_demo_evidence_does_not_seed_or_run_against_sqlite(self) -> None:
        checked_paths = [
            PROJECT_ROOT / "docs/evidence/115-mvp-demo-story-browser-uat.md",
            PROJECT_ROOT / "specs/115-mvp-demo-story-browser-uat/plan.md",
        ]

        for path in checked_paths:
            with self.subTest(path=str(path.relative_to(PROJECT_ROOT))):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("sqlite://", content)
                self.assertIn("mysql+pymysql://", content)

    def test_product_demo_uat_artifacts_do_not_retain_sqlite_evidence(self) -> None:
        artifact_root = PROJECT_ROOT / "artifacts/slices/115-mvp-demo-story-browser-uat/115.1"
        if not artifact_root.exists():
            self.skipTest("115 browser UAT artifact directory is not present in this checkout")

        text_suffixes = {".env", ".json", ".md", ".txt"}
        forbidden_markers = ("sqlite://", "SQLite", "sqlite", "hify-uat.db")
        offenders: list[str] = []
        for path in artifact_root.rglob("*"):
            if not path.is_file():
                continue
            relative_path = str(path.relative_to(PROJECT_ROOT))
            if path.suffix in {".db", ".sqlite", ".sqlite3"}:
                offenders.append(relative_path)
                continue
            if path.suffix not in text_suffixes and path.name != ".env.demo":
                continue
            content = path.read_text(encoding="utf-8")
            if any(marker in content for marker in forbidden_markers):
                offenders.append(relative_path)

        self.assertEqual([], offenders)

    def test_product_live_and_demo_specs_do_not_prescribe_sqlite_runtime(self) -> None:
        checked_paths = [
            PROJECT_ROOT / "specs/129-mysql8-one-click-demo-seed-gate/spec.md",
            PROJECT_ROOT / "specs/135-openrouter-deepseek-v4-flash-live-gate/plan.md",
            PROJECT_ROOT / "specs/136-runtime-v2-openrouter-live-acceptance/spec.md",
        ]
        forbidden_markers = (
            "disposable SQLite",
            "SQLite database",
            "SQLite seed",
            "SQLite seed tests",
            "sqlite://",
            "hify.db",
        )

        offenders: list[str] = []
        for path in checked_paths:
            content = path.read_text(encoding="utf-8")
            if any(marker in content for marker in forbidden_markers):
                offenders.append(str(path.relative_to(PROJECT_ROOT)))

        self.assertEqual([], offenders)

    def test_application_code_and_scripts_do_not_create_sqlite_database_urls(self) -> None:
        checked_roots = [PROJECT_ROOT / "app", PROJECT_ROOT / "scripts"]

        offenders: list[str] = []
        for root in checked_roots:
            for path in root.rglob("*.py"):
                content = path.read_text(encoding="utf-8")
                if "sqlite://" in content:
                    offenders.append(str(path.relative_to(PROJECT_ROOT)))

        self.assertEqual([], offenders)

    def test_runtime_adjacent_tests_do_not_use_sqlite_databases(self) -> None:
        checked_roots = [
            PROJECT_ROOT / "tests" / "integration",
            PROJECT_ROOT / "tests" / "contract",
            PROJECT_ROOT / "tests" / "e2e",
            PROJECT_ROOT / "tests" / "acceptance",
        ]
        forbidden_markers = ("sqlite://", "sqlite:///", "sqlite3", "aiosqlite")

        offenders: list[str] = []
        for root in checked_roots:
            for path in root.rglob("*.py"):
                content = path.read_text(encoding="utf-8")
                if any(marker in content for marker in forbidden_markers):
                    offenders.append(str(path.relative_to(PROJECT_ROOT)))

        self.assertEqual([], offenders)

    def test_mysql8_test_harness_requires_disposable_databases(self) -> None:
        content = (PROJECT_ROOT / "tests/support/mysql.py").read_text(encoding="utf-8")

        self.assertIn("HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL", content)
        self.assertIn("Refusing shared-schema fallback", content)
        self.assertNotIn("_drop_all_tables", content)
        self.assertNotIn("DROP TABLE IF EXISTS", content)


if __name__ == "__main__":
    unittest.main()
