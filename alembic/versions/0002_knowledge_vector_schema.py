from alembic import op

from app.core.database import Base
from app.core.schema import ensure_pgvector_extension, register_baseline_tables

revision = "0002_knowledge_vector_schema"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

KNOWLEDGE_VECTOR_TABLES = ("document_chunk", "document_embedding")


def upgrade() -> None:
    register_baseline_tables()
    bind = op.get_bind()
    ensure_pgvector_extension(bind)
    for table_name in KNOWLEDGE_VECTOR_TABLES:
        table = Base.metadata.tables[table_name]
        table.create(bind=bind, checkfirst=True)
        for index in table.indexes:
            index.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    register_baseline_tables()
    bind = op.get_bind()
    for table_name in reversed(KNOWLEDGE_VECTOR_TABLES):
        table = Base.metadata.tables[table_name]
        for index in table.indexes:
            index.drop(bind=bind, checkfirst=True)
        table.drop(bind=bind, checkfirst=True)
