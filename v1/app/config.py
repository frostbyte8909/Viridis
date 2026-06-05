from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/viridis"
    redis_url: str = "redis://localhost:6379/0"
    admin_token: str = "dev_admin_token"
    server_pepper: str = "dev_server_pepper"
    mode: str = "normal"  # normal, degraded, maintenance

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
