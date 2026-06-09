import sqlalchemy as sa
from alembic import op

revision = "0009_agent_retrieval_settings"
down_revision = "0008_agent_tool_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _columns("agent")
    if "knowledge_base_ids" not in columns:
        op.add_column("agent", sa.Column("knowledge_base_ids", sa.JSON(), nullable=True))
    if "retrieval_settings" not in columns:
        op.add_column("agent", sa.Column("retrieval_settings", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _columns("agent")
    if "retrieval_settings" in columns:
        op.drop_column("agent", "retrieval_settings")
    if "knowledge_base_ids" in columns:
        op.drop_column("agent", "knowledge_base_ids")


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
