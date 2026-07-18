from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository


class RuntimeJobLeaseGuard:
    def __init__(
        self,
        session: Session,
        *,
        job_id: int,
        worker_id: str,
        lease_fence: str,
    ) -> None:
        self._repository = RuntimeJobRepository(session)
        self._job_id = int(job_id)
        self._worker_id = worker_id
        self._lease_fence = lease_fence

    def __call__(self) -> None:
        self._repository.assert_lease_owned(
            self._job_id,
            worker_id=self._worker_id,
            lease_token=self._lease_fence,
        )
