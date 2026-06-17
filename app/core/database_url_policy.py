from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine, make_url


DEFAULT_MYSQL8_DATABASE_URL = "mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4"


def backend_name(database_url: str) -> str:
    return make_url(database_url).get_backend_name().lower()


def assert_mysql8_database_url(database_url: str, *, setting_name: str = "HIFY_DATABASE_URL") -> None:
    backend = backend_name(database_url)
    if backend == "mysql":
        return
    if backend == "sqlite":
        raise ValueError(
            f"SQLite is not allowed for {setting_name}; use a MySQL8 URL such as {DEFAULT_MYSQL8_DATABASE_URL}."
        )
    raise ValueError(
        f"MySQL8 is required for {setting_name}; got backend {backend!r}. "
        f"Use a URL such as {DEFAULT_MYSQL8_DATABASE_URL}."
    )


def assert_mysql8_connection(bind: Any, *, setting_name: str = "HIFY_DATABASE_URL") -> None:
    dialect = getattr(bind, "dialect", None)
    backend = str(getattr(dialect, "name", "") or "").lower()
    if backend == "sqlite":
        raise ValueError(
            f"SQLite is not allowed for {setting_name}; use a MySQL8 database."
        )
    if backend != "mysql":
        raise ValueError(f"MySQL8 is required for {setting_name}; got backend {backend!r}.")

    version_text = _server_version_text(bind)
    if "mariadb" in version_text.lower():
        raise ValueError(f"MySQL8 is required for {setting_name}; got MariaDB server {version_text!r}.")

    version_info = _version_info(getattr(dialect, "server_version_info", None)) or _version_info(version_text)
    if not version_info:
        raise ValueError(f"MySQL8 is required for {setting_name}; could not determine server version.")
    if version_info[0] < 8:
        version_label = version_text or ".".join(str(part) for part in version_info)
        raise ValueError(f"MySQL8 is required for {setting_name}; got MySQL server {version_label}.")


def _server_version_text(bind: Any) -> str:
    statement = sa.text("SELECT VERSION()")
    if isinstance(bind, Engine):
        with bind.connect() as connection:
            return str(connection.execute(statement).scalar_one_or_none() or "")
    if isinstance(bind, Connection):
        return str(bind.execute(statement).scalar_one_or_none() or "")
    return ""


def _version_info(value: object) -> tuple[int, ...]:
    if isinstance(value, tuple):
        return tuple(int(part) for part in value if isinstance(part, int))
    if not isinstance(value, str):
        return ()
    parts: list[int] = []
    for raw_part in value.split(".", 3)[:3]:
        digits = "".join(character for character in raw_part if character.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)
