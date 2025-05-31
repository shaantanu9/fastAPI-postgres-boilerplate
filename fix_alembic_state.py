import asyncio
from app.db.session import engine
from sqlalchemy import text

async def fix_alembic():
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE alembic_version SET version_num = '4fa0d8b64602'"))
        print('Fixed alembic state to latest existing migration')

asyncio.run(fix_alembic()) 