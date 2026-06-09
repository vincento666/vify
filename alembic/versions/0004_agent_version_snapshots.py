import sqlalchemy as sa
from alembic import op

revision = "0004_agent_version_snapshots"
down_revision = "0003_agent_chat_entry_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "agent_version" in _tables():
        return
    op.create_table(
        "agent_version",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False, server_default=""),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("released", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("agent_id", "version_no", name="idx_agent_version_agent_no"),
    )
    op.create_index("idx_agent_version_agent_id", "agent_version", ["agent_id"])


def downgrade() -> None:
    if "agent_version" not in _tables():
        return
    op.drop_index("idx_agent_version_agent_id", table_name="agent_version")
    op.drop_table("agent_version")


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())
