from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.schema import register_baseline_tables

register_baseline_tables()


class WorkflowPublishRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._version = Base.metadata.tables["workflow_published_version"]

    def next_version(self, workflow_id: int, flow_type: str) -> int:
        latest = self._session.execute(
            sa.select(sa.func.max(self._version.c.version)).where(
                self._version.c.workflow_id == workflow_id,
                self._version.c.flow_type == flow_type,
                self._version.c.deleted.is_(False),
            )
        ).scalar_one()
        return int(latest or 0) + 1

    def create_version(
        self,
        *,
        workflow_id: int,
        flow_type: str,
        version: int,
        snapshot: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._version.update()
            .where(
                self._version.c.workflow_id == workflow_id,
                self._version.c.flow_type == flow_type,
                self._version.c.deleted.is_(False),
            )
            .values(active=False, updated_at=now)
        )
        row = self._session.execute(
            self._version.insert()
            .values(
                workflow_id=workflow_id,
                flow_type=flow_type,
                version=version,
                snapshot=snapshot,
                validation=validation,
                active=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._version)
        ).mappings().one()
        self._session.commit()
        return dict(row)

    def list_versions(self, workflow_id: int, flow_type: str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._version)
            .where(
                self._version.c.workflow_id == workflow_id,
                self._version.c.flow_type == flow_type,
                self._version.c.deleted.is_(False),
            )
            .order_by(self._version.c.version.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_version(self, workflow_id: int, flow_type: str, version_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._version).where(
                self._version.c.id == version_id,
                self._version.c.workflow_id == workflow_id,
                self._version.c.flow_type == flow_type,
                self._version.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def active_version(self, workflow_id: int, flow_type: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._version).where(
                self._version.c.workflow_id == workflow_id,
                self._version.c.flow_type == flow_type,
                self._version.c.active.is_(True),
                self._version.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def activate_version(self, workflow_id: int, flow_type: str, version_id: int) -> dict[str, Any] | None:
        row = self.get_version(workflow_id, flow_type, version_id)
        if row is None:
            return None
        now = datetime.now()
        self._session.execute(
            self._version.update()
            .where(
                self._version.c.workflow_id == workflow_id,
                self._version.c.flow_type == flow_type,
                self._version.c.deleted.is_(False),
            )
            .values(active=False, updated_at=now)
        )
        activated = self._session.execute(
            self._version.update()
            .where(self._version.c.id == version_id)
            .values(active=True, updated_at=now)
            .returning(self._version)
        ).mappings().one()
        self._session.commit()
        return dict(activated)
