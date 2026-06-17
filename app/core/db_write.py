from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.schema import Column, Table


def insert_and_fetch(
    session: Session,
    table: Table,
    values: dict[str, Any],
    *,
    key_column: Column[Any] | None = None,
) -> dict[str, Any]:
    key = key_column if key_column is not None else _single_primary_key(table)
    result = session.execute(table.insert().values(**values))
    key_value = values.get(key.name)
    if key_value is None and isinstance(result, CursorResult):
        primary_key = result.inserted_primary_key
        if primary_key:
            key_value = primary_key[0]
    if key_value is None:
        raise RuntimeError(f"Could not resolve inserted primary key for {table.name}")
    return fetch_by_key(session, table, key_value, key_column=key)


def insert_and_get_id(
    session: Session,
    table: Table,
    values: dict[str, Any],
    *,
    key_column: Column[Any] | None = None,
) -> int:
    key = key_column if key_column is not None else _single_primary_key(table)
    result = session.execute(table.insert().values(**values))
    key_value = values.get(key.name)
    if key_value is None and isinstance(result, CursorResult):
        primary_key = result.inserted_primary_key
        if primary_key:
            key_value = primary_key[0]
    if key_value is None:
        raise RuntimeError(f"Could not resolve inserted primary key for {table.name}")
    return int(key_value)


def update_and_fetch(
    session: Session,
    table: Table,
    where: ColumnElement[bool] | Sequence[ColumnElement[bool]],
    values: dict[str, Any],
    *,
    key_column: Column[Any] | None = None,
    key_value: Any | None = None,
) -> dict[str, Any] | None:
    key = key_column if key_column is not None else _single_primary_key(table)
    conditions = _conditions(where)
    if key_value is None:
        key_value = session.execute(sa.select(key).where(*conditions)).scalar_one_or_none()
    if key_value is None:
        return None
    result = session.execute(table.update().where(*conditions).values(**values))
    if isinstance(result, CursorResult) and result.rowcount <= 0:
        return None
    return fetch_by_key(session, table, key_value, key_column=key)


def fetch_by_key(
    session: Session,
    table: Table,
    key_value: Any,
    *,
    key_column: Column[Any] | None = None,
) -> dict[str, Any]:
    key = key_column if key_column is not None else _single_primary_key(table)
    row = session.execute(sa.select(table).where(key == key_value)).mappings().one()
    return dict(row)


def _single_primary_key(table: Table) -> Column[Any]:
    primary_keys = list(table.primary_key.columns)
    if len(primary_keys) != 1:
        raise ValueError(f"{table.name} must have exactly one primary key")
    return primary_keys[0]


def _conditions(
    where: ColumnElement[bool] | Sequence[ColumnElement[bool]],
) -> list[ColumnElement[bool]]:
    if isinstance(where, Sequence) and not isinstance(where, ColumnElement):
        return list(where)
    return [where]
