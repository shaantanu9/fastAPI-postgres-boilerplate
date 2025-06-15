import os

import typer
from rich.console import Console
from rich.prompt import Prompt

app = typer.Typer(help="FastAPI Boilerplate Project Scaffold CLI")
console = Console()

# --- Minimal templates for key files ---
TEMPLATES = {
    "app/main.py": """from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.exception_handlers import add_exception_handlers

app = FastAPI(title="FastAPI Boilerplate")
add_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"message": "OK"}
""",
    "app/api/v1/api.py": """from fastapi import APIRouter
from app.api.v1.endpoints import user

api_router = APIRouter()
api_router.include_router(user.router, prefix="/users", tags=["users"])
""",
    "app/api/v1/endpoints/user.py": """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.crud.user import get_user_by_username, create_user
from app.db.schemas.user import UserCreate, UserRead
from app.api.v1.dependencies import get_db_dep

router = APIRouter()

@router.post("/", response_model=UserRead)
async def create_user_endpoint(user: UserCreate, db: AsyncSession = Depends(get_db_dep)):
    db_user = await get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await create_user(db, user)

@router.get("/{username}", response_model=UserRead)
async def read_user(username: str, db: AsyncSession = Depends(get_db_dep)):
    db_user = await get_user_by_username(db, username)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
""",
    "app/api/v1/dependencies.py": """from fastapi import Depends
from app.db.session import get_db

def get_common_dependency():
    return "common"

def get_db_dep(db=Depends(get_db)):
    return db
""",
    "app/core/config.py": """from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str
    database_url_without_async: str
    jwt_secret_token: str

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
""",
    "app/core/exception_handlers.py": """from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

def add_exception_handlers(app: FastAPI):
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
""",
    "app/core/logging.py": """from loguru import logger

def setup_logging():
    logger.add("logs/app.log", rotation="1 week")
""",
    "app/db/session.py": """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

DATABASE_URL = get_settings().database_url

engine = create_async_engine(DATABASE_URL, future=True, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
""",
    "app/db/base.py": """from sqlalchemy.orm import DeclarativeMeta, declarative_base

Base: DeclarativeMeta = declarative_base()
""",
    "app/db/models/user.py": """from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
""",
    "app/db/schemas/user.py": """from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True
""",
    "app/db/crud/user.py": """from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.user import User
from app.db.schemas.user import UserCreate

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: UserCreate):
    db_user = User(username=user.username, email=user.email, hashed_password=user.password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
""",
    "app/middlewares/logging_middleware.py": """from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        print(f"Response status: {response.status_code}")
        return response
""",
    "app/utils/task_queue.py": """import asyncio

queue = asyncio.Queue()

async def add_task(task):
    await queue.put(task)

async def worker():
    while True:
        task = await queue.get()
        # process task
        queue.task_done()
""",
    "tests/conftest.py": """import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
""",
    "tests/api/test_user.py": """def test_create_and_get_user(client):
    user_data = {"username": "alice", "email": "alice@example.com", "password": "secret"}
    resp = client.post("/api/v1/users/", json=user_data)
    assert resp.status_code == 200
    user = resp.json()
    assert user["username"] == "alice"
    resp2 = client.get(f"/api/v1/users/{user['username']}")
    assert resp2.status_code == 200
    assert resp2.json()["email"] == "alice@example.com"
""",
    "tests/api/test_health.py": """def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"message": "OK"}
""",
    ".env": """DATABASE_URL=postgresql+asyncpg://youruser:yourpassword@localhost:5432/yourdb
DATABASE_URL_WITHOUT_ASYNC=postgresql://youruser:yourpassword@localhost:5432/yourdb
JWT_SECRET_TOKEN=your-very-secret-key
""",
}

DIRS = [
    "app/api/v1/endpoints",
    "app/core",
    "app/db/crud",
    "app/db/models",
    "app/db/schemas",
    "app/middlewares",
    "app/services",
    "app/utils",
    "tests/api",
]

# --- Scaffold Boilerplate CLI ---
import typer
from rich.console import Console

app = typer.Typer(help="FastAPI Boilerplate Project Scaffold CLI")
console = Console()

