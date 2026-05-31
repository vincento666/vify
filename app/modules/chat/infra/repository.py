from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.schema import register_baseline_tables

register_baseline_tables()


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._agent = Base.metadata.tables["agent"]
        self._agent_tool = Base.metadata.tables["agent_tool"]
        self._chat_session = Base.metadata.tables["chat_session"]
        self._chat_message = Base.metadata.tables["chat_message"]

    def agent_exists(self, agent_id: int) -> bool:
        return (
            self._session.execute(
                sa.select(sa.func.count()).select_from(self._agent).where(
                    self._agent.c.id == agent_id,
                    self._agent.c.deleted.is_(False),
                )
            ).scalar_one()
            > 0
        )

    def create_session(self, agent_id: int) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._chat_session.insert()
            .values(
                agent_id=agent_id,
                title="新对话",
                status="ACTIVE",
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._chat_session)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._chat_session).where(
                self._chat_session.c.id == session_id,
                self._chat_session.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_agent(self, agent_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._agent).where(
                self._agent.c.id == agent_id,
                self._agent.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_agent_tool_ids(self, agent_id: int) -> list[int]:
        rows = self._session.execute(
            sa.select(self._agent_tool.c.mcp_server_id)
            .where(self._agent_tool.c.agent_id == agent_id)
            .order_by(self._agent_tool.c.mcp_server_id.asc())
        ).all()
        return [int(row[0]) for row in rows]

    def list_sessions(
        self,
        page: int,
        page_size: int,
        agent_id: int | None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._chat_session.c.deleted.is_(False)]
        if agent_id is not None:
            conditions.append(self._chat_session.c.agent_id == agent_id)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._chat_session).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._chat_session)
            .where(*conditions)
            .order_by(self._chat_session.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def delete_session(self, session_id: int) -> bool:
        result = self._session.execute(
            self._chat_session.update()
            .where(self._chat_session.c.id == session_id, self._chat_session.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def rename_session_if_default(self, session_id: int, title: str) -> None:
        self._session.execute(
            self._chat_session.update()
            .where(
                self._chat_session.c.id == session_id,
                self._chat_session.c.title == "新对话",
                self._chat_session.c.deleted.is_(False),
            )
            .values(title=title[:200], updated_at=datetime.now())
        )
        self._session.commit()

    def list_messages(
        self,
        session_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [
            self._chat_message.c.session_id == session_id,
            self._chat_message.c.deleted.is_(False),
        ]
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._chat_message).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._chat_message)
            .where(*conditions)
            .order_by(self._chat_message.c.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def insert_message(
        self,
        session_id: int,
        role: str,
        content: str,
        tokens: int = 0,
        finish_reason: str = "",
        latency_ms: int = 0,
    ) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._chat_message.insert()
            .values(
                session_id=session_id,
                role=role,
                content=content,
                tokens=tokens,
                finish_reason=finish_reason,
                latency_ms=latency_ms,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._chat_message)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row
