import pytest
import sqlalchemy as sa

from app.core.database import check_database_schema


def test_check_database_schema_reports_missing_tables_and_columns() -> None:
    engine = sa.create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                """
                CREATE TABLE provider (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL
                )
                """
            )
        )

    with pytest.raises(RuntimeError) as raised:
        check_database_schema(engine)

    message = str(raised.value)
    assert "missing tables" in message
    assert "model_config" in message
    assert "missing columns" in message
    assert "provider.type" in message
