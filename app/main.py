from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db, engine
from .models import Base
from .crud import get_users, create_user

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/users")
async def read_users(db: AsyncSession = Depends(get_db)):
    return await get_users(db)

@app.post("/users")
async def add_user(name: str, email: str, db: AsyncSession = Depends(get_db)):
    return await create_user(db, name, email)
