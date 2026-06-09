import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


class KnowledgeVectorMigrationTest(unittest.TestCase):
    def test_upgrade_head_creates_vector_tables_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "hify.db"
            database_url = f"sqlite:///{db_path}"
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)

            command.upgrade(config, "head")

            engine = create_engine(database_url)
            inspector = inspect(engine)
            table_names = set(inspector.get_table_names())
            chunk_columns = {column["name"] for column in inspector.get_columns("document_chunk")}
            embedding_columns = {
                column["name"] for column in inspector.get_columns("document_embedding")
            }
            faq_embedding_columns = {
                column["name"] for column in inspector.get_columns("knowledge_faq_embedding")
            }
            chunk_indexes = {index["name"] for index in inspector.get_indexes("document_chunk")}
            embedding_indexes = {
                index["name"] for index in inspector.get_indexes("document_embedding")
            }
            faq_embedding_indexes = {
                index["name"] for index in inspector.get_indexes("knowledge_faq_embedding")
            }

            self.assertIn("document_chunk", table_names)
            self.assertIn("document_embedding", table_names)
            self.assertIn("knowledge_faq_embedding", table_names)
            self.assertIn("document_id", chunk_columns)
            self.assertIn("chunk_id", embedding_columns)
            self.assertIn("embedding", embedding_columns)
            self.assertIn("faq_id", faq_embedding_columns)
            self.assertIn("embedding", faq_embedding_columns)
            self.assertIn("idx_document_chunk_document_id", chunk_indexes)
            self.assertIn("idx_document_embedding_chunk_id", embedding_indexes)
            self.assertIn("idx_document_embedding_vector_cosine", embedding_indexes)
            self.assertIn("idx_knowledge_faq_embedding_faq_id", faq_embedding_indexes)
            self.assertIn("idx_knowledge_faq_embedding_vector_cosine", faq_embedding_indexes)


if __name__ == "__main__":
    unittest.main()
