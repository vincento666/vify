import sqlalchemy as sa
from alembic import op

revision = "0003_agent_chat_entry_fields"
down_revision = "0002_knowledge_vector_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _agent_columns()
    if "opening_message" not in columns:
        op.add_column("agent", sa.Column("opening_message", sa.Text(), nullable=True))
    if "suggested_questions" not in columns:
        op.add_column("agent", sa.Column("suggested_questions", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _agent_columns()
    if "suggested_questions" in columns:
        op.drop_column("agent", "suggested_questions")
    if "opening_message" in columns:
        op.drop_column("agent", "opening_message")


def _agent_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("agent")}
