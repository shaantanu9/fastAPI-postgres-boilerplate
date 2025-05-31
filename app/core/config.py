from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

class Settings(BaseSettings):
    # Database configuration
    database_url: str
    database_url_without_async: str
    
    # JWT configuration
    jwt_secret_token: str  # Loaded from .env
    
    # Procrastinate configuration
    procrastinate_schema: str = "procrastinate"
    procrastinate_app_name: str = "FastAPI App"
    procrastinate_worker_concurrency: int = 10
    procrastinate_log_level: str = "INFO"
    
    # PostgreSQL connection for Procrastinate (sync) - will be extracted from database_url
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_database: Optional[str] = None
    
    # Task queue configuration
    task_queue_max_retries: int = 3
    task_queue_retry_delay: int = 60  # seconds
    
    class Config:
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse database URL to extract connection details for Procrastinate
        if self.database_url_without_async:
            parsed = urlparse(self.database_url_without_async)
            self.postgres_host = parsed.hostname or "localhost"
            self.postgres_port = parsed.port or 5432
            self.postgres_user = parsed.username or "postgres"
            self.postgres_password = parsed.password or "password"
            self.postgres_database = parsed.path.lstrip('/') or "fastapi_db"
    
    @property
    def procrastinate_connection_string(self) -> str:
        """Get PostgreSQL connection string for Procrastinate (sync driver)"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

@lru_cache
def get_settings():
    return Settings()
