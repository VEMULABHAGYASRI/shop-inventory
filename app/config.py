"""Application settings, read from environment variables (or a .env file).

Every setting is prefixed with INVENTORY_ in the environment, e.g. the field
`secret_key` is read from INVENTORY_SECRET_KEY. See .env.example.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INVENTORY_",
        env_file=".env",
        extra="ignore",
    )

    # No default on purpose: the app must not start with a guessable key.
    secret_key: str
    database_url: str = "sqlite:///./data/inventory.db"
    token_expire_minutes: int = 720
    log_level: str = "INFO"
    low_stock_webhook_url: str = ""

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_real(cls, value: str) -> str:
        if value == "change-me" or len(value) < 16:
            raise ValueError(
                "INVENTORY_SECRET_KEY must be a random string of at least 16 "
                "characters. See .env.example for how to generate one."
            )
        return value
