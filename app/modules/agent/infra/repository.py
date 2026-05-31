from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.schema import register_baseline_tables

register_baseline_tables()


class AgentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._agent = Base.metadata.tables["agent"]
        self._agent_tool = Base.metadata.tables["agent_tool"]
        self._mcp_server = Base.metadata.tables["mcp_server"]

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        payload = {
            **values,
            "enabled": True,
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }
        result = self._session.execute(self._agent.insert().values(**payload).returning(self._agent))
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get(self, agent_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._agent).where(
                self._agent.c.id == agent_id,
                self._agent.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_page(
        self,
        page: int,
        page_size: int,
        enabled: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._agent.c.deleted.is_(False)]
        if enabled is not None:
            conditions.append(self._agent.c.enabled.is_(enabled))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._agent).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._agent)
            .where(*conditions)
            .order_by(self._agent.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def update(self, agent_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._agent.update()
            .where(self._agent.c.id == agent_id, self._agent.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get(agent_id)

    def delete(self, agent_id: int) -> bool:
        result = self._session.execute(
            self._agent.update()
            .where(self._agent.c.id == agent_id, self._agent.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def list_tool_ids(self, agent_id: int) -> list[int]:
        rows = self._session.execute(
            sa.select(self._agent_tool.c.mcp_server_id)
            .where(self._agent_tool.c.agent_id == agent_id)
            .order_by(self._agent_tool.c.mcp_server_id.asc())
        ).all()
        return [int(row[0]) for row in rows]

    def tool_count(self, agent_id: int) -> int:
        return int(
            self._session.execute(
                sa.select(sa.func.count())
                .select_from(self._agent_tool)
                .where(self._agent_tool.c.agent_id == agent_id)
            ).scalar_one()
        )

    def list_available_tool_ids(self, tool_ids: list[int]) -> list[int]:
        if not tool_ids:
            return []
        rows = self._session.execute(
            sa.select(self._mcp_server.c.id).where(
                self._mcp_server.c.id.in_(tool_ids),
                self._mcp_server.c.enabled.is_(True),
                self._mcp_server.c.deleted.is_(False),
            )
        ).all()
        return [int(row[0]) for row in rows]

    def replace_tool_bindings(self, agent_id: int, tool_ids: list[int]) -> None:
        now = datetime.now()
        self._session.execute(self._agent_tool.delete().where(self._agent_tool.c.agent_id == agent_id))
        if tool_ids:
            self._session.execute(
                self._agent_tool.insert(),
                [
                    {
                        "agent_id": agent_id,
                        "mcp_server_id": tool_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                    for tool_id in tool_ids
                ],
            )
        self._session.commit()