# --- Directory structure ---
DIRS = [
    "app/api/v1/endpoints",
    "app/core",
    "logs",
    "tests/api",
]

# --- File templates for USER/AUTH/JWT boilerplate ---
TEMPLATES = {
    # Project files
    "pyproject.toml": """
[project]
# This will be replaced with your actual project name
name = "${project_name}"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]>=0.115.12",
    "uvicorn[standard]",
    "sqlalchemy",
    "asyncpg",
    "psycopg2-binary",
    "python-dotenv",
    "pydantic",
    "httpx",
    "jinja2",
    "python-multipart",
    "email-validator",
    "itsdangerous",
    "pydantic-settings",
    "greenlet",
    "fastapi-mcp>=0.3.3",
    "loguru>=0.7.3",
    "alembic",
    "pyjwt",
    "passlib[bcrypt]",
    "fastmcp>=2.3.2",
    "mcp>=1.8.0",
]
""",
    ".gitignore": ".env\n.venv\n__pycache__/\n*.pyc\n*.pyo\n*.pyd\nuv.lock\nlogs/\n",
    "README.md": """# FastAPI + PostgreSQL User/Auth Boilerplate\n\n## Features\n- Async FastAPI app\n- SQLAlchemy 2.0, Alembic migrations\n- JWT auth, Loguru logging\n- Modular user CRUD and registration/login\n- uv for dependency management\n\n## Setup\n\n```bash\nuv pip install -r requirements.txt\nuv run -- alembic upgrade head\nuv run -- uvicorn app.main:app --reload\n```\n""",
    ".env": """DATABASE_URL=postgresql+asyncpg://youruser:yourpassword@localhost:5432/yourdb
DATABASE_URL_WITHOUT_ASYNC=postgresql://youruser:yourpassword@localhost:5432/yourdb
JWT_SECRET_TOKEN=your-very-secret-key
""",
    "alembic.ini": """# Alembic configuration file
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:pass@localhost/dbname
# ...rest of alembic.ini...
""",
    "alembic/env.py": """import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.config import get_settings
from app.db.base import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def get_url():
    return get_settings().database_url_without_async

config.set_main_option("sqlalchemy.url", get_url())

def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""",
    "alembic/script.py.mako": '''"""${message}"""

revision = '${up_revision}'
down_revision = ${down_revision if down_revision is not None else None}
branch_labels = ${repr(branch_labels) if branch_labels else None}
depends_on = ${repr(depends_on) if depends_on else None}

def upgrade():
    pass

def downgrade():
    pass
''',
    # --- App core files ---
    "app/main.py": """from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.exception_handlers import add_exception_handlers

app = FastAPI(title="FastAPI User/Auth Boilerplate")
add_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")

# --- MCP Integration ---
try:
    from fastapi_mcp import FastApiMCP
    mcp = FastApiMCP(app)
    mcp.mount()
    print("[INFO] FastAPI-MCP successfully mounted.")
except ImportError as e:
    print("[ERROR] fastapi_mcp is not installed. Install it with 'uv pip install fastapi_mcp' or 'poetry add fastapi_mcp'.")
except Exception as e:
    print(f"[ERROR] Failed to mount FastAPI-MCP: {e}")

@app.get("/health")
def health_check():
    return {"message": "OK"}
""",
    "app/__init__.py": "",
    "app/api/__init__.py": "",
    "app/api/v1/__init__.py": "",
    "app/api/v1/api.py": """from fastapi import APIRouter
from app.api.v1.endpoints import user

api_router = APIRouter()
api_router.include_router(user.router, prefix="/users", tags=["users"])
""",
    "app/api/v1/dependencies.py": """from fastapi import Depends
from app.db.session import get_db

def get_common_dependency():
    return "common"

def get_db_dep(db=Depends(get_db)):
    return db
""",
    "app/api/v1/endpoints/__init__.py": "",
    "app/api/v1/endpoints/user.py": """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.crud.user import get_user_by_username, create_user
from app.db.schemas.user import UserCreate, UserRead
from app.api.v1.dependencies import get_db_dep

router = APIRouter()

@router.post("/", response_model=UserRead)
async def create_user_endpoint(user: UserCreate, db: AsyncSession = Depends(get_db_dep)):
    db_user = await get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await create_user(db, user)

@router.get("/{username}", response_model=UserRead)
async def read_user(username: str, db: AsyncSession = Depends(get_db_dep)):
    db_user = await get_user_by_username(db, username)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
""",
    # --- Core ---
    "app/core/__init__.py": "",
    "app/core/config.py": """from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str
    database_url_without_async: str
    jwt_secret_token: str

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
""",
    "app/core/exception_handlers.py": """from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

def add_exception_handlers(app: FastAPI):
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
""",
    "app/core/logging.py": """from loguru import logger

def setup_logging():
    logger.add("logs/app.log", rotation="1 week")
""",
    "app/core/security.py": """from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: int = 3600):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_settings().jwt_secret_token, algorithm="HS256")
    return encoded_jwt
""",
    # --- DB ---
    "app/db/__init__.py": "",
    "app/db/base.py": """from sqlalchemy.orm import DeclarativeMeta, declarative_base

Base: DeclarativeMeta = declarative_base()
""",
    "app/db/session.py": """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

DATABASE_URL = get_settings().database_url

engine = create_async_engine(DATABASE_URL, future=True, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
""",
    "app/db/models/__init__.py": "",
    "app/db/models/user.py": """from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
""",
    "app/db/schemas/__init__.py": "",
    "app/db/schemas/user.py": """from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True
""",
    "app/db/crud/__init__.py": "",
    "app/db/crud/user.py": """from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.user import User
from app.db.schemas.user import UserCreate

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: UserCreate):
    db_user = User(username=user.username, email=user.email, hashed_password=user.password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
""",
    # --- Services ---
    "app/services/__init__.py": "",
    "app/services/base_service.py": """from typing import Generic, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")

class BaseService(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int):
        return await db.get(self.model, id)
""",
    "app/services/user_service.py": """from app.services.base_service import BaseService
from app.db.models.user import User

class UserService(BaseService[User]):
    pass
""",
    # --- Middlewares ---
    "app/middlewares/__init__.py": "",
    "app/middlewares/logging_middleware.py": """from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        print(f"Response status: {response.status_code}")
        return response
""",
    # --- Utils ---
    "app/utils/__init__.py": "",
    "app/utils/task_queue.py": """import asyncio

queue = asyncio.Queue()

async def add_task(task):
    await queue.put(task)

async def worker():
    while True:
        task = await queue.get()
        # process task
        queue.task_done()
""",
    # --- Tests ---
    "tests/__init__.py": "",
    "tests/conftest.py": """import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
""",
    "tests/api/__init__.py": "",
    "tests/api/test_user.py": """def test_create_and_get_user(client):
    user_data = {"username": "alice", "email": "alice@example.com", "password": "secret"}
    resp = client.post("/api/v1/users/", json=user_data)
    assert resp.status_code == 200
    user = resp.json()
    assert user["username"] == "alice"
    resp2 = client.get(f"/api/v1/users/{user['username']}")
    assert resp2.status_code == 200
    assert resp2.json()["email"] == "alice@example.com"
""",
    "tests/api/test_health.py": """def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"message": "OK"}
""",
}

