"""Application settings.

Every setting has a sensible default, so the app runs with no configuration.
To change one, set an environment variable (prefixed INVENTORY_) or put it in
an optional .env file. See .env.example.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INVENTORY_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/inventory.db"
    session_expire_minutes: int = 720  # 12 hours = one shop day
    log_level: str = "INFO"
    low_stock_webhook_url: str = ""
