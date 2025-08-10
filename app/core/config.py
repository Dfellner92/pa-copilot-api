from pydantic import BaseModel
import os

class Settings(BaseModel):
    app_name: str = "PA Copilot API"
    env: str = os.getenv("APP_ENV", "dev")

settings = Settings()
