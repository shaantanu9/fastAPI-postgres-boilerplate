from fastapi import FastAPI
from app.core.logging import setup_logging
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.api.v1.endpoints import user as user_endpoints

# Initialize logging and settings
setup_logging()
settings = get_settings()

app = FastAPI(title="FastAPI Modular Boilerplate", version="1.0.0")

# Include API routers
app.include_router(user_endpoints.router, prefix="/api/v1", tags=["users"])

# Startup event: create tables if they don't exist
@app.on_event("startup")
async def on_startup():
    import logging
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logging.info("Database tables created/verified.")
    except Exception as e:
        logging.error(f"[Startup Error] Could not create tables: {e}")
        raise

# (Optional) Add root endpoint or health check
@app.get("/")
def root():
    return {"status": "ok", "message": "Welcome to the FastAPI Modular Boilerplate!"}

# If running directly, launch with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
