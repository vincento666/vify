from pathlib import Path

from alembic import command
from alembic.config import Config
import sqlalchemy as sa

from tests.support.mysql import Mysql8TestDatabase


def test_runtime_job_owner_identity_migration_upgrades_and_downgrades() -> None:
    with Mysql8TestDatabase("runtime_job_owner_identity_migration") as database:
        assert database.engine is not None
        metadata = sa.MetaData()
        sa.Table(
            "runtime_jobs",
            metadata,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("owner_type", sa.String(20), nullable=False),
            sa.Column("run_id", sa.BigInteger(), nullable=False),
            sa.Column("job_type", sa.String(60), nullable=False),
            sa.UniqueConstraint("run_id", "job_type", name="idx_runtime_jobs_run_type"),
        ).create(database.engine)
        config = _alembic_config(database.database_url)
        command.stamp(config, "0034_ai_assistant_model_usage")

        command.upgrade(config, "head")

        upgraded = _unique_constraints(database.engine)
        assert upgraded["idx_runtime_jobs_owner_run_type"] == (
            "owner_type",
            "run_id",
            "job_type",
        )
        assert "idx_runtime_jobs_run_type" not in upgraded

        command.downgrade(config, "0034_ai_assistant_model_usage")

        downgraded = _unique_constraints(database.engine)
        assert downgraded["idx_runtime_jobs_run_type"] == ("run_id", "job_type")
        assert "idx_runtime_jobs_owner_run_type" not in downgraded


def test_runtime_job_owner_identity_is_alembic_clean_at_head() -> None:
    with Mysql8TestDatabase("runtime_job_owner_identity_head") as database:
        config = _alembic_config(database.database_url)

        command.upgrade(config, "head")

        command.check(config)


def _alembic_config(database_url: str) -> Config:
    repository_root = Path(__file__).resolve().parents[3]
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("script_location", str(repository_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _unique_constraints(engine: sa.Engine) -> dict[str, tuple[str, ...]]:
    return {
        str(item["name"]): tuple(item["column_names"])
        for item in sa.inspect(engine).get_unique_constraints("runtime_jobs")
        if item.get("name")
    }
