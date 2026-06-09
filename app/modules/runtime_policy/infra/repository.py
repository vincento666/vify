from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables, runtime_policy_tables

register_runtime_policy_tables()


class RuntimePolicyRepository:
    def __init__(self, session: Session) -> None:
        register_runtime_policy_tables()
        self._session = session
        self._profile = Base.metadata.tables["runtime_policy_profile"]
        self._decision_log = Base.metadata.tables["runtime_decision_log"]
        self._evaluation_run = Base.metadata.tables["runtime_policy_evaluation_run"]
        self._ensure_tables()

    @property
    def session(self) -> Session:
        return self._session

    def create_profile(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._profile.insert()
            .values(
                **values,
                version=1,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._profile)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_profile(self, profile_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._profile).where(
                self._profile.c.id == profile_id,
                self._profile.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_profiles(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        mode: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._profile.c.deleted.is_(False)]
        if status:
            conditions.append(self._profile.c.status == status)
        if mode:
            conditions.append(self._profile.c.mode == mode)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._profile).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._profile)
            .where(*conditions)
            .order_by(self._profile.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def list_active_profiles(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._profile)
            .where(
                self._profile.c.status == "active",
                self._profile.c.deleted.is_(False),
            )
            .order_by(self._profile.c.id.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def update_profile(self, profile_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        existing = self.get_profile(profile_id)
        if existing is None:
            return None
        now = datetime.now()
        self._session.execute(
            self._profile.update()
            .where(
                self._profile.c.id == profile_id,
                self._profile.c.deleted.is_(False),
            )
            .values(
                **values,
                version=int(existing["version"]) + 1,
                updated_at=now,
            )
        )
        self._session.commit()
        return self.get_profile(profile_id)

    def delete_profile(self, profile_id: int) -> bool:
        result = self._session.execute(
            self._profile.update()
            .where(
                self._profile.c.id == profile_id,
                self._profile.c.deleted.is_(False),
            )
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def create_decision_log(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._decision_log.insert()
            .values(
                **values,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._decision_log)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_decision_log(self, log_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._decision_log).where(
                self._decision_log.c.id == log_id,
                self._decision_log.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_decision_logs(
        self,
        page: int,
        page_size: int,
        *,
        session_id: int | None = None,
        profile_id: int | None = None,
        action: str | None = None,
        source_layer: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._decision_log.c.deleted.is_(False)]
        if session_id is not None:
            conditions.append(self._decision_log.c.session_id == session_id)
        if profile_id is not None:
            conditions.append(self._decision_log.c.policy_profile_id == profile_id)
        if action:
            conditions.append(self._decision_log.c.final_action == action)
        if source_layer:
            conditions.append(self._decision_log.c.source_layer == source_layer)
        if created_from is not None:
            conditions.append(self._decision_log.c.created_at >= created_from)
        if created_to is not None:
            conditions.append(self._decision_log.c.created_at <= created_to)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._decision_log).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._decision_log)
            .where(*conditions)
            .order_by(self._decision_log.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create_evaluation_run(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._evaluation_run.insert()
            .values(
                **values,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._evaluation_run)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_evaluation_run(self, run_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._evaluation_run).where(
                self._evaluation_run.c.id == run_id,
                self._evaluation_run.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_evaluation_runs(
        self,
        page: int,
        page_size: int,
        *,
        profile_id: int | None = None,
        run_type: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._evaluation_run.c.deleted.is_(False)]
        if profile_id is not None:
            conditions.append(self._evaluation_run.c.profile_id == profile_id)
        if run_type:
            conditions.append(self._evaluation_run.c.run_type == run_type)
        if status:
            conditions.append(self._evaluation_run.c.status == status)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._evaluation_run).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._evaluation_run)
            .where(*conditions)
            .order_by(self._evaluation_run.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def _ensure_tables(self) -> None:
        bind = self._session.get_bind()
        if bind is None:
            return
        Base.metadata.create_all(bind=bind, tables=runtime_policy_tables())
