from __future__ import annotations

from typing import Mapping

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.modules.customer_assistant.eval.promotion_report import ChatflowDataReadiness


def check_chatflow_data_readiness(
    session: Session,
    *,
    required_sop_chatflow_ids: Mapping[str, int],
    allow_fallback_mock: bool = False,
) -> ChatflowDataReadiness:
    checked_sop_keys = sorted(required_sop_chatflow_ids)
    missing_sop_keys: list[str] = []
    missing_chatflow_ids: list[int] = []

    workflow_table = Base.metadata.tables["workflow"]
    for sop_key, chatflow_id in sorted(required_sop_chatflow_ids.items()):
        row = session.execute(
            sa.select(workflow_table.c.id).where(
                workflow_table.c.id == chatflow_id,
                workflow_table.c.flow_type == "CHATFLOW",
                workflow_table.c.deleted.is_(False),
            )
        ).first()
        if row is None:
            missing_sop_keys.append(sop_key)
            missing_chatflow_ids.append(chatflow_id)

    if missing_sop_keys and allow_fallback_mock:
        return ChatflowDataReadiness(
            status="mock_fallback",
            strategy="explicit_fallback_mock",
            checked_sop_keys=checked_sop_keys,
            missing_sop_keys=missing_sop_keys,
            missing_chatflow_ids=missing_chatflow_ids,
            notes=[
                "Using explicit fallback mock bindings for demo readiness; production Chatflow seed/import is not ready."
            ],
        )

    if missing_sop_keys:
        return ChatflowDataReadiness(
            status="missing_seed_data",
            strategy="database_seed_or_import_required",
            checked_sop_keys=checked_sop_keys,
            missing_sop_keys=missing_sop_keys,
            missing_chatflow_ids=missing_chatflow_ids,
            notes=[
                "Required SOP binding points to missing Chatflow row. Seed or import Chatflow definitions before production readiness."
            ],
        )

    return ChatflowDataReadiness(
        status="ready",
        strategy="database_seed_or_import",
        checked_sop_keys=checked_sop_keys,
    )