import subprocess


@app.command()
def scaffold() -> None:
    """Interactively scaffold a complete FastAPI + PostgreSQL boilerplate using uv."""
    console.print(
        "[bold cyan]Welcome to the FastAPI Boilerplate Scaffold CLI![/bold cyan]",
    )
    project_name = Prompt.ask(
        "Enter your project name (leave blank for current directory)", default="",
    ).strip()
    target_dir = project_name or os.getcwd()

    # Check if directory exists and is empty
    if project_name:
        if os.path.exists(project_name):
            if os.listdir(project_name):
                console.print(
                    f"[red]Directory '{project_name}' is not empty. Aborting.[/red]",
                )
                raise typer.Exit
        else:
            # Step 1: Run 'uv init <project_name>'
            console.print(f"[cyan]Initializing project with uv: {project_name}[/cyan]")
            result = subprocess.run(["uv", "init", project_name], check=False)
            # return;
            if result.returncode != 0:
                console.print(
                    "[red]uv init failed. Please make sure uv is installed.[/red]",
                )
                raise typer.Exit
    # Using current directory
    elif os.listdir(target_dir):
        console.print("[red]Current directory is not empty. Aborting.[/red]")
        raise typer.Exit

    # Step 2: Change into the project directory if needed
    if project_name:
        os.chdir(project_name)
        target_dir = os.getcwd()

    # Step 3: Create directories and files as before
    for d in DIRS:
        os.makedirs(d, exist_ok=True)
        if "__init__.py" not in d and not os.path.exists(
            os.path.join(d, "__init__.py"),
        ):
            open(os.path.join(d, "__init__.py"), "a").close()

    # Replace variables in template content
    for path, content in TEMPLATES.items():
        full_path = os.path.join(target_dir, path) if project_name else path
        dir_path = os.path.dirname(full_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        # Replace template variables
        processed_content = content.replace(
            "${project_name}", project_name or os.path.basename(os.getcwd()),
        )

        with open(full_path, "w") as f:
            f.write(processed_content)

    # run uv sync command
    result = subprocess.run(["uv", "sync"], check=False)
    if result.returncode != 0:
        console.print("[red]uv sync failed. Please make sure uv is installed.[/red]")
        raise typer.Exit

    # --- Alembic async setup ---
    console.print("[cyan]Setting up Alembic for async PostgreSQL...[/cyan]")
    # Run alembic init -t async alembic
    result = subprocess.run(["alembic", "init", "-t", "async", "alembic"], check=False)
    if result.returncode != 0:
        console.print(
            "[red]alembic init failed. Please make sure alembic is installed.[/red]",
        )
        raise typer.Exit

    # Patch alembic.ini with correct DB URL from .env
    import re

    env_path = os.path.join(target_dir, ".env") if project_name else ".env"
    db_url = None
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("DATABASE_URL_WITHOUT_ASYNC="):
                    db_url = line.strip().split("=", 1)[-1]
                    break
    if db_url:
        ini_path = (
            os.path.join(target_dir, "alembic.ini") if project_name else "alembic.ini"
        )
        with open(ini_path) as f:
            ini_content = f.read()
        ini_content = re.sub(
            r"sqlalchemy.url\s*=.*", f"sqlalchemy.url = {db_url}", ini_content,
        )
        with open(ini_path, "w") as f:
            f.write(ini_content)

    # Patch alembic/env.py for dynamic config and correct Base
    env_py_path = (
        os.path.join(target_dir, "alembic", "env.py")
        if project_name
        else os.path.join("alembic", "env.py")
    )
    if os.path.exists(env_py_path):
        with open(env_py_path) as f:
            env_py = f.read()
        # Replace target_metadata and db url logic
        env_py = re.sub(
            r"from alembic import context.*?target_metadata = .*?\n",
            "from alembic import context\nimport os\nimport sys\nsys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))\nfrom app.core.config import get_settings\nfrom app.db.base import Base\n\ntarget_metadata = Base.metadata\n",
            env_py,
            flags=re.DOTALL,
        )
        # Replace get_url() if present
        env_py = re.sub(
            r"def get_url\(\):.*?return .*?\n",
            "def get_url():\n    return get_settings().database_url_without_async\n",
            env_py,
            flags=re.DOTALL,
        )
        with open(env_py_path, "w") as f:
            f.write(env_py)

    console.print(
        f"[green]Boilerplate for '{project_name or target_dir}' created with uv, DB connectivity, Alembic (async), TOML, and testable code![/green]",
    )
    console.print(
        "\n[bold yellow]Alembic async migration setup complete![/bold yellow]",
    )
    console.print("\n[white]Next steps:[/white]")
    console.print(
        "  1. [bold]alembic revision --autogenerate -m 'Initial migration'[/bold]  # generate migration script",
    )
    console.print("  2. [bold]alembic upgrade head[/bold]  # apply to your database\n")
    console.print(
        "You can also integrate Alembic migrations into FastAPI startup for dev, but this is optional and not always recommended for production.",
    )


if __name__ == "__main__":
    app()

    app()
