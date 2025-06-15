import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
import jwt
from typing import AsyncGenerator, Generator
import logging
from loguru import logger

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.config import get_settings

settings = get_settings()

# Configure logging for tests
@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests."""
    # Remove existing handlers
    logger.remove()
    
    # Add test-specific handler
    logger.add(
        "tests/test.log",
        rotation="1 MB",
        retention="1 week",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
        backtrace=True,
        diagnose=True
    )
    
    # Also log to console for immediate feedback
    logger.add(
        sys.stderr,
        format="{time:HH:mm:ss} | {level} | {message}",
        level="INFO",
        colorize=True
    )

@pytest.fixture(scope="session")
def anyio_backend():
    """Specify the async backend for pytest-asyncio."""
    return "asyncio"

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async client for testing."""
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

@pytest.fixture
def make_token() -> Generator[callable, None, None]:
    """Create a JWT token for testing."""
    def _make_token(user_id: str = "testuser") -> str:
        return jwt.encode(
            {"sub": user_id},
            settings.jwt_secret_token,
            algorithm="HS256"
        )
    yield _make_token

@pytest.fixture
async def authenticated_client(client: AsyncClient, make_token) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated client for testing."""
    token = make_token()
    client.headers["Authorization"] = f"Bearer {token}"
    yield client 