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
        self._release = Base.metadata.tables["runtime_policy_release"]
        self._audit_event = Base.metadata.tables["runtime_policy_audit_event"]
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

    def set_profile_status(self, profile_id: int, status: str) -> dict[str, Any] | None:
        self._session.execute(
            self._profile.update()
            .where(
                self._profile.c.id == profile_id,
                self._profile.c.deleted.is_(False),
            )
            .values(status=status, updated_at=datetime.now())
        )
        self._session.commit()
        return self.get_profile(profile_id)

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

    def create_release(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._release.insert()
            .values(
                **values,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._release)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_release(self, release_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._release).where(
                self._release.c.id == release_id,
                self._release.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_release(self, release_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        existing = self.get_release(release_id)
        if existing is None:
            return None
        self._session.execute(
            self._release.update()
            .where(
                self._release.c.id == release_id,
                self._release.c.deleted.is_(False),
            )
            .values(**values, updated_at=datetime.now())
        )
        self._session.commit()
        return self.get_release(release_id)

    def list_releases(
        self,
        page: int,
        page_size: int,
        *,
        profile_id: int | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._release.c.deleted.is_(False)]
        if profile_id is not None:
            conditions.append(self._release.c.profile_id == profile_id)
        if status:
            conditions.append(self._release.c.status == status)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._release).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._release)
            .where(*conditions)
            .order_by(self._release.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def list_releases_for_profile(self, profile_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._release)
            .where(
                self._release.c.profile_id == profile_id,
                self._release.c.deleted.is_(False),
            )
            .order_by(self._release.c.id.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def create_audit_event(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._audit_event.insert()
            .values(
                **values,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._audit_event)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def list_audit_events(
        self,
        page: int,
        page_size: int,
        *,
        release_id: int | None = None,
        evaluation_run_id: int | None = None,
        profile_id: int | None = None,
        event_type: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._audit_event.c.deleted.is_(False)]
        if release_id is not None:
            conditions.append(self._audit_event.c.release_id == release_id)
        if evaluation_run_id is not None:
            conditions.append(self._audit_event.c.evaluation_run_id == evaluation_run_id)
        if profile_id is not None:
            conditions.append(self._audit_event.c.profile_id == profile_id)
        if event_type:
            conditions.append(self._audit_event.c.event_type == event_type)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._audit_event).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._audit_event)
            .where(*conditions)
            .order_by(self._audit_event.c.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def _ensure_tables(self) -> None:
        bind = self._session.get_bind()
        if bind is None:
            return
        Base.metadata.create_all(bind=bind, tables=runtime_policy_tables())
