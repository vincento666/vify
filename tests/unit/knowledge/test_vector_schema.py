import unittest

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.core.database import Base
from app.core.schema import register_baseline_tables


class KnowledgeVectorSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        register_baseline_tables()

    def test_document_chunk_table_shape(self) -> None:
        table = Base.metadata.tables["document_chunk"]

        self.assertEqual(
            {
                "id",
                "document_id",
                "chunk_index",
                "content",
                "token_count",
                "content_hash",
                "metadata",
                "deleted",
                "created_at",
                "updated_at",
            },
            set(table.columns.keys()),
        )
        self.assertIn("idx_document_chunk_document_id", {index.name for index in table.indexes})

    def test_embedding_table_uses_pgvector_cosine_index(self) -> None:
        table = Base.metadata.tables["document_embedding"]
        embedding_type = table.c.embedding.type

        self.assertIsInstance(embedding_type, Vector)
        self.assertEqual(1536, embedding_type.dim)
        self.assertIn("idx_document_embedding_chunk_id", {index.name for index in table.indexes})

        vector_index = next(
            index for index in table.indexes if index.name == "idx_document_embedding_vector_cosine"
        )
        self.assertEqual("ivfflat", vector_index.dialect_options["postgresql"]["using"])
        self.assertEqual(
            {"embedding": "vector_cosine_ops"},
            vector_index.dialect_options["postgresql"]["ops"],
        )
        compiled = str(sa.schema.CreateIndex(vector_index).compile(dialect=postgresql.dialect()))

        self.assertIn("USING ivfflat", compiled)
        self.assertIn("vector_cosine_ops", compiled)


if __name__ == "__main__":
    unittest.main()
