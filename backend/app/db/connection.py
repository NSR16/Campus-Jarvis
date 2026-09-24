from dataclasses import dataclass

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
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
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
