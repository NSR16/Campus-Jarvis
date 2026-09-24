from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Campus JARVIS API"
    app_env: str = "development"
    frontend_origin: str = "http://localhost:5173"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "campus_jarvis"
    database_user: str = "postgres"
    database_password: str = "postgres"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
