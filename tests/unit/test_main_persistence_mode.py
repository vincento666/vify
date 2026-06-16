import asyncio
from types import SimpleNamespace

from app import main


def test_lifespan_skips_database_initialise_in_host_and_check_modes(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main, "initialise_database", lambda: calls.append("ddl"))
    monkeypatch.setattr(main, "check_database_schema", lambda: calls.append("check"))

    for mode in ("host",):
        calls.clear()
        monkeypatch.setattr(main, "settings", SimpleNamespace(persistence_mode=mode))

        asyncio.run(_enter_lifespan_once())

        assert calls == []


def test_lifespan_runs_schema_check_in_check_mode_without_database_initialise(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main, "initialise_database", lambda: calls.append("ddl"))
    monkeypatch.setattr(main, "check_database_schema", lambda: calls.append("check"))
    monkeypatch.setattr(main, "settings", SimpleNamespace(persistence_mode="check"))

    asyncio.run(_enter_lifespan_once())

    assert calls == ["check"]


def test_lifespan_initialises_database_in_local_and_test_modes(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main, "initialise_database", lambda: calls.append("ddl"))
    monkeypatch.setattr(main, "check_database_schema", lambda: calls.append("check"))

    for mode in ("local", "test"):
        calls.clear()
        monkeypatch.setattr(main, "settings", SimpleNamespace(persistence_mode=mode))

        asyncio.run(_enter_lifespan_once())

        assert calls == ["ddl"]


async def _enter_lifespan_once() -> None:
    async with main.lifespan(main.app):
        pass
