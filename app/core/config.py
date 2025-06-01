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
    
    # Application metadata
    APP_NAME: str = "FastAPI PostgreSQL Application"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "Enterprise FastAPI application with PostgreSQL"
    ENVIRONMENT: str = "development"
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Health check settings
    HEALTH_CHECK_ENABLED: bool = True
    
    # File management settings
    FILE_STORAGE_TYPE: str = "local"  # local, s3, azure, gcp
    FILE_UPLOAD_MAX_SIZE: int = 100 * 1024 * 1024  # 100MB
    FILE_STORAGE_PATH: str = "./uploads"
    
    # S3 settings (for file storage)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: str = "us-east-1"
    AWS_S3_ENDPOINT_URL: Optional[str] = None
    
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
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_email: str = ""
    smtp_from_name: str = "Your App"
    email_secret_key: str = "your-email-secret-key-change-this"
    
    # Frontend URLs for SaaS
    frontend_url: str = "http://localhost:3000"
    support_email: str = "support@yourapp.com"
    app_name: str = "Your SaaS App"
    
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
