from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.core.logging import setup_logging
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.api.v1.api import api_router
from app.core.exception_handlers import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler,
)

# Initialize logging and settings
setup_logging()
settings = get_settings()

app = FastAPI(title="FastAPI Modular Boilerplate", version="1.0.0")

# Request/Response Logging Middleware
from loguru import logger
import time
from starlette.requests import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms"
    )
    return response

# Register centralized exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Mount versioned API
app.include_router(api_router, prefix="/api/v1")

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
