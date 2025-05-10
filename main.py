from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, engine
from app import crud, models
from app.schemas import UserCreate, UserRead
import uvicorn

# Create FastAPI app instance
app = FastAPI()

# Startup event: Create tables if they don't exist
@app.on_event("startup")
async def startup():
    # This runs at server startup and ensures your tables are present in the database.
    # If you see DB connection errors here, check your DATABASE_URL and DB server status.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
    except Exception as e:
        print(f"[Startup Error] Could not create tables: {e}")
        raise

# Endpoint: List all users
@app.get("/users", response_model=list[UserRead])
async def read_users(db: AsyncSession = Depends(get_db)):
    # Debug: You can add print/logging here to inspect DB session or results
    users = await crud.get_users(db)
    return users

# Endpoint: Create a new user
@app.post("/users", response_model=UserRead)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Debug: Print incoming user data if needed
    return await crud.create_user(db, name=user.name, email=user.email)

if __name__ == "__main__":
    # Debug: This will only run if you execute `python main.py` directly
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
