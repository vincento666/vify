import sqlalchemy as sa
from alembic import op

revision = "0007_agent_prompt_optimization"
down_revision = "0006_agent_memory_variables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "agent_prompt_optimization" in _tables():
        return
    op.create_table(
        "agent_prompt_optimization",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("optimized_prompt", sa.Text(), nullable=False),
        sa.Column("model_config_id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
        sa.Column("audit", sa.JSON(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_agent_prompt_optimization_agent_id", "agent_prompt_optimization", ["agent_id"])


def downgrade() -> None:
    if "agent_prompt_optimization" not in _tables():
        return
    op.drop_index("idx_agent_prompt_optimization_agent_id", table_name="agent_prompt_optimization")
    op.drop_table("agent_prompt_optimization")


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())
