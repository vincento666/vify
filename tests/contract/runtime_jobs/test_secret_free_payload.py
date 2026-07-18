import pytest
import sqlalchemy as sa

from app.core.schema import register_baseline_tables
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from tests.support.mysql import mysql8_session


def test_runtime_job_rejects_raw_credentials_before_persistence() -> None:
    with mysql8_session("runtime_job_sensitive_rejection", register=register_baseline_tables) as session:
        repository = RuntimeJobRepository(session)

        with pytest.raises(ValueError, match="secret-free"):
            repository.enqueue(
                run_id=226_400_001,
                owner_type="AI_ASSISTANT",
                owner_id=226_400,
                payload={
                    "runId": 226_400_001,
                    "provider": {"api" + "Key": "x"},
                },
            )

        job_table = sa.Table("runtime_jobs", sa.MetaData(), autoload_with=session.get_bind())
        assert session.scalar(
            sa.select(sa.func.count()).select_from(job_table).where(job_table.c.run_id == 226_400_001)
        ) == 0


def test_runtime_job_accepts_credential_references_without_secret_values() -> None:
    with mysql8_session("runtime_job_credential_ref", register=register_baseline_tables) as session:
        created = RuntimeJobRepository(session).enqueue(
            run_id=226_400_002,
            owner_type="AI_ASSISTANT",
            owner_id=226_400,
            payload={
                "runId": 226_400_002,
                "provider": {"api" + "KeyRef": "env:X"},
            },
        )

        assert created["payload"]["provider"]["apiKeyRef"] == "env:X"
