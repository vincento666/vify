import sqlalchemy as sa
from alembic import op

revision = "0012_evaluation_evaluator_version_binding"
down_revision = "0011_agent_access_sharing_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "evaluator_version_ids" not in _columns("evaluation_experiment"):
        op.add_column("evaluation_experiment", sa.Column("evaluator_version_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    if "evaluator_version_ids" in _columns("evaluation_experiment"):
        op.drop_column("evaluation_experiment", "evaluator_version_ids")


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
