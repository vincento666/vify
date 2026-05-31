from alembic import op

from app.core.database import Base
from app.core.schema import register_baseline_tables

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

KNOWLEDGE_VECTOR_TABLES = {"document_chunk", "document_embedding"}


def upgrade() -> None:
    register_baseline_tables()
    Base.metadata.create_all(bind=op.get_bind(), tables=_baseline_tables())


def downgrade() -> None:
    register_baseline_tables()
    bind = op.get_bind()
    for table in reversed(_baseline_tables()):
        table.drop(bind=bind, checkfirst=True)


def _baseline_tables() -> list:
    return [table for table in Base.metadata.sorted_tables if table.name not in KNOWLEDGE_VECTOR_TABLES]
