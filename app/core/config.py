from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings


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

    # Settings for observability system (compatible with main.py)
    PROJECT_NAME: str = "FastAPI PostgreSQL Application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Health check settings
    HEALTH_CHECK_ENABLED: bool = True

    # File management settings
    FILE_STORAGE_TYPE: str = "local"  # local, s3, azure, gcp
    FILE_UPLOAD_MAX_SIZE: int = 100 * 1024 * 1024  # 100MB
    FILE_STORAGE_PATH: str = "./uploads"

    # S3 settings (for file storage)
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_S3_BUCKET: str | None = None
    AWS_S3_REGION: str = "us-east-1"
    AWS_S3_ENDPOINT_URL: str | None = None

    # Procrastinate configuration
    procrastinate_schema: str = "procrastinate"
    procrastinate_app_name: str = "FastAPI App"
    procrastinate_worker_concurrency: int = 10
    procrastinate_log_level: str = "INFO"

    # PostgreSQL connection for Procrastinate (sync) - will be extracted from database_url
    postgres_host: str | None = None
    postgres_port: int | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_database: str | None = None

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

    # AWS SES Settings
    AWS_REGION: str = "us-east-1"
    SES_CONFIGURATION_SET: str | None = None
    EMAIL_FROM_DOMAIN: str | None = None
    EMAIL_FROM_EMAIL: str = "noreply@yourapp.com"
    EMAIL_FROM_NAME: str = "Your App"

    # Email provider selection
    EMAIL_PROVIDER: str = "ses"  # 'ses' or 'smtp'

    # Frontend URLs for SaaS
    frontend_url: str = "http://localhost:3000"
    support_email: str = "support@yourapp.com"
    app_name: str = "Your SaaS App"

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Parse database URL to extract connection details for Procrastinate
        if self.database_url_without_async:
            parsed = urlparse(self.database_url_without_async)
            self.postgres_host = parsed.hostname or "localhost"
            self.postgres_port = parsed.port or 5432
            self.postgres_user = parsed.username or "postgres"
            self.postgres_password = parsed.password or "password"
            self.postgres_database = parsed.path.lstrip("/") or "fastapi_db"

    @property
    def procrastinate_connection_string(self) -> str:
        """Get PostgreSQL connection string for Procrastinate (sync driver)."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"


@lru_cache
def get_settings():
    return Settings()


# Export settings instance for direct import
settings = get_settings()


def validate_aws_configuration() -> dict:
    """Validate AWS configuration and return status information.

    Returns:
        Dict with validation results and helpful debugging info

    """
    validation_result = {
        "aws_credentials_configured": False,
        "aws_region_configured": False,
        "email_settings_configured": False,
        "issues": [],
        "recommendations": [],
    }

    # Check AWS credentials
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        validation_result["aws_credentials_configured"] = True
    else:
        validation_result["issues"].append(
            "AWS credentials not configured in environment variables",
        )
        validation_result["recommendations"].append(
            "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables",
        )

    # Check AWS region
    if settings.AWS_REGION:
        validation_result["aws_region_configured"] = True
    else:
        validation_result["issues"].append("AWS region not configured")
        validation_result["recommendations"].append(
            "Set AWS_REGION environment variable (default: us-east-1)",
        )

    # Check email settings
    if settings.EMAIL_FROM_EMAIL and settings.EMAIL_FROM_NAME:
        validation_result["email_settings_configured"] = True
    else:
        validation_result["issues"].append("Email from settings not configured")
        validation_result["recommendations"].append(
            "Set EMAIL_FROM_EMAIL and EMAIL_FROM_NAME in settings",
        )

    # Overall status
    validation_result["is_valid"] = (
        validation_result["aws_credentials_configured"]
        and validation_result["aws_region_configured"]
        and validation_result["email_settings_configured"]
    )

    return validation_result


def get_debug_info() -> dict:
    """Get debugging information about current configuration."""
    import os

    return {
        "aws_access_key_configured": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "aws_secret_key_configured": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
        "aws_region": settings.AWS_REGION,
        "email_from_email": settings.EMAIL_FROM_EMAIL,
        "email_from_name": settings.EMAIL_FROM_NAME,
        "email_provider": settings.EMAIL_PROVIDER,
        "ses_configuration_set": settings.SES_CONFIGURATION_SET,
        "email_from_domain": settings.EMAIL_FROM_DOMAIN,
        "environment_variables_set": {
            "AWS_ACCESS_KEY_ID": bool(os.getenv("AWS_ACCESS_KEY_ID")),
            "AWS_SECRET_ACCESS_KEY": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
            "AWS_REGION": bool(os.getenv("AWS_REGION")),
            "EMAIL_FROM_EMAIL": bool(os.getenv("EMAIL_FROM_EMAIL")),
            "EMAIL_FROM_NAME": bool(os.getenv("EMAIL_FROM_NAME")),
        },
    }
