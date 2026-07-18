from __future__ import annotations

from datetime import datetime, timedelta
import secrets
import time
from typing import Any

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables
from app.modules.runtime.domain.runtime_job_worker import RuntimeJobLeaseLost
from app.modules.runtime.domain.job_payload import validate_durable_job_payload

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
        validated_payload = validate_durable_job_payload(payload or {})
        normalized_owner_type = owner_type.upper()
        existing = self.get_by_run(
            run_id,
            owner_type=normalized_owner_type,
            job_type=job_type,
        )
        if existing is not None:
            if (
                str(existing.get("status") or "").upper() == "FAILED"
                and str(job_type).startswith("runtime_v2_resume:")
            ):
                return self._requeue_failed_resume_job(int(existing["id"]), validated_payload)
            return existing
        now = datetime.now()
        try:
            row = insert_and_fetch(
                self._session,
                self._job,
                {
                    "run_id": run_id,
                    "owner_type": normalized_owner_type,
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
                    "payload": validated_payload,
                    "deleted": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            self._session.commit()
            return row
        except IntegrityError:
            self._session.rollback()
            existing = self.get_by_run(
                run_id,
                owner_type=normalized_owner_type,
                job_type=job_type,
            )
            if existing is not None:
                if (
                    str(existing.get("status") or "").upper() == "FAILED"
                    and str(job_type).startswith("runtime_v2_resume:")
                ):
                    return self._requeue_failed_resume_job(int(existing["id"]), validated_payload)
                return existing
            raise

    def _requeue_failed_resume_job(
        self,
        job_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Atomically make a user-requested V2 resume retry eligible for a fresh attempt budget."""
        now = datetime.now()
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "FAILED",
                self._job.c.deleted.is_(False),
            )
            .values(
                status="QUEUED",
                attempt_count=0,
                lease_owner="",
                lease_token="",
                lease_expires_at=None,
                last_heartbeat_at=None,
                available_at=None,
                started_at=None,
                finished_at=None,
                last_error=None,
                payload=payload or {},
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            existing = self.get(job_id)
            if existing is None:
                raise RuntimeError(f"Runtime resume job {job_id} not found")
            return existing
        self._session.commit()
        return self._required(job_id)

    def get(self, job_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._job).where(
                self._job.c.id == job_id,
                self._job.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_by_run(
        self,
        run_id: int,
        *,
        owner_type: str | None = None,
        job_type: str = "runtime_v2_completion",
    ) -> dict[str, Any] | None:
        conditions = [
            self._job.c.run_id == run_id,
            self._job.c.job_type == job_type,
            self._job.c.deleted.is_(False),
        ]
        normalized_owner_type = str(owner_type or "").strip().upper()
        if normalized_owner_type:
            conditions.append(self._job.c.owner_type == normalized_owner_type)
        row = self._session.execute(
            sa.select(self._job)
            .where(*conditions)
            .order_by(self._job.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def list_active_for_queue_gate(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._job)
            .where(
                self._job.c.deleted.is_(False),
                self._job.c.status.in_(("QUEUED", "RUNNING")),
            )
            .order_by(self._job.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def count_active(
        self,
        *,
        owner_types: tuple[str, ...] | None = None,
    ) -> int:
        conditions = [
            self._job.c.deleted.is_(False),
            self._job.c.status.in_(("QUEUED", "RUNNING")),
        ]
        owner_filter = _normalize_owner_types(owner_types)
        if owner_filter is not None:
            conditions.append(self._job.c.owner_type.in_(owner_filter))
        return int(
            self._session.execute(
                sa.select(sa.func.count()).select_from(self._job).where(*conditions)
            ).scalar_one()
        )

    def list_jobs(
        self,
        *,
        page: int,
        page_size: int,
        owner_type: str | None = None,
        status: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions = [self._job.c.deleted.is_(False)]
        normalized_owner_type = str(owner_type or "").strip().upper()
        normalized_status = str(status or "").strip().upper()
        normalized_tenant_id = str(tenant_id or "").strip()
        if normalized_owner_type:
            conditions.append(self._job.c.owner_type == normalized_owner_type)
        if normalized_status:
            conditions.append(self._job.c.status == normalized_status)

        rows = self._session.execute(
            sa.select(self._job)
            .where(*conditions)
            .order_by(self._job.c.updated_at.desc(), self._job.c.id.desc())
        ).mappings().all()

        items: list[dict[str, Any]] = []
        for row in rows:
            item = _runtime_ops_job_item(dict(row))
            if normalized_tenant_id and item["tenantId"] != normalized_tenant_id:
                continue
            items.append(item)

        safe_page = max(1, int(page or 1))
        safe_page_size = max(1, int(page_size or 20))
        start = (safe_page - 1) * safe_page_size
        return items[start : start + safe_page_size], len(items)

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        owner_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        for attempt in range(50):
            now = datetime.now()
            lease_token = secrets.token_urlsafe(24)
            owner_filter = _normalize_owner_types(owner_types)
            owner_clause = ""
            params: dict[str, Any] = {
                "worker_id": worker_id,
                "lease_token": lease_token,
                "lease_expires_at": now + timedelta(seconds=lease_seconds),
                "now": now,
            }
            if owner_filter is not None:
                owner_placeholders: list[str] = []
                for index, owner_type in enumerate(owner_filter):
                    name = f"owner_type_{index}"
                    owner_placeholders.append(f":{name}")
                    params[name] = owner_type
                owner_clause = f" AND owner_type IN ({', '.join(owner_placeholders)})"
            try:
                result = self._session.execute(
                    sa.text(
                        f"""
                        UPDATE runtime_jobs
                        SET status = 'RUNNING',
                            lease_owner = :worker_id,
                            lease_token = :lease_token,
                            lease_expires_at = :lease_expires_at,
                            last_heartbeat_at = :now,
                            started_at = COALESCE(started_at, :now),
                            attempt_count = attempt_count + 1,
                            updated_at = :now
                        WHERE deleted = 0
                          AND (
                            (status = 'QUEUED' AND (available_at IS NULL OR available_at <= :now))
                            OR (status = 'RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at < :now)
                          )
                          {owner_clause}
                        ORDER BY priority ASC, id ASC
                        LIMIT 1
                        """
                    ),
                    params,
                )
            except OperationalError:
                self._session.rollback()
                time.sleep(min(0.001 * (attempt + 1), 0.02))
                continue
            if result.rowcount != 1:
                self._session.rollback()
                return None
            self._session.commit()
            row = self._session.execute(
                sa.select(self._job).where(
                    self._job.c.lease_token == lease_token,
                    self._job.c.lease_owner == worker_id,
                    self._job.c.deleted.is_(False),
                )
            ).mappings().one_or_none()
            return dict(row) if row else None
        return None

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
            sa.select(self._job).where(*conditions).with_for_update(skip_locked=True)
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
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "RUNNING",
                self._job.c.lease_owner == worker_id,
                self._job.c.lease_token == (lease_token or self._lease_token_for(job_id)),
                self._job.c.lease_expires_at.is_not(None),
                self._job.c.lease_expires_at > now,
                self._job.c.deleted.is_(False),
            )
            .values(
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                last_heartbeat_at=now,
                updated_at=now,
            )
        )
        self._ensure_owned_update(result.rowcount, job_id)
        self._session.commit()
        return self._required(job_id)

    def complete(self, job_id: int, *, worker_id: str, lease_token: str | None = None) -> dict[str, Any]:
        for attempt in range(10):
            now = datetime.now()
            try:
                result = self._session.execute(
                    self._job.update()
                    .where(
                        self._job.c.id == job_id,
                        self._job.c.status == "RUNNING",
                        self._job.c.lease_owner == worker_id,
                        self._job.c.lease_token == (lease_token or self._lease_token_for(job_id)),
                        self._job.c.lease_expires_at.is_not(None),
                        self._job.c.lease_expires_at > now,
                        self._job.c.deleted.is_(False),
                    )
                    .values(status="COMPLETED", finished_at=now, lease_expires_at=None, updated_at=now)
                )
            except OperationalError as exc:
                self._session.rollback()
                if not _is_deadlock_or_serialization_failure(exc) or attempt >= 9:
                    raise
                time.sleep(min(0.001 * (attempt + 1), 0.02))
                continue
            self._ensure_owned_update(result.rowcount, job_id)
            self._session.commit()
            return self._required(job_id)
        raise RuntimeError(f"Runtime job {job_id} completion retry exhausted")

    def fail(
        self,
        job_id: int,
        *,
        worker_id: str,
        error: str,
        lease_token: str | None = None,
        retry_backoff_seconds: tuple[int, ...] = (5, 30, 120),
    ) -> dict[str, Any]:
        now = datetime.now()
        row = self._required(job_id)
        attempt_count = int(row["attempt_count"] or 0)
        max_attempts = max(1, int(row["max_attempts"] or 1))
        should_retry = attempt_count < max_attempts
        values: dict[str, Any]
        if should_retry:
            values = {
                "status": "QUEUED",
                "last_error": error,
                "available_at": now + timedelta(seconds=_retry_delay_seconds(attempt_count, retry_backoff_seconds)),
                "lease_owner": "",
                "lease_token": "",
                "lease_expires_at": None,
                "last_heartbeat_at": None,
                "finished_at": None,
                "updated_at": now,
            }
        else:
            values = {
                "status": "FAILED",
                "last_error": error,
                "available_at": None,
                "lease_owner": "",
                "lease_token": "",
                "lease_expires_at": None,
                "finished_at": now,
                "updated_at": now,
            }
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "RUNNING",
                self._job.c.lease_owner == worker_id,
                self._job.c.lease_token == (lease_token or self._lease_token_for(job_id)),
                self._job.c.lease_expires_at.is_not(None),
                self._job.c.lease_expires_at > now,
                self._job.c.deleted.is_(False),
            )
            .values(**values)
        )
        self._ensure_owned_update(result.rowcount, job_id)
        self._session.commit()
        return self._required(job_id)

    def cancel_by_run(
        self,
        run_id: int,
        *,
        owner_type: str | None = None,
        job_type: str = "runtime_v2_completion",
        reason: str = "cancelled",
    ) -> dict[str, Any] | None:
        row = self.get_by_run(
            run_id,
            owner_type=owner_type,
            job_type=job_type,
        )
        if row is None or row["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return row
        now = datetime.now()
        self._session.execute(
            self._job.update()
            .where(self._job.c.id == int(row["id"]))
            .values(
                status="CANCELLED",
                last_error=reason,
                lease_owner="",
                lease_token="",
                finished_at=now,
                lease_expires_at=None,
                updated_at=now,
            )
        )
        self._session.commit()
        return self._required(int(row["id"]))

    def requeue_cancelled(self, job_id: int) -> dict[str, Any]:
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "CANCELLED",
                self._job.c.deleted.is_(False),
            )
            .values(
                status="QUEUED",
                available_at=None,
                lease_owner="",
                lease_token="",
                lease_expires_at=None,
                last_heartbeat_at=None,
                finished_at=None,
                last_error=None,
                updated_at=datetime.now(),
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            raise RuntimeError(f"Runtime job {job_id} is not cancelled")
        self._session.commit()
        return self._required(job_id)

    def list_dlq(self, *, owner_types: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        conditions = [
            self._job.c.deleted.is_(False),
            self._job.c.status == "FAILED",
        ]
        owner_filter = _normalize_owner_types(owner_types)
        if owner_filter is not None:
            conditions.append(self._job.c.owner_type.in_(owner_filter))
        rows = self._session.execute(
            sa.select(self._job)
            .where(*conditions)
            .order_by(self._job.c.updated_at.asc(), self._job.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def retry_dlq(self, job_id: int) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status.in_(("FAILED", "IGNORED")),
                self._job.c.deleted.is_(False),
            )
            .values(
                status="QUEUED",
                available_at=None,
                lease_owner="",
                lease_token="",
                lease_expires_at=None,
                last_heartbeat_at=None,
                finished_at=None,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            raise RuntimeError(f"Runtime job {job_id} is not retryable from DLQ")
        self._session.commit()
        return self._required(job_id)

    def ignore_dlq(self, job_id: int, *, reason: str = "ignored") -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "FAILED",
                self._job.c.deleted.is_(False),
            )
            .values(
                status="IGNORED",
                last_error=reason,
                lease_owner="",
                lease_token="",
                lease_expires_at=None,
                last_heartbeat_at=None,
                finished_at=now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            raise RuntimeError(f"Runtime job {job_id} is not ignorable from DLQ")
        self._session.commit()
        return self._required(job_id)

    def mark_dlq_resolved(self, job_id: int, *, reason: str = "resolved") -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status == "FAILED",
                self._job.c.deleted.is_(False),
            )
            .values(
                status="RESOLVED",
                last_error=reason,
                lease_owner="",
                lease_token="",
                lease_expires_at=None,
                last_heartbeat_at=None,
                finished_at=now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            raise RuntimeError(f"Runtime job {job_id} is not resolvable from DLQ")
        self._session.commit()
        return self._required(job_id)

    def reopen_dlq(self, job_id: int, *, reason: str = "reopened") -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == job_id,
                self._job.c.status.in_(("IGNORED", "RESOLVED")),
                self._job.c.deleted.is_(False),
            )
            .values(
                status="FAILED",
                last_error=reason,
                lease_owner="",
                lease_token="",
                lease_expires_at=None,
                last_heartbeat_at=None,
                finished_at=now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            raise RuntimeError(f"Runtime job {job_id} is not reopenable from DLQ")
        self._session.commit()
        return self._required(job_id)

    def _claim_row(self, row: dict[str, Any], *, worker_id: str, lease_seconds: int) -> dict[str, Any] | None:
        now = datetime.now()
        started_at = row["started_at"] or now
        lease_token = secrets.token_urlsafe(24)
        result = self._session.execute(
            self._job.update()
            .where(
                self._job.c.id == int(row["id"]),
                sa.or_(
                    self._job.c.status == "QUEUED",
                    sa.and_(
                        self._job.c.status == "RUNNING",
                        self._job.c.lease_expires_at.is_not(None),
                        self._job.c.lease_expires_at < now,
                    ),
                ),
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
        if result.rowcount != 1:
            self._session.rollback()
            return None
        self._session.commit()
        return self._required(int(row["id"]))

    def _required(self, job_id: int) -> dict[str, Any]:
        row = self.get(job_id)
        if row is None:
            raise RuntimeError(f"Runtime job {job_id} not found")
        return row

    def assert_lease_owned(
        self,
        job_id: int,
        *,
        worker_id: str,
        lease_token: str,
    ) -> None:
        now = datetime.now()
        owned = self._session.execute(
            sa.select(self._job.c.id).where(
                self._job.c.id == job_id,
                self._job.c.status == "RUNNING",
                self._job.c.lease_owner == worker_id,
                self._job.c.lease_token == lease_token,
                self._job.c.lease_expires_at.is_not(None),
                self._job.c.lease_expires_at > now,
                self._job.c.deleted.is_(False),
            )
        ).scalar_one_or_none()
        if owned is None:
            self._session.rollback()
            raise RuntimeJobLeaseLost(
                f"Runtime job {job_id} lease is no longer owned by {worker_id}"
            )

    def _ensure_owned_update(self, rowcount: int, job_id: int) -> None:
        if rowcount == 1:
            return
        self._session.rollback()
        raise RuntimeJobLeaseLost(
            f"Runtime job {job_id} lease is no longer owned by this worker"
        )

    def _lease_token_for(self, job_id: int) -> str:
        row = self.get(job_id)
        return str(row.get("lease_token") or "") if row is not None else ""


def _normalize_owner_types(owner_types: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if owner_types is None:
        return None
    normalized = tuple(sorted({str(owner_type).upper() for owner_type in owner_types if str(owner_type).strip()}))
    return normalized or None


def _retry_delay_seconds(attempt_count: int, retry_backoff_seconds: tuple[int, ...]) -> int:
    sequence = tuple(max(0, int(item)) for item in retry_backoff_seconds) or (0,)
    index = max(0, min(attempt_count - 1, len(sequence) - 1))
    return sequence[index]


def _is_deadlock_or_serialization_failure(exc: OperationalError) -> bool:
    original = getattr(exc, "orig", None)
    args = getattr(original, "args", ()) or ()
    errno = args[0] if args else None
    sqlstate = getattr(original, "sqlstate", None)
    message = str(original or exc).lower()
    return errno == 1213 or sqlstate == "40001" or "deadlock" in message


def _runtime_ops_job_item(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    job_id = int(row.get("id") or 0)
    available_at = _runtime_ops_iso(row.get("available_at"))
    return {
        "jobId": job_id,
        "runId": int(row.get("run_id") or 0),
        "ownerType": str(row.get("owner_type") or "").upper(),
        "ownerId": int(row.get("owner_id") or 0),
        "jobType": str(row.get("job_type") or ""),
        "status": str(row.get("status") or "").upper(),
        "priority": int(row.get("priority") or 0),
        "attemptCount": int(row.get("attempt_count") or 0),
        "maxAttempts": int(row.get("max_attempts") or 0),
        "leaseOwner": str(row.get("lease_owner") or ""),
        "leaseExpiresAt": _runtime_ops_iso(row.get("lease_expires_at")),
        "lastHeartbeatAt": _runtime_ops_iso(row.get("last_heartbeat_at")),
        "availableAt": available_at,
        "nextRetryAt": available_at,
        "startedAt": _runtime_ops_iso(row.get("started_at")),
        "finishedAt": _runtime_ops_iso(row.get("finished_at")),
        "lastError": str(row.get("last_error") or ""),
        "tenantId": str(payload.get("tenantId") or "local"),
        "createdAt": _runtime_ops_iso(row.get("created_at")),
        "updatedAt": _runtime_ops_iso(row.get("updated_at")),
        "statusRef": f"/api/v1/runtime-jobs/{job_id}",
        "runRef": f"/api/v1/runtime-runs/{int(row.get('run_id') or 0)}",
    }


def format_runtime_ops_job(row: dict[str, Any]) -> dict[str, Any]:
    return _runtime_ops_job_item(row)


def _runtime_ops_iso(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return None
