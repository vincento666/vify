"""knowledge faq embedding

Revision ID: 0015_knowledge_faq_embedding
Revises: 0014_chat_message_tool_calls
Create Date: 2026-06-08 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

from app.core.database import Base
from app.core.schema import ensure_pgvector_extension, register_baseline_tables


revision: str = "0015_knowledge_faq_embedding"
down_revision: str | None = "0014_chat_message_tool_calls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    register_baseline_tables()
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        return
    ensure_pgvector_extension(bind)
    table = Base.metadata.tables["knowledge_faq_embedding"]
    table.create(bind=bind, checkfirst=True)
    for index in table.indexes:
        index.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    register_baseline_tables()
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        return
    table = Base.metadata.tables["knowledge_faq_embedding"]
    for index in table.indexes:
        index.drop(bind=bind, checkfirst=True)
    table.drop(bind=bind, checkfirst=True)
