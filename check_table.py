#!/usr/bin/env python3
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check_table():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'products';"))
        tables = result.fetchall()
        if tables:
            print('✅ Products table exists')
        else:
            print('❌ Products table does not exist')

if __name__ == "__main__":
    asyncio.run(check_table()) 