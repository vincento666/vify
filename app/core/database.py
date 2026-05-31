from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def make_engine(database_url: str, echo: bool = False) -> Engine:
    return create_engine(database_url, echo=echo, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


def get_session_factory() -> sessionmaker[Session]:
    return make_session_factory(get_engine())


def initialise_database() -> None:
    from app.core.schema import ensure_pgvector_extension, register_baseline_tables

    register_baseline_tables()
    engine = get_engine()
    ensure_pgvector_extension(engine)
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session]:
    with get_session_factory()() as session:
        yield session
