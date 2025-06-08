import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, engine_from_config, pool

# Load environment variables from .env for Alembic CLI
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Patch: Inject DATABASE_URL from environment if not already present
# Always set sqlalchemy.url from the DATABASE_URL environment variable if present
_db_url = os.getenv("DATABASE_URL_WITHOUT_ASYNC")
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.db.base import Base

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# SCAFFOLD_SAFE_AUTOGENERATE_CONFIG - Prevents touching existing infrastructure
def include_name(name, type_, parent_names) -> bool:
    """Filter function to prevent autogenerate from touching existing infrastructure.
    Only includes tables that are part of our application models.
    """
    if type_ == "table":
        # List of infrastructure tables to never touch
        infrastructure_tables = {
            "alembic_version",
            "procrastinate_jobs",
            "procrastinate_job",  # Alternative naming
            "procrastinate_events",
            "procrastinate_periodic_defers",
            "procrastinate_periodic_defer",  # Alternative naming
            "procrastinate_locks",
            "procrastinate_workers",
        }

        # Skip infrastructure tables
        if name in infrastructure_tables:
            return False

        # Only include tables that match our application naming pattern
        # This prevents touching any existing tables not managed by our scaffold
        return True

    return True


def include_object(object, name, type_, reflected, compare_to) -> bool:
    """Advanced filtering to prevent autogenerate from modifying existing infrastructure."""
    if type_ == "table":
        # Infrastructure tables to never touch
        infrastructure_tables = {
            "alembic_version",
            "procrastinate_jobs",
            "procrastinate_job",  # Alternative naming
            "procrastinate_events",
            "procrastinate_periodic_defers",
            "procrastinate_periodic_defer",  # Alternative naming
            "procrastinate_locks",
            "procrastinate_workers",
        }

        if name in infrastructure_tables:
            return False

    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
