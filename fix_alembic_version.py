"""
Alembic Version Fix Utility

This utility script helps fix corrupted alembic version states that can occur when:
- Migration files are manually deleted
- Database and migration files get out of sync
- Alembic references non-existent migration revisions

Usage:
1. Check what migrations are available: `alembic history`
2. Update the correct_head variable below to the desired revision
3. Run: `python fix_alembic_version.py`

Common Scenarios:
- After removing models with migrations
- When alembic current shows "Can't locate revision" errors
- When migration system is corrupted after manual file deletions

Safety Notes:
- Always backup your database before running
- Verify the target revision exists in `alembic history`
- This directly modifies the alembic_version table
"""

import sys
sys.path.append('.')
from app.db.session import engine
from sqlalchemy import text
import asyncio

async def fix_alembic_version(target_revision: str = None):
    """
    Fix the alembic version table to point to the correct head
    
    Args:
        target_revision: The revision ID to set as current (if None, uses preset)
    """
    try:
        async with engine.begin() as conn:
            # Check current version in database
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.fetchone()
            current_rev = current_version[0] if current_version else 'None'
            print(f"Current alembic version in database: {current_rev}")
            
            # Set target revision - UPDATE THIS BASED ON YOUR NEEDS
            # Run `alembic history` to see available revisions
            # Use `alembic heads` to see the latest head
            correct_head = target_revision or "ec62d2a648e7"  # Default: TestRemoval3 migration
            
            print(f"Target revision: {correct_head}")
            
            # Confirm before proceeding (unless target_revision is explicitly provided)
            if not target_revision:
                confirm = input(f"Update alembic version from '{current_rev}' to '{correct_head}'? (y/N): ")
                if confirm.lower() not in ['y', 'yes']:
                    print("Operation cancelled")
                    return False
            
            # Update the alembic version
            await conn.execute(text("UPDATE alembic_version SET version_num = :version"), {"version": correct_head})
            print(f"✅ Updated alembic version to: {correct_head}")
            
            # Verify the update
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            new_version = result.fetchone()
            new_rev = new_version[0] if new_version else 'None'
            print(f"✅ Verified new alembic version: {new_rev}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error fixing alembic version: {e}")
        return False

async def get_current_alembic_version():
    """Get the current alembic version from the database"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.fetchone()
            return current_version[0] if current_version else None
    except Exception as e:
        print(f"Error getting current version: {e}")
        return None

async def list_available_revisions():
    """Helper function to show available revisions (requires alembic command)"""
    import subprocess
    try:
        result = subprocess.run(['alembic', 'history'], capture_output=True, text=True)
        if result.returncode == 0:
            print("Available revisions:")
            print(result.stdout)
        else:
            print("Could not get revision history")
    except Exception as e:
        print(f"Error listing revisions: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix alembic version table')
    parser.add_argument('--revision', '-r', help='Target revision ID')
    parser.add_argument('--list', '-l', action='store_true', help='List available revisions')
    parser.add_argument('--current', '-c', action='store_true', help='Show current version')
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_available_revisions())
    elif args.current:
        current = asyncio.run(get_current_alembic_version())
        print(f"Current alembic version: {current}")
    else:
        asyncio.run(fix_alembic_version(args.revision)) 