from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "FishERP"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # CORS - raw comma-separated string; use `cors_origins_list` for the parsed value.
    # Kept as `str` (not `list[str]`) because pydantic-settings JSON-decodes complex
    # env types by default, which breaks a plain comma-separated .env value.
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # Security - JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Security - password policy
    password_min_length: int = 8

    # Security - login rate limiting / account lockout
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_minutes: int = 15
    account_lockout_threshold: int = 5
    account_lockout_minutes: int = 15

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
