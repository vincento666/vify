import sqlalchemy as sa
from alembic import op

revision = "0010_agent_evaluation_gate"
down_revision = "0009_agent_retrieval_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "evaluation_gate" not in _columns("agent"):
        op.add_column("agent", sa.Column("evaluation_gate", sa.JSON(), nullable=True))


def downgrade() -> None:
    if "evaluation_gate" in _columns("agent"):
        op.drop_column("agent", "evaluation_gate")


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
