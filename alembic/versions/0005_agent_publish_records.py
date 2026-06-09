import sqlalchemy as sa
from alembic import op

revision = "0005_agent_publish_records"
down_revision = "0004_agent_version_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "agent_publish_record" in _tables():
        return
    op.create_table(
        "agent_publish_record",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
        sa.Column("version_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
        sa.Column("channel_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="PUBLISHED"),
        sa.Column("endpoint", sa.String(500), nullable=False, server_default=""),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_agent_publish_agent_id", "agent_publish_record", ["agent_id"])
    op.create_index("idx_agent_publish_version_id", "agent_publish_record", ["version_id"])


def downgrade() -> None:
    if "agent_publish_record" not in _tables():
        return
    op.drop_index("idx_agent_publish_version_id", table_name="agent_publish_record")
    op.drop_index("idx_agent_publish_agent_id", table_name="agent_publish_record")
    op.drop_table("agent_publish_record")


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())
