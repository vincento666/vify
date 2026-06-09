import sqlalchemy as sa
from alembic import op

revision = "0008_agent_tool_policies"
down_revision = "0007_agent_prompt_optimization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _columns("agent")
    if "tool_policies" not in columns:
        op.add_column("agent", sa.Column("tool_policies", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _columns("agent")
    if "tool_policies" in columns:
        op.drop_column("agent", "tool_policies")


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
