#!/usr/bin/env python3
"""Fix alembic version table"""

import asyncio
from app.db.session import engine
from sqlalchemy import text

async def fix_alembic_async():
    """Fix alembic for async engine"""
    async with engine.begin() as conn:
        # Check current version
        try:
            result = await conn.execute(text('SELECT version_num FROM alembic_version'))
            current = result.fetchone()
            print(f'Current version: {current[0] if current else None}')
        except Exception as e:
            print(f'Error reading version: {e}')
        
        # Update to the head version
        try:
            await conn.execute(text("UPDATE alembic_version SET version_num = '7022e95fa946'"))
            print('Updated to head version: 7022e95fa946')
        except Exception as e:
            print(f'Error updating version: {e}')

def fix_alembic_sync():
    """Fix alembic for sync engine"""
    with engine.connect() as conn:
        # Check current version
        try:
            result = conn.execute(text('SELECT version_num FROM alembic_version'))
            current = result.fetchone()
            print(f'Current version: {current[0] if current else None}')
        except Exception as e:
            print(f'Error reading version: {e}')
        
        # Update to the head version
        try:
            conn.execute(text("UPDATE alembic_version SET version_num = '7022e95fa946'"))
            conn.commit()
            print('Updated to head version: 7022e95fa946')
        except Exception as e:
            print(f'Error updating version: {e}')

if __name__ == "__main__":
    # Check if we have an async engine
    if hasattr(engine, 'begin'):
        # Async engine
        asyncio.run(fix_alembic_async())
    else:
        # Sync engine
        fix_alembic_sync() 