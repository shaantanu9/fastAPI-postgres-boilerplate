import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError


# Custom exception for application-specific errors
class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# Handler for AppException
async def app_exception_handler(request: Request, exc: AppException):
    logging.error(f"AppException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# Handler for HTTPException
async def http_exception_handler(request: Request, exc: HTTPException):
    logging.error(f"HTTPException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Handler for SQLAlchemy errors
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logging.error(f"SQLAlchemyError: {exc!s}")
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred."},
    )


# Handler for unhandled exceptions
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc!s}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
