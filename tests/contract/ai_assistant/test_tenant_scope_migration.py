from pathlib import Path

from alembic import command
from alembic.config import Config
import sqlalchemy as sa

from tests.support.mysql import Mysql8TestDatabase


def test_ai_assistant_tenant_scope_migration_upgrades_and_downgrades() -> None:
    with Mysql8TestDatabase("ai_assistant_tenant_scope_migration") as database:
        config = _alembic_config(database.database_url)
        command.upgrade(config, "0035_runtime_job_owner_identity")

        command.upgrade(config, "head")

        inspector = sa.inspect(database.engine)
        for table_name in (
            "ai_assistant_session",
            "ai_assistant_run",
            "ai_assistant_memory_cursor",
            "ai_assistant_memory_completion",
            "ai_assistant_model_usage",
        ):
            assert "tenant_id" in {
                str(column["name"])
                for column in inspector.get_columns(table_name)
            }
        assert _index_columns(
            database.engine,
            "ai_assistant_run",
            "idx_ai_assistant_run_scope",
        ) == ("tenant_id", "user_id", "workspace_id", "session_id", "deleted")

        command.downgrade(config, "0035_runtime_job_owner_identity")

        downgraded = sa.inspect(database.engine)
        assert "tenant_id" not in {
            str(column["name"])
            for column in downgraded.get_columns("ai_assistant_run")
        }
        assert _index_columns(
            database.engine,
            "ai_assistant_run",
            "idx_ai_assistant_run_scope",
        ) == ("user_id", "workspace_id", "session_id", "deleted")


def _alembic_config(database_url: str) -> Config:
    repository_root = Path(__file__).resolve().parents[3]
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("script_location", str(repository_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _index_columns(
    engine: sa.Engine,
    table_name: str,
    index_name: str,
) -> tuple[str, ...]:
    return next(
        tuple(str(column) for column in index["column_names"])
        for index in sa.inspect(engine).get_indexes(table_name)
        if index.get("name") == index_name
    )
