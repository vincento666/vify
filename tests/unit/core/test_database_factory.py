from types import SimpleNamespace
from unittest.mock import patch

from app.core import database


MYSQL8_URL = "mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4"


def test_get_engine_reuses_global_engine_for_same_settings() -> None:
    first_engine = object()
    second_engine = object()

    database.reset_engine_cache()
    try:
        with (
            patch.object(database, "get_settings", return_value=SimpleNamespace(database_url=MYSQL8_URL)),
            patch.object(database, "make_engine", side_effect=[first_engine, second_engine]) as make_engine,
        ):
            assert database.get_engine() is first_engine
            assert database.get_engine() is first_engine

        assert make_engine.call_count == 1
    finally:
        database.reset_engine_cache(dispose=False)


def test_get_session_factory_reuses_factory_for_global_engine() -> None:
    engine = object()
    first_factory = object()
    second_factory = object()

    database.reset_engine_cache()
    try:
        with (
            patch.object(database, "get_engine", return_value=engine) as get_engine,
            patch.object(database, "make_session_factory", side_effect=[first_factory, second_factory]) as make_factory,
        ):
            assert database.get_session_factory() is first_factory
            assert database.get_session_factory() is first_factory

        assert get_engine.call_count == 2
        assert make_factory.call_count == 1
    finally:
        database.reset_engine_cache(dispose=False)
