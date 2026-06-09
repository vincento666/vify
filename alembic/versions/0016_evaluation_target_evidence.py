"""evaluation target evidence

Revision ID: 0016_evaluation_target_evidence
Revises: 0015_knowledge_faq_embedding
Create Date: 2026-06-08 13:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_evaluation_target_evidence"
down_revision: str | None = "0015_knowledge_faq_embedding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = _columns("evaluation_case_result")
    additions = [
        ("target_type", sa.Column("target_type", sa.String(length=30), nullable=True)),
        ("target_run_id", sa.Column("target_run_id", sa.BigInteger(), nullable=True)),
        ("target_status", sa.Column("target_status", sa.String(length=30), nullable=True)),
        ("target_debug_url", sa.Column("target_debug_url", sa.String(length=500), nullable=True)),
        ("target_evidence_summary", sa.Column("target_evidence_summary", sa.JSON(), nullable=True)),
    ]
    for column_name, column in additions:
        if column_name not in columns:
            op.add_column("evaluation_case_result", column)


def downgrade() -> None:
    columns = _columns("evaluation_case_result")
    for column_name in (
        "target_evidence_summary",
        "target_debug_url",
        "target_status",
        "target_run_id",
        "target_type",
    ):
        if column_name in columns:
            op.drop_column("evaluation_case_result", column_name)


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
