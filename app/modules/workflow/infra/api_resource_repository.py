from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables

register_baseline_tables()


class ApiResourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._api_resource = Base.metadata.tables["api_resource"]
        self._api_tool = Base.metadata.tables["api_tool"]

    def list_resources(
        self,
        page: int,
        page_size: int,
        enabled: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._api_resource.c.deleted.is_(False)]
        if enabled is not None:
            conditions.append(self._api_resource.c.enabled.is_(enabled))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._api_resource).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._api_resource)
            .where(*conditions)
            .order_by(self._api_resource.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create_resource(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._api_resource,
            {**values, "deleted": False, "created_at": now, "updated_at": now},
        )
        self._session.commit()
        return row

    def get_resource(self, resource_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._api_resource).where(
                self._api_resource.c.id == resource_id,
                self._api_resource.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_resource(self, resource_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        if not values:
            return self.get_resource(resource_id)
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._api_resource.update()
            .where(self._api_resource.c.id == resource_id, self._api_resource.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get_resource(resource_id)

    def delete_resource(self, resource_id: int) -> bool:
        result = self._session.execute(
            self._api_resource.update()
            .where(self._api_resource.c.id == resource_id, self._api_resource.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def list_tools(
        self,
        page: int,
        page_size: int,
        adapter_type: str | None = None,
        model_callable: bool | None = None,
        enabled: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._api_tool.c.deleted.is_(False)]
        if adapter_type:
            conditions.append(self._api_tool.c.adapter_type == adapter_type)
        if model_callable is not None:
            conditions.append(self._api_tool.c.model_callable.is_(model_callable))
        if enabled is not None:
            conditions.append(self._api_tool.c.enabled.is_(enabled))
        total = self._session.execute(sa.select(sa.func.count()).select_from(self._api_tool).where(*conditions)).scalar_one()
        rows = self._session.execute(
            sa.select(self._api_tool)
            .where(*conditions)
            .order_by(self._api_tool.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create_tool(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._api_tool,
            {**values, "deleted": False, "created_at": now, "updated_at": now},
        )
        self._session.commit()
        return row

    def get_tool(self, tool_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._api_tool).where(
                self._api_tool.c.id == tool_id,
                self._api_tool.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def find_tool(self, name: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._api_tool)
            .where(
                self._api_tool.c.name == name,
                self._api_tool.c.deleted.is_(False),
            )
            .order_by(self._api_tool.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None
