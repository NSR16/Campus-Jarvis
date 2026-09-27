from pathlib import Path

import pytest
from fastapi import FastAPI
from psycopg.conninfo import conninfo_to_dict

from app.core.config import Settings
from app.db import connection, schema
from app.main import lifespan


def test_database_config_builds_escaped_conninfo() -> None:
    settings = Settings(
        database_host="db.example.test",
        database_port=5544,
        database_name="campus data",
        database_user="jarvis user",
        database_password="p@ss word",
    )

    config = connection.get_database_config(settings)
    parsed = conninfo_to_dict(config.dsn)

    assert parsed == {
        "host": "db.example.test",
        "port": "5544",
        "dbname": "campus data",
        "user": "jarvis user",
        "password": "p@ss word",
    }


def test_create_connection_pool_is_configured_but_not_opened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakePool:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(connection, "AsyncConnectionPool", FakePool)

    connection.create_connection_pool(Settings(database_password="pool-secret"))

    assert conninfo_to_dict(str(captured["conninfo"]))["password"] == "pool-secret"
    assert captured["min_size"] == 1
    assert captured["max_size"] == 10
    assert captured["timeout"] == 30.0
    assert captured["open"] is False


@pytest.mark.anyio
async def test_schema_initializer_executes_checked_in_sql() -> None:
    class FakeConnection:
        query: str | None = None
        prepare: bool | None = None

        async def execute(self, query: str, *, prepare: bool) -> None:
            self.query = query
            self.prepare = prepare

    fake_connection = FakeConnection()

    await schema.initialize_schema(fake_connection)  # type: ignore[arg-type]

    assert fake_connection.query == Path(schema.SCHEMA_FILE).read_text(encoding="utf-8")
    assert fake_connection.prepare is False
    assert "CREATE EXTENSION IF NOT EXISTS vector" in fake_connection.query
    assert "VECTOR(768) NOT NULL" in fake_connection.query


@pytest.mark.anyio
async def test_lifespan_opens_and_closes_connection_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePool:
        opened = False
        closed = False

        async def open(self, *, wait: bool) -> None:
            assert wait is True
            self.opened = True

        async def close(self) -> None:
            self.closed = True

    pool = FakePool()
    monkeypatch.setattr("app.main.create_connection_pool", lambda settings: pool)
    application = FastAPI()

    async with lifespan(application):
        assert application.state.db_pool is pool
        assert pool.opened is True
        assert pool.closed is False

    assert pool.closed is True