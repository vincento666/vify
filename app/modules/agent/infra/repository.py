from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables

register_baseline_tables()


class AgentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._agent = Base.metadata.tables["agent"]
        self._agent_tool = Base.metadata.tables["agent_tool"]
        self._mcp_server = Base.metadata.tables["mcp_server"]
        self._agent_version = Base.metadata.tables["agent_version"]
        self._agent_publish_record = Base.metadata.tables["agent_publish_record"]
        self._agent_prompt_optimization = Base.metadata.tables["agent_prompt_optimization"]
        self._evaluation_experiment = Base.metadata.tables["evaluation_experiment"]
        self._evaluation_run = Base.metadata.tables["evaluation_run"]

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        payload = {
            **values,
            "enabled": True,
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }
        row = insert_and_fetch(self._session, self._agent, payload)
        self._session.commit()
        return row

    def get(self, agent_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._agent).where(
                self._agent.c.id == agent_id,
                self._agent.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def find_default_live_llm_agent(self) -> dict[str, Any] | None:
        model_config = Base.metadata.tables["model_config"]
        provider = Base.metadata.tables["provider"]
        row = self._session.execute(
            sa.select(self._agent)
            .select_from(
                self._agent.join(
                    model_config,
                    model_config.c.id == self._agent.c.model_config_id,
                ).join(provider, provider.c.id == model_config.c.provider_id)
            )
            .where(
                self._agent.c.enabled.is_(True),
                self._agent.c.deleted.is_(False),
                model_config.c.enabled.is_(True),
                model_config.c.deleted.is_(False),
                provider.c.enabled.is_(True),
                provider.c.deleted.is_(False),
                provider.c.base_url.not_like("mock://%"),
            )
            .order_by(self._agent.c.updated_at.desc(), self._agent.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def find_live_llm_agent_by_name(self, name: str) -> dict[str, Any] | None:
        model_config = Base.metadata.tables["model_config"]
        provider = Base.metadata.tables["provider"]
        row = self._session.execute(
            sa.select(self._agent)
            .select_from(
                self._agent.join(
                    model_config,
                    model_config.c.id == self._agent.c.model_config_id,
                ).join(provider, provider.c.id == model_config.c.provider_id)
            )
            .where(
                self._agent.c.name == name,
                self._agent.c.enabled.is_(True),
                self._agent.c.deleted.is_(False),
                model_config.c.enabled.is_(True),
                model_config.c.deleted.is_(False),
                provider.c.enabled.is_(True),
                provider.c.deleted.is_(False),
                provider.c.base_url.not_like("mock://%"),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_page(
        self,
        page: int,
        page_size: int,
        enabled: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._agent.c.deleted.is_(False)]
        if enabled is not None:
            conditions.append(self._agent.c.enabled.is_(enabled))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._agent).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._agent)
            .where(*conditions)
            .order_by(self._agent.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def update(self, agent_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._agent.update()
            .where(self._agent.c.id == agent_id, self._agent.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get(agent_id)

    def delete(self, agent_id: int) -> bool:
        result = self._session.execute(
            self._agent.update()
            .where(self._agent.c.id == agent_id, self._agent.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def list_tool_ids(self, agent_id: int) -> list[int]:
        rows = self._session.execute(
            sa.select(self._agent_tool.c.mcp_server_id)
            .where(self._agent_tool.c.agent_id == agent_id)
            .order_by(self._agent_tool.c.mcp_server_id.asc())
        ).all()
        return [int(row[0]) for row in rows]

    def tool_count(self, agent_id: int) -> int:
        return int(
            self._session.execute(
                sa.select(sa.func.count())
                .select_from(self._agent_tool)
                .where(self._agent_tool.c.agent_id == agent_id)
            ).scalar_one()
        )

    def list_available_tool_ids(self, tool_ids: list[int]) -> list[int]:
        if not tool_ids:
            return []
        rows = self._session.execute(
            sa.select(self._mcp_server.c.id).where(
                self._mcp_server.c.id.in_(tool_ids),
                self._mcp_server.c.enabled.is_(True),
                self._mcp_server.c.deleted.is_(False),
            )
        ).all()
        return [int(row[0]) for row in rows]

    def replace_tool_bindings(self, agent_id: int, tool_ids: list[int]) -> None:
        now = datetime.now()
        self._session.execute(self._agent_tool.delete().where(self._agent_tool.c.agent_id == agent_id))
        if tool_ids:
            self._session.execute(
                self._agent_tool.insert(),
                [
                    {
                        "agent_id": agent_id,
                        "mcp_server_id": tool_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                    for tool_id in tool_ids
                ],
            )
        self._session.commit()

    def create_version(self, agent_id: int, name: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        version_no = self.next_version_no(agent_id)
        row = insert_and_fetch(
            self._session,
            self._agent_version,
            {
                "agent_id": agent_id,
                "version_no": version_no,
                "name": name,
                "snapshot": snapshot,
                "released": False,
                "released_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def next_version_no(self, agent_id: int) -> int:
        current = self._session.execute(
            sa.select(sa.func.max(self._agent_version.c.version_no)).where(
                self._agent_version.c.agent_id == agent_id,
                self._agent_version.c.deleted.is_(False),
            )
        ).scalar_one()
        return int(current or 0) + 1

    def list_versions(self, agent_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._agent_version)
            .where(
                self._agent_version.c.agent_id == agent_id,
                self._agent_version.c.deleted.is_(False),
            )
            .order_by(self._agent_version.c.version_no.desc(), self._agent_version.c.id.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_version(self, agent_id: int, version_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._agent_version).where(
                self._agent_version.c.id == version_id,
                self._agent_version.c.agent_id == agent_id,
                self._agent_version.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def release_version(self, agent_id: int, version_id: int) -> dict[str, Any] | None:
        if self.get_version(agent_id, version_id) is None:
            return None
        now = datetime.now()
        self._session.execute(
            self._agent_version.update()
            .where(
                self._agent_version.c.agent_id == agent_id,
                self._agent_version.c.deleted.is_(False),
            )
            .values(released=False, released_at=None, updated_at=now)
        )
        self._session.execute(
            self._agent_version.update()
            .where(
                self._agent_version.c.id == version_id,
                self._agent_version.c.agent_id == agent_id,
                self._agent_version.c.deleted.is_(False),
            )
            .values(released=True, released_at=now, updated_at=now)
        )
        self._session.commit()
        return self.get_version(agent_id, version_id)

    def create_publish_record(
        self,
        agent_id: int,
        version_id: int,
        channel_type: str,
        endpoint: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._agent_publish_record,
            {
                "agent_id": agent_id,
                "version_id": version_id,
                "channel_type": channel_type,
                "status": "PUBLISHED",
                "endpoint": endpoint,
                "config": config or {},
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_publish_records(self, agent_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._agent_publish_record)
            .where(
                self._agent_publish_record.c.agent_id == agent_id,
                self._agent_publish_record.c.deleted.is_(False),
            )
            .order_by(self._agent_publish_record.c.id.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_publish_record(self, agent_id: int, publish_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._agent_publish_record).where(
                self._agent_publish_record.c.id == publish_id,
                self._agent_publish_record.c.agent_id == agent_id,
                self._agent_publish_record.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def unpublish_record(self, agent_id: int, publish_id: int) -> dict[str, Any] | None:
        if self.get_publish_record(agent_id, publish_id) is None:
            return None
        self._session.execute(
            self._agent_publish_record.update()
            .where(
                self._agent_publish_record.c.id == publish_id,
                self._agent_publish_record.c.agent_id == agent_id,
                self._agent_publish_record.c.deleted.is_(False),
            )
            .values(status="UNPUBLISHED", updated_at=datetime.now())
        )
        self._session.commit()
        return self.get_publish_record(agent_id, publish_id)

    def create_prompt_optimization(
        self,
        agent_id: int,
        original_prompt: str,
        instruction: str,
        optimized_prompt: str,
        model_config_id: int,
        audit: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._agent_prompt_optimization,
            {
                "agent_id": agent_id,
                "original_prompt": original_prompt,
                "instruction": instruction,
                "optimized_prompt": optimized_prompt,
                "model_config_id": model_config_id,
                "audit": audit,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_prompt_optimizations(self, agent_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._agent_prompt_optimization)
            .where(
                self._agent_prompt_optimization.c.agent_id == agent_id,
                self._agent_prompt_optimization.c.deleted.is_(False),
            )
            .order_by(self._agent_prompt_optimization.c.id.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_latest_evaluation_run(self, experiment_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._evaluation_run)
            .select_from(
                self._evaluation_run.join(
                    self._evaluation_experiment,
                    self._evaluation_experiment.c.latest_run_id == self._evaluation_run.c.id,
                )
            )
            .where(
                self._evaluation_experiment.c.id == experiment_id,
                self._evaluation_experiment.c.deleted.is_(False),
                self._evaluation_run.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None
