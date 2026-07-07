from unittest.mock import patch

from app.core.config import Settings
from app.core.database import DatabasePoolConfig, make_engine


MYSQL8_URL = "mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4"


def test_settings_exposes_database_pool_config_schema() -> None:
    settings = Settings(
        _env_file=None,
        database_pool_size=12,
        database_max_overflow=7,
        database_pool_timeout_seconds=9.5,
        database_pool_recycle_seconds=1800,
        database_pool_pre_ping=False,
    )

    config = DatabasePoolConfig.from_settings(settings)

    assert config.sqlalchemy_kwargs() == {
        "pool_size": 12,
        "max_overflow": 7,
        "pool_timeout": 9.5,
        "pool_recycle": 1800,
        "pool_pre_ping": False,
    }


def test_make_engine_applies_pool_config_to_sqlalchemy_create_engine() -> None:
    engine = object()
    pool_config = DatabasePoolConfig(
        pool_size=16,
        max_overflow=4,
        pool_timeout=6.0,
        pool_recycle=1200,
        pool_pre_ping=True,
    )

    with (
        patch("app.core.database.create_engine", return_value=engine) as create_engine,
        patch("app.core.database.assert_mysql8_connection") as assert_connection,
    ):
        result = make_engine(MYSQL8_URL, pool_config=pool_config)

    assert result is engine
    create_engine.assert_called_once_with(
        MYSQL8_URL,
        echo=False,
        future=True,
        pool_size=16,
        max_overflow=4,
        pool_timeout=6.0,
        pool_recycle=1200,
        pool_pre_ping=True,
    )
    assert_connection.assert_called_once_with(engine)
