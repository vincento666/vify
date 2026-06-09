import sqlalchemy as sa
from alembic import op

revision = "0006_agent_memory_variables"
down_revision = "0005_agent_publish_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _columns("agent")
    if "variables" not in columns:
        op.add_column("agent", sa.Column("variables", sa.JSON(), nullable=True))
    if "memory" not in columns:
        op.add_column("agent", sa.Column("memory", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _columns("agent")
    if "memory" in columns:
        op.drop_column("agent", "memory")
    if "variables" in columns:
        op.drop_column("agent", "variables")


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
