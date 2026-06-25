from __future__ import annotations

from datetime import datetime, timedelta
import secrets
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables

register_baseline_tables()


class RuntimeJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._job = Base.metadata.tables["runtime_jobs"]

    def enqueue(
        self,
        *,
        run_id: int,
        owner_type: str,
        owner_id: int,
        job_type: str = "runtime_v2_completion",
        payload: dict[str, Any] | None = None,
        priority: int = 100,
        max_attempts: int = 3,
        available_at: datetime | None = None,
    ) -> dict[str, Any]:
        existing = self.get_by_run(run_id, job_type=job_type)
        if existing is not None:
            return existing
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._job,
            {
                "run_id": run_id,
                "owner_type": owner_type.upper(),
                "owner_id": owner_id,
                "job_type": job_type,
                "status": "QUEUED",
                "priority": priority,
                "attempt_count": 0,
                "max_attempts": max_attempts,
                "lease_owner": "",
                "lease_token": "",
                "lease_expires_at": None,
                "last_heartbeat_at": None,
                "available_at": available_at,
                "started_at": None,
                "finished_at": None,
                "last_error": None,
                "payload": payload or {},
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def get(self, job_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._job).where(
                self._job.c.id == job_id,
                self._job.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_by_run(self, run_id: int, *, job_type: str = "runtime_v2_completion") -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._job)
            .where(
                self._job.c.run_id == run_id,
                self._job.c.job_type == job_type,
                self._job.c.deleted.is_(False),
            )
            .order_by(self._job.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        owner_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        now = datetime.now()
        owner_filter = _normalize_owner_types(owner_types)
        conditions = [
            self._job.c.deleted.is_(False),
            sa.or_(
                sa.and_(
                    self._job.c.status == "QUEUED",
                    sa.or_(self._job.c.available_at.is_(None), self._job.c.available_at <= now),
                ),
                sa.and_(
                    self._job.c.status == "RUNNING",
                    self._job.c.lease_expires_at.is_not(None),
                    self._job.c.lease_expires_at < now,
                ),
            ),
        ]
        if owner_filter is not None:
            conditions.append(self._job.c.owner_type.in_(owner_filter))
        row = self._session.execute(
            sa.select(self._job)
            .where(*conditions)
            .order_by(self._job.c.priority.asc(), self._job.c.id.asc())
            .limit(1)
        ).mappings().first()
        if row is None:
            return None
        return self._claim_row(dict(row), worker_id=worker_id, lease_seconds=lease_seconds)

    def claim(
        self,
        job_id: int,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        owner_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        now = datetime.now()
        owner_filter = _normalize_owner_types(owner_types)
        conditions = [
            self._job.c.id == job_id,
            self._job.c.deleted.is_(False),
            sa.or_(
                self._job.c.status == "QUEUED",
                sa.and_(
                    self._job.c.status == "RUNNING",
                    self._job.c.lease_expires_at.is_not(None),
                    self._job.c.lease_expires_at < now,
                ),
            ),
        ]
        if owner_filter is not None:
            conditions.append(self._job.c.owner_type.in_(owner_filter))
        row = self._session.execute(
            sa.select(self._job).where(*conditions)
        ).mappings().one_or_none()
        if row is None:
            return None
        return self._claim_row(dict(row), worker_id=worker_id, lease_seconds=lease_seconds)

    def heartbeat(
        self,
        job_id: int,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        lease_token: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "RUNNING",
                self._job.c.lease_owner == worker_id,
                self._job.c.lease_token == (lease_token or self._lease_token_for(job_id)),
                self._job.c.deleted.is_(False),
            )
            .values(
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                last_heartbeat_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        return self._required(job_id)

    def complete(self, job_id: int, *, worker_id: str, lease_token: str | None = None) -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "RUNNING",
                self._job.c.lease_owner == worker_id,
                self._job.c.lease_token == (lease_token or self._lease_token_for(job_id)),
                self._job.c.deleted.is_(False),
            )
            .values(status="COMPLETED", finished_at=now, lease_expires_at=None, updated_at=now)
        )
        self._session.commit()
        return self._required(job_id)

    def fail(self, job_id: int, *, worker_id: str, error: str, lease_token: str | None = None) -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "RUNNING",
                self._job.c.lease_owner == worker_id,
                self._job.c.lease_token == (lease_token or self._lease_token_for(job_id)),
                self._job.c.deleted.is_(False),
            )
            .values(
                status="FAILED",
                last_error=error,
                finished_at=now,
                lease_expires_at=None,
                updated_at=now,
            )
        )
        self._session.commit()
        return self._required(job_id)

    def cancel_by_run(self, run_id: int, *, reason: str = "cancelled") -> dict[str, Any] | None:
        row = self.get_by_run(run_id)
        if row is None or row["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return row
        now = datetime.now()
        self._session.execute(
            self._job.update()
            .where(self._job.c.id == int(row["id"]))
            .values(status="CANCELLED", last_error=reason, finished_at=now, lease_expires_at=None, updated_at=now)
        )
        self._session.commit()
        return self._required(int(row["id"]))

    def _claim_row(self, row: dict[str, Any], *, worker_id: str, lease_seconds: int) -> dict[str, Any]:
        now = datetime.now()
        started_at = row["started_at"] or now
        lease_token = secrets.token_urlsafe(24)
        self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == int(row["id"]),
                self._job.c.status.in_(("QUEUED", "RUNNING")),
                self._job.c.deleted.is_(False),
            )
            .values(
                status="RUNNING",
                lease_owner=worker_id,
                lease_token=lease_token,
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                last_heartbeat_at=now,
                started_at=started_at,
                attempt_count=int(row["attempt_count"] or 0) + 1,
                updated_at=now,
            )
        )
        self._session.commit()
        return self._required(int(row["id"]))

    def _required(self, job_id: int) -> dict[str, Any]:
        row = self.get(job_id)
        if row is None:
            raise RuntimeError(f"Runtime job {job_id} not found")
        return row

    def _lease_token_for(self, job_id: int) -> str:
        row = self.get(job_id)
        return str(row.get("lease_token") or "") if row is not None else ""


def _normalize_owner_types(owner_types: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if owner_types is None:
        return None
    normalized = tuple(sorted({str(owner_type).upper() for owner_type in owner_types if str(owner_type).strip()}))
    return normalized or None
