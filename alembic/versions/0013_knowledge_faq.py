"""knowledge faq

Revision ID: 0013_knowledge_faq
Revises: 0012_evaluation_evaluator_version_binding
Create Date: 2026-06-03 17:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0013_knowledge_faq"
down_revision: str | None = "0012_evaluation_evaluator_version_binding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "knowledge_faq" not in _tables():
        op.create_table(
            "knowledge_faq",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
            sa.Column("knowledge_base_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("answer", sa.Text(), nullable=False),
            sa.Column("alternative_questions", sa.JSON(), nullable=True),
            sa.Column("keywords", sa.JSON(), nullable=True),
            sa.Column("category", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="manual"),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    indexes = _indexes("knowledge_faq")
    if "idx_knowledge_faq_knowledge_base_id" not in indexes:
        op.create_index("idx_knowledge_faq_knowledge_base_id", "knowledge_faq", ["knowledge_base_id"])
    if "idx_knowledge_faq_enabled" not in indexes:
        op.create_index("idx_knowledge_faq_enabled", "knowledge_faq", ["enabled"])


def downgrade() -> None:
    if "knowledge_faq" not in _tables():
        return
    indexes = _indexes("knowledge_faq")
    if "idx_knowledge_faq_enabled" in indexes:
        op.drop_index("idx_knowledge_faq_enabled", table_name="knowledge_faq")
    if "idx_knowledge_faq_knowledge_base_id" in indexes:
        op.drop_index("idx_knowledge_faq_knowledge_base_id", table_name="knowledge_faq")
    op.drop_table("knowledge_faq")


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    if table_name not in _tables():
        return set()
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
