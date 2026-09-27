from dataclasses import dataclass

from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return make_conninfo(
            host=self.host,
            port=self.port,
            dbname=self.name,
            user=self.user,
            password=self.password,
        )


def get_database_config(settings: Settings) -> DatabaseConfig:
    """Translate application settings into database connection configuration."""
    return DatabaseConfig(
        host=settings.database_host,
        port=settings.database_port,
        name=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    )


def create_connection_pool(settings: Settings) -> AsyncConnectionPool:
    """Create, but do not open, the application's asynchronous connection pool."""
    database_config = get_database_config(settings)
    return AsyncConnectionPool(
        conninfo=database_config.dsn,
        min_size=1,
        max_size=10,
        timeout=30.0,
        open=False,
    )
