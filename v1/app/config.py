from typing import Literal
from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: PostgresDsn
    redis_url: RedisDsn
    admin_token: str
    server_pepper: str
    mode: Literal["normal", "degraded", "maintenance"] = "normal"
    trusted_proxies: list[str] = []
    audit_retention_days: int = 0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
