from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.schema import register_baseline_tables

register_baseline_tables()


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._eval_set = Base.metadata.tables["eval_set"]
        self._eval_case = Base.metadata.tables["eval_case"]
        self._evaluator = Base.metadata.tables["evaluator"]
        self._agent = Base.metadata.tables["agent"]
        self._workflow = Base.metadata.tables["workflow"]
        self._experiment = Base.metadata.tables["evaluation_experiment"]
        self._run = Base.metadata.tables["evaluation_run"]
        self._case_result = Base.metadata.tables["evaluation_case_result"]

    @property
    def session(self) -> Session:
        return self._session

    def list_eval_sets(
        self,
        page: int,
        page_size: int,
        name: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._eval_set.c.deleted.is_(False)]
        if name:
            conditions.append(self._eval_set.c.name.like(f"%{name}%"))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._eval_set).where(*conditions)
        ).scalar_one()
        case_count = self._case_count_subquery()
        rows = self._session.execute(
            sa.select(self._eval_set, case_count.label("case_count"))
            .where(*conditions)
            .order_by(self._eval_set.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create_eval_set(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._eval_set.insert()
            .values(**values, deleted=False, created_at=now, updated_at=now)
            .returning(self._eval_set)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        row["case_count"] = 0
        return row

    def get_eval_set(self, eval_set_id: int) -> dict[str, Any] | None:
        case_count = self._case_count_subquery()
        row = self._session.execute(
            sa.select(self._eval_set, case_count.label("case_count")).where(
                self._eval_set.c.id == eval_set_id,
                self._eval_set.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_eval_set(self, eval_set_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        if not values:
            return self.get_eval_set(eval_set_id)
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._eval_set.update()
            .where(self._eval_set.c.id == eval_set_id, self._eval_set.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get_eval_set(eval_set_id)

    def delete_eval_set(self, eval_set_id: int) -> bool:
        now = datetime.now()
        result = self._session.execute(
            self._eval_set.update()
            .where(self._eval_set.c.id == eval_set_id, self._eval_set.c.deleted.is_(False))
            .values(deleted=True, updated_at=now)
        )
        if isinstance(result, CursorResult) and result.rowcount > 0:
            self._session.execute(
                self._eval_case.update()
                .where(self._eval_case.c.eval_set_id == eval_set_id, self._eval_case.c.deleted.is_(False))
                .values(deleted=True, updated_at=now)
            )
            self._session.commit()
            return True
        self._session.commit()
        return False

    def list_cases(self, eval_set_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._eval_case)
            .where(
                self._eval_case.c.eval_set_id == eval_set_id,
                self._eval_case.c.deleted.is_(False),
            )
            .order_by(self._eval_case.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def create_case(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._eval_case.insert()
            .values(**values, deleted=False, created_at=now, updated_at=now)
            .returning(self._eval_case)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_case(self, eval_case_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._eval_case).where(
                self._eval_case.c.id == eval_case_id,
                self._eval_case.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_case(self, eval_case_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._eval_case.update()
            .where(self._eval_case.c.id == eval_case_id, self._eval_case.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get_case(eval_case_id)

    def delete_case(self, eval_case_id: int) -> bool:
        result = self._session.execute(
            self._eval_case.update()
            .where(self._eval_case.c.id == eval_case_id, self._eval_case.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def list_evaluators(
        self,
        page: int,
        page_size: int,
        name: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._evaluator.c.deleted.is_(False)]
        if name:
            conditions.append(self._evaluator.c.name.like(f"%{name}%"))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._evaluator).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._evaluator)
            .where(*conditions)
            .order_by(self._evaluator.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create_evaluator(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._evaluator.insert()
            .values(**values, enabled=True, deleted=False, created_at=now, updated_at=now)
            .returning(self._evaluator)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_evaluator(self, evaluator_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._evaluator).where(
                self._evaluator.c.id == evaluator_id,
                self._evaluator.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_evaluator(self, evaluator_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._evaluator.update()
            .where(self._evaluator.c.id == evaluator_id, self._evaluator.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get_evaluator(evaluator_id)

    def delete_evaluator(self, evaluator_id: int) -> bool:
        result = self._session.execute(
            self._evaluator.update()
            .where(self._evaluator.c.id == evaluator_id, self._evaluator.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def agent_exists(self, agent_id: int) -> bool:
        return (
            self._session.execute(
                sa.select(sa.func.count()).select_from(self._agent).where(
                    self._agent.c.id == agent_id,
                    self._agent.c.enabled.is_(True),
                    self._agent.c.deleted.is_(False),
                )
            ).scalar_one()
            > 0
        )

    def workflow_exists(self, workflow_id: int, flow_type: str) -> bool:
        return (
            self._session.execute(
                sa.select(sa.func.count()).select_from(self._workflow).where(
                    self._workflow.c.id == workflow_id,
                    self._workflow.c.flow_type == flow_type,
                    self._workflow.c.deleted.is_(False),
                )
            ).scalar_one()
            > 0
        )

    def list_experiments(
        self,
        page: int,
        page_size: int,
        name: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._experiment.c.deleted.is_(False)]
        if name:
            conditions.append(self._experiment.c.name.like(f"%{name}%"))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._experiment).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._experiment)
            .where(*conditions)
            .order_by(self._experiment.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create_experiment(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._experiment.insert()
            .values(
                **values,
                status="READY",
                latest_run_id=None,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._experiment)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_experiment(self, experiment_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._experiment).where(
                self._experiment.c.id == experiment_id,
                self._experiment.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_experiment_latest_run(self, experiment_id: int, run_id: int) -> None:
        self._session.execute(
            self._experiment.update()
            .where(self._experiment.c.id == experiment_id, self._experiment.c.deleted.is_(False))
            .values(latest_run_id=run_id, status="RAN", updated_at=datetime.now())
        )
        self._session.commit()

    def create_run(self, experiment_id: int, total_cases: int) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._run.insert()
            .values(
                experiment_id=experiment_id,
                status="RUNNING",
                total_cases=total_cases,
                passed_cases=0,
                failed_cases=0,
                aggregate_score=0.0,
                pass_rate=0.0,
                started_at=now,
                finished_at=None,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._run)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def finish_run(
        self,
        run_id: int,
        status: str,
        passed_cases: int,
        failed_cases: int,
        aggregate_score: float,
        pass_rate: float,
    ) -> dict[str, Any] | None:
        now = datetime.now()
        self._session.execute(
            self._run.update()
            .where(self._run.c.id == run_id, self._run.c.deleted.is_(False))
            .values(
                status=status,
                passed_cases=passed_cases,
                failed_cases=failed_cases,
                aggregate_score=aggregate_score,
                pass_rate=pass_rate,
                finished_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        return self.get_run(run_id)

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._run).where(self._run.c.id == run_id, self._run.c.deleted.is_(False))
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_runs(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._run.c.deleted.is_(False)]
        if status:
            conditions.append(self._run.c.status == status)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._run).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._run)
            .where(*conditions)
            .order_by(self._run.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create_case_result(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._case_result.insert()
            .values(**values, deleted=False, created_at=now, updated_at=now)
            .returning(self._case_result)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get_case_result(self, case_result_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._case_result).where(
                self._case_result.c.id == case_result_id,
                self._case_result.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_case_results(self, run_id: int, status: str | None = None) -> list[dict[str, Any]]:
        conditions: list[ColumnElement[bool]] = [
            self._case_result.c.run_id == run_id,
            self._case_result.c.deleted.is_(False),
        ]
        if status:
            conditions.append(self._case_result.c.status == status)
        rows = self._session.execute(
            sa.select(self._case_result)
            .where(*conditions)
            .order_by(self._case_result.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def _case_count_subquery(self) -> sa.ScalarSelect[int]:
        return (
            sa.select(sa.func.count())
            .select_from(self._eval_case)
            .where(
                self._eval_case.c.eval_set_id == self._eval_set.c.id,
                self._eval_case.c.deleted.is_(False),
            )
            .correlate(self._eval_set)
            .scalar_subquery()
        )
