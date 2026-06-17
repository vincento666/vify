from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
import os
import re
import time
from typing import Any
import uuid

import sqlalchemy as sa
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, initialise_database, make_session_factory
from app.core.database_url_policy import assert_mysql8_database_url
from app.core.schema import register_baseline_tables, tables_for_bind


def mysql8_test_base_url() -> str:
    database_url = os.getenv("HIFY_MYSQL8_TEST_DATABASE_URL") or os.getenv("HIFY_DATABASE_URL") or get_settings().database_url
    assert_mysql8_database_url(database_url, setting_name="HIFY_MYSQL8_TEST_DATABASE_URL")
    return database_url


class Mysql8TestDatabase:
    def __init__(self, prefix: str = "hify_test") -> None:
        base_url = make_url(mysql8_test_base_url())
        admin_database_url = os.getenv("HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL")
        if admin_database_url:
            assert_mysql8_database_url(admin_database_url, setting_name="HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL")
            if not base_url.username:
                raise RuntimeError("HIFY_MYSQL8_TEST_DATABASE_URL must include a username when test admin URL is set")
        self._app_url = base_url
        self._admin_url = make_url(admin_database_url) if admin_database_url else base_url
        self._uses_admin_url = admin_database_url is not None
        self.database_name = _database_name(prefix)
        self.database_url = _url_text(base_url.set(database=self.database_name))
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None

    def __enter__(self) -> Mysql8TestDatabase:
        try:
            with _admin_engine(self._admin_url).begin() as connection:
                connection.execute(
                    sa.text(
                        f"CREATE DATABASE `{_quote_name(self.database_name)}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
                if self._uses_admin_url:
                    connection.execute(
                        sa.text(
                            f"GRANT ALL PRIVILEGES ON `{_quote_name(self.database_name)}`.* "
                            f"TO {_quote_literal(str(self._app_url.username or ''))}@"
                            f"{_quote_literal(os.getenv('HIFY_MYSQL8_TEST_GRANT_HOST', '%'))}"
                        )
                    )
        except SQLAlchemyError as exc:
            raise RuntimeError(
                "MySQL8 tests require disposable database creation. Grant CREATE/DROP DATABASE "
                "to HIFY_MYSQL8_TEST_DATABASE_URL, or set HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL "
                "for test-only database create/drop. Refusing shared-schema fallback."
            ) from exc
        self.engine = sa.create_engine(self.database_url, future=True)
        self.session_factory = make_session_factory(self.engine)
        return self

    def __exit__(self, *_exc: object) -> None:
        if self.engine is not None:
            self.engine.dispose()
        with _admin_engine(self._admin_url).begin() as connection:
            connection.execute(sa.text(f"DROP DATABASE IF EXISTS `{_quote_name(self.database_name)}`"))

    def create_all(
        self,
        *,
        tables: Iterable[sa.Table] | None = None,
        register: Callable[[], object] | None = None,
    ) -> None:
        if self.engine is None:
            raise RuntimeError("Mysql8TestDatabase must be entered before create_all")
        if register is not None:
            register()
        else:
            register_baseline_tables()
        selected_tables = list(tables) if tables is not None else tables_for_bind(self.engine)
        Base.metadata.create_all(bind=self.engine, tables=selected_tables)

    def session(self) -> Session:
        if self.session_factory is None:
            raise RuntimeError("Mysql8TestDatabase must be entered before opening a session")
        return self.session_factory()


def mysql8_unittest_database(
    testcase: Any,
    prefix: str = "hify_test",
    *,
    tables: Iterable[sa.Table] | None = None,
    register: Callable[[], object] | None = None,
) -> Mysql8TestDatabase:
    database = Mysql8TestDatabase(prefix)
    database.__enter__()
    database_url_override = _DatabaseUrlOverride(database.database_url)
    database_url_override.__enter__()
    try:
        database.create_all(tables=tables, register=register)
    except Exception:
        database_url_override.__exit__(None, None, None)
        database.__exit__(None, None, None)
        raise
    if not hasattr(testcase, "_tmp_dir"):
        setattr(testcase, "_tmp_dir", _NoopCleanup())

    def cleanup() -> None:
        database_url_override.__exit__(None, None, None)
        database.__exit__(None, None, None)

    testcase.addCleanup(cleanup)
    return database


class _NoopCleanup:
    def cleanup(self) -> None:
        return


class _DatabaseUrlOverride:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._previous_url: str | None = None

    def __enter__(self) -> None:
        self._previous_url = os.environ.get("HIFY_DATABASE_URL")
        os.environ["HIFY_DATABASE_URL"] = self._database_url
        get_settings.cache_clear()

    def __exit__(self, *_exc: object) -> None:
        if self._previous_url is None:
            os.environ.pop("HIFY_DATABASE_URL", None)
        else:
            os.environ["HIFY_DATABASE_URL"] = self._previous_url
        get_settings.cache_clear()


@contextmanager
def mysql8_session(
    prefix: str = "hify_test",
    *,
    tables: Iterable[sa.Table] | None = None,
    register: Callable[[], object] | None = None,
) -> Iterator[Session]:
    with Mysql8TestDatabase(prefix) as database:
        database.create_all(tables=tables, register=register)
        with database.session() as session:
            yield session


class mysql8_app_database:
    def __init__(self, prefix: str = "hify_app_test") -> None:
        self._database = Mysql8TestDatabase(prefix)
        self._previous_url: str | None = None

    def __enter__(self) -> None:
        self._database.__enter__()
        self._previous_url = os.environ.get("HIFY_DATABASE_URL")
        os.environ["HIFY_DATABASE_URL"] = self._database.database_url
        get_settings.cache_clear()
        initialise_database()

    def __exit__(self, *_exc: object) -> None:
        if self._previous_url is None:
            os.environ.pop("HIFY_DATABASE_URL", None)
        else:
            os.environ["HIFY_DATABASE_URL"] = self._previous_url
        get_settings.cache_clear()
        self._database.__exit__(*_exc)


@contextmanager
def mysql8_database_url(prefix: str = "hify_test") -> Iterator[str]:
    with Mysql8TestDatabase(prefix) as database:
        yield database.database_url


@contextmanager
def configured_mysql8_database_url(database_url: str) -> Iterator[None]:
    assert_mysql8_database_url(database_url)
    previous_url = os.environ.get("HIFY_DATABASE_URL")
    os.environ["HIFY_DATABASE_URL"] = database_url
    get_settings.cache_clear()
    try:
        yield
    finally:
        if previous_url is None:
            os.environ.pop("HIFY_DATABASE_URL", None)
        else:
            os.environ["HIFY_DATABASE_URL"] = previous_url
        get_settings.cache_clear()


def _admin_engine(url: URL) -> Engine:
    return sa.create_engine(_url_text(url), future=True)


def _database_name(prefix: str) -> str:
    clean_prefix = re.sub(r"[^a-zA-Z0-9_]+", "_", prefix).strip("_").lower() or "hify_test"
    suffix = f"{os.getpid()}_{time.time_ns()}_{uuid.uuid4().hex[:8]}"
    return f"{clean_prefix}_{suffix}"[:63]


def _quote_name(name: str) -> str:
    return name.replace("`", "``")


def _quote_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def _url_text(url: URL) -> str:
    return url.render_as_string(hide_password=False)
