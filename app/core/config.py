from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str
    jwt_secret_token: str  # Loaded from .env
    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
