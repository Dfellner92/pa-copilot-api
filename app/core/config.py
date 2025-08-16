from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")
    app_name: str = "PA Copilot API"
    env: str = Field(default="dev", alias="APP_ENV")
    database_url: str = "postgresql://localhost/pa_copilot"

    secret_key: str = "dummy_secret_key_df"
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60
    file_storage_dir: str = "./var/uploads"

settings = Settings()