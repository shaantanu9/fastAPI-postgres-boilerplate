import asyncio
import contextlib

import asyncpg

from app.core.config import get_settings


async def check_tables() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url_without_async)
    try:
        # Check existing tables
        result = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        for _row in result:
            pass

        # Check specific table structure
        for table in ["users", "products", "orders"]:
            try:
                columns = await conn.fetch(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)

                if columns:
                    for _col in columns:
                        pass

                # Check row count
                await conn.fetchval(f"SELECT COUNT(*) FROM {table}")

            except Exception:
                pass

        # Check alembic version
        with contextlib.suppress(Exception):
            await conn.fetchval("SELECT version_num FROM alembic_version")

    except Exception:
        pass
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_tables())
