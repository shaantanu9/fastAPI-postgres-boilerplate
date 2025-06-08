import contextlib
from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()
DATABASE_URL = settings.database_url

if DATABASE_URL.startswith("postgresql+asyncpg"):
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )

    async def get_db():
        async with AsyncSessionLocal() as session:
            yield session
else:
    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(bind=engine)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


async def get_redis() -> AsyncGenerator[Redis]:
    """Get Redis connection for dependency injection.
    Provides a Redis connection with graceful error handling.
    """
    redis_client = None
    try:
        # Create Redis connection from settings
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30,
        )

        # Test the connection
        await redis_client.ping()
        yield redis_client

    except Exception:
        # Log the error but don't fail the request
        # Yield None so the calling code can handle the absence of Redis gracefully
        yield None

    finally:
        if redis_client:
            with contextlib.suppress(Exception):
                await redis_client.close()
