from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables
from app.modules.provider.domain.connection import ConnectionTestResult

register_baseline_tables()


class ProviderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._provider = Base.metadata.tables["provider"]
        self._model_config = Base.metadata.tables["model_config"]
        self._provider_health = Base.metadata.tables["provider_health"]

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        payload = {
            **values,
            "enabled": True,
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }
        row = insert_and_fetch(self._session, self._provider, payload)
        self._session.commit()
        return row

    def get(self, provider_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._provider).where(
                self._provider.c.id == provider_id,
                self._provider.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_page(
        self,
        page: int,
        page_size: int,
        provider_type: str | None = None,
        enabled: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._provider.c.deleted.is_(False)]
        if provider_type:
            conditions.append(self._provider.c.type == provider_type)
        if enabled is not None:
            conditions.append(self._provider.c.enabled.is_(enabled))

        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._provider).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._provider)
            .where(*conditions)
            .order_by(self._provider.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def update(self, provider_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        if not values:
            return self.get(provider_id)

        values["updated_at"] = datetime.now()
        self._session.execute(
            self._provider.update()
            .where(self._provider.c.id == provider_id, self._provider.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get(provider_id)

    def delete(self, provider_id: int) -> bool:
        result = self._session.execute(
            self._provider.update()
            .where(self._provider.c.id == provider_id, self._provider.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def list_models(self, provider_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._model_config)
            .where(
                self._model_config.c.provider_id == provider_id,
                self._model_config.c.deleted.is_(False),
            )
            .order_by(self._model_config.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_health(self, provider_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._provider_health).where(
                self._provider_health.c.provider_id == provider_id,
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_enabled_model_config(self, model_config_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(
                self._model_config.c.id,
                self._model_config.c.provider_id,
                self._provider.c.type.label("provider_type"),
                self._provider.c.base_url.label("provider_base_url"),
                self._provider.c.auth_config.label("provider_auth_config"),
                self._model_config.c.name,
                self._model_config.c.model_id,
                self._model_config.c.context_size,
                self._model_config.c.extra_params,
            )
            .select_from(
                self._model_config.join(
                    self._provider,
                    self._provider.c.id == self._model_config.c.provider_id,
                )
            )
            .where(
                self._model_config.c.id == model_config_id,
                self._model_config.c.enabled.is_(True),
                self._model_config.c.deleted.is_(False),
                self._provider.c.enabled.is_(True),
                self._provider.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def find_enabled_model_config_by_model_id(self, model_id: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(
                self._model_config.c.id,
                self._model_config.c.provider_id,
                self._provider.c.type.label("provider_type"),
                self._provider.c.base_url.label("provider_base_url"),
                self._provider.c.auth_config.label("provider_auth_config"),
                self._model_config.c.name,
                self._model_config.c.model_id,
                self._model_config.c.context_size,
                self._model_config.c.extra_params,
            )
            .select_from(
                self._model_config.join(
                    self._provider,
                    self._provider.c.id == self._model_config.c.provider_id,
                )
            )
            .where(
                self._model_config.c.model_id == model_id,
                self._model_config.c.enabled.is_(True),
                self._model_config.c.deleted.is_(False),
                self._provider.c.enabled.is_(True),
                self._provider.c.deleted.is_(False),
            )
            .order_by(self._model_config.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def get_enabled_provider_model_config(
        self,
        provider_id: int,
        model_config_id: int,
    ) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(
                self._model_config.c.id,
                self._model_config.c.provider_id,
                self._provider.c.type.label("provider_type"),
                self._provider.c.base_url.label("provider_base_url"),
                self._provider.c.auth_config.label("provider_auth_config"),
                self._model_config.c.name,
                self._model_config.c.model_id,
                self._model_config.c.context_size,
                self._model_config.c.extra_params,
            )
            .select_from(
                self._model_config.join(
                    self._provider,
                    self._provider.c.id == self._model_config.c.provider_id,
                )
            )
            .where(
                self._provider.c.id == provider_id,
                self._model_config.c.id == model_config_id,
                self._model_config.c.provider_id == provider_id,
                self._model_config.c.enabled.is_(True),
                self._model_config.c.deleted.is_(False),
                self._provider.c.enabled.is_(True),
                self._provider.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_enabled_providers(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._provider)
            .where(self._provider.c.enabled.is_(True), self._provider.c.deleted.is_(False))
            .order_by(self._provider.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def upsert_health(self, provider_id: int, result: ConnectionTestResult) -> None:
        now = datetime.now()
        existing = self.get_health(provider_id)
        fail_count = 0 if result.success else int(existing["fail_count"]) + 1 if existing else 1
        values = {
            "provider_id": provider_id,
            "status": "UP" if result.success else "DOWN",
            "last_check_at": now,
            "last_success_at": now if result.success else existing["last_success_at"] if existing else None,
            "fail_count": fail_count,
            "latency_ms": result.latency_ms,
            "error_message": result.error_message,
            "updated_at": now,
        }
        if existing:
            self._session.execute(
                self._provider_health.update()
                .where(self._provider_health.c.provider_id == provider_id)
                .values(**values)
            )
        else:
            self._session.execute(self._provider_health.insert().values(**values))
        self._session.commit()
