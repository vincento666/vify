from logging.config import fileConfig
import os
from pathlib import Path
import sys

from alembic import context
import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.core.database_url_policy import assert_mysql8_connection, assert_mysql8_database_url
from app.core.schema import register_baseline_tables

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

configured_database_url = config.get_main_option("sqlalchemy.url")
if database_url := os.getenv("HIFY_DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", database_url)
assert_mysql8_database_url(config.get_main_option("sqlalchemy.url"))

register_baseline_tables()
target_metadata = Base.metadata


def _ensure_mysql_version_table(connection: object) -> None:
    if connection.dialect.name != "mysql":  # type: ignore[attr-defined]
        return
    inspector = sa.inspect(connection)
    if "alembic_version" not in inspector.get_table_names():
        connection.execute(  # type: ignore[attr-defined]
            sa.text(
                "CREATE TABLE alembic_version ("
                "version_num VARCHAR(255) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                ")"
            )
        )
        return
    columns = {column["name"]: column for column in inspector.get_columns("alembic_version")}
    version_column = columns.get("version_num")
    column_type = version_column["type"] if version_column else None
    if getattr(column_type, "length", 0) < 255:
        connection.execute(sa.text("ALTER TABLE alembic_version MODIFY version_num VARCHAR(255) NOT NULL"))  # type: ignore[attr-defined]


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        assert_mysql8_connection(connection)
        _ensure_mysql_version_table(connection)
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
        if connection.in_transaction():
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
