from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    stripe_api_key: SecretStr = Field(default=...)
    resend_api_key: SecretStr = Field(default=...)
    resend_from_email: str = "onboarding@resend.dev"
    debug: bool = Field(default=False)
    migrator_db_url: SecretStr = Field(default=...)
    db_user: SecretStr = Field(default=...)
    db_password: SecretStr = Field(default=...)
    db_host: SecretStr = Field(default=...)
    db_port: SecretStr = Field(default=...)
    db_name: SecretStr = Field(default=...)
    jwt_secret_key: SecretStr = Field(default=...)
    jwt_algorithm: str = Field(default=...)
    access_token_expire_minutes: int = Field(default=...)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @computed_field
    @property
    def async_database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.db_user.get_secret_value(),
            password=self.db_password.get_secret_value(),
            host=self.db_host.get_secret_value(),
            port=int(self.db_port.get_secret_value()),
            database=self.db_name.get_secret_value(),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
