from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.schema import register_baseline_tables

register_baseline_tables()


class ChatflowChannelRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._channel_config = Base.metadata.tables["chatflow_channel_config"]

    def list_configs(self, chatflow_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._channel_config)
            .where(
                self._channel_config.c.chatflow_id == chatflow_id,
                self._channel_config.c.deleted.is_(False),
            )
            .order_by(self._channel_config.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_config(self, chatflow_id: int, channel_id: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._channel_config).where(
                self._channel_config.c.chatflow_id == chatflow_id,
                self._channel_config.c.channel_id == channel_id,
                self._channel_config.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def upsert_config(
        self,
        *,
        chatflow_id: int,
        channel_id: str,
        display_name: str,
        enabled: bool,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now()
        existing = self.get_config(chatflow_id, channel_id)
        if existing is None:
            row = self._session.execute(
                self._channel_config.insert()
                .values(
                    chatflow_id=chatflow_id,
                    channel_id=channel_id,
                    display_name=display_name,
                    enabled=enabled,
                    config=config,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
                .returning(self._channel_config)
            ).mappings().one()
        else:
            row = self._session.execute(
                self._channel_config.update()
                .where(self._channel_config.c.id == existing["id"])
                .values(
                    display_name=display_name,
                    enabled=enabled,
                    config=config,
                    updated_at=now,
                )
                .returning(self._channel_config)
            ).mappings().one()
        self._session.commit()
        return dict(row)
