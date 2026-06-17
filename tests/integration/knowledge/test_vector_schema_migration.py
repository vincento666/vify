import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from tests.support.mysql import configured_mysql8_database_url, mysql8_database_url


class KnowledgeVectorMigrationTest(unittest.TestCase):
    def test_upgrade_head_creates_mysql8_compatible_knowledge_tables_without_pgvector(self) -> None:
        with mysql8_database_url("knowledge_vector_schema") as database_url:
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)

            with configured_mysql8_database_url(database_url):
                command.upgrade(config, "head")

            engine = create_engine(database_url)
            try:
                inspector = inspect(engine)
                table_names = set(inspector.get_table_names())
                chunk_columns = {column["name"] for column in inspector.get_columns("document_chunk")}
                chunk_indexes = {index["name"] for index in inspector.get_indexes("document_chunk")}
            finally:
                engine.dispose()

            self.assertIn("document_chunk", table_names)
            self.assertNotIn("document_embedding", table_names)
            self.assertNotIn("knowledge_faq_embedding", table_names)
            self.assertIn("document_id", chunk_columns)
            self.assertIn("idx_document_chunk_document_id", chunk_indexes)


if __name__ == "__main__":
    unittest.main()
