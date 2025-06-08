import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import get_settings
from redis.asyncio import Redis
from typing import AsyncGenerator

settings = get_settings()
DATABASE_URL = settings.database_url

if DATABASE_URL.startswith("postgresql+asyncpg"):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
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


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Get Redis connection for dependency injection.
    Provides a Redis connection with graceful error handling.
    """
    redis_client = None
    try:
        # Create Redis connection from settings
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        redis_client = Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Test the connection
        await redis_client.ping()
        yield redis_client
        
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Warning: Redis connection failed: {e}")
        # Yield None so the calling code can handle the absence of Redis gracefully
        yield None
        
    finally:
        if redis_client:
            try:
                await redis_client.close()
            except Exception as e:
                print(f"Warning: Error closing Redis connection: {e}")
