#!/usr/bin/env python3
"""Initialize Procrastinate database schema.

This script creates all the necessary tables and types for Procrastinate
to work properly with the PostgreSQL database.
"""

import asyncio
import sys

from app.core.config import get_settings
from app.utils.procrastinate_manager import procrastinate_app


async def init_schema() -> bool:
    """Initialize Procrastinate schema async."""
    get_settings()


    try:
        # Open app and apply schema
        async with procrastinate_app.open_async():

            # Apply schema (create tables, types, etc.)
            await procrastinate_app.schema_manager.apply_schema()

    except Exception:
        return False

    return True


def init_schema_sync() -> bool:
    """Initialize Procrastinate schema sync."""
    get_settings()


    try:
        # Open app and apply schema
        with procrastinate_app.open():

            # Apply schema (create tables, types, etc.)
            procrastinate_app.schema_manager.apply_schema()

    except Exception:
        return False

    return True


async def verify_schema() -> bool | None:
    """Verify that the schema was created properly."""
    import psycopg2

    settings = get_settings()

    try:
        conn = psycopg2.connect(settings.procrastinate_connection_string)
        cur = conn.cursor()

        # Check tables
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'procrastinate'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]

        # Check types
        cur.execute("""
            SELECT typname FROM pg_type t
            JOIN pg_namespace n ON t.typnamespace = n.oid
            WHERE n.nspname = 'procrastinate'
            ORDER BY typname;
        """)
        [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()


        expected_tables = ["procrastinate_jobs", "procrastinate_events"]
        missing_tables = [t for t in expected_tables if t not in tables]

        return not missing_tables

    except Exception:
        return False


async def main() -> int:
    """Main function."""
    # Try async first
    success = await init_schema()

    if not success:
        success = init_schema_sync()

    if success:
        verified = await verify_schema()

        if verified:
            return 0
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
