import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import get_settings

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
