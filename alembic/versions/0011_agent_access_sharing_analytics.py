import sqlalchemy as sa
from alembic import op

revision = "0011_agent_access_sharing_analytics"
down_revision = "0010_agent_evaluation_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _columns("agent")
    for column_name in ("access", "sharing", "catalog", "analytics"):
        if column_name not in columns:
            op.add_column("agent", sa.Column(column_name, sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _columns("agent")
    for column_name in ("analytics", "catalog", "sharing", "access"):
        if column_name in columns:
            op.drop_column("agent", column_name)


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
