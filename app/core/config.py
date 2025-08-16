from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="")
    app_name: str = "PA Copilot API"
    app_env: str = "dev"
    database_url: str 

    secret_key: str   
    jwt_alg: str           
    access_token_expire_minutes: int
    file_storage_dir: str 

settings = Settings()