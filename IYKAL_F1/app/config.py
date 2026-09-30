"""
تنظیمات مرکزی پروژه با pydantic-settings
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # --- Meta / Instagram ---
    ig_access_token: str = ""
    ig_user_id: str = ""
    meta_app_secret: str = ""
    webhook_verify_token: str = "icall_secret_token_2026"

    # --- Database ---
    db_user: str = "postgres"
    db_password: str = "1363973126"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "icall_db"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- App ---
    app_env: str = "development"
    debug: bool = True
    api_key: str = "dev_api_key_change_me_in_prod"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()