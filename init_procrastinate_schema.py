#!/usr/bin/env python3
"""
Initialize Procrastinate database schema.

This script creates all the necessary tables and types for Procrastinate
to work properly with the PostgreSQL database.
"""

import asyncio
import sys
from app.utils.procrastinate_manager import procrastinate_app
from app.core.config import get_settings

async def init_schema():
    """Initialize Procrastinate schema async"""
    settings = get_settings()
    
    print(f"🔧 Initializing Procrastinate schema...")
    print(f"📍 Database: {settings.procrastinate_connection_string}")
    print(f"📦 Schema: {settings.procrastinate_schema}")
    
    try:
        # Open app and apply schema
        async with procrastinate_app.open_async():
            print("🔗 Connected to database")
            
            # Apply schema (create tables, types, etc.)
            await procrastinate_app.schema_manager.apply_schema()
            print("✅ Schema applied successfully!")
            
    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        return False
    
    return True

def init_schema_sync():
    """Initialize Procrastinate schema sync"""
    settings = get_settings()
    
    print(f"🔧 Initializing Procrastinate schema (sync)...")
    print(f"📍 Database: {settings.procrastinate_connection_string}")
    print(f"📦 Schema: {settings.procrastinate_schema}")
    
    try:
        # Open app and apply schema
        with procrastinate_app.open():
            print("🔗 Connected to database")
            
            # Apply schema (create tables, types, etc.)
            procrastinate_app.schema_manager.apply_schema()
            print("✅ Schema applied successfully!")
            
    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        return False
    
    return True

async def verify_schema():
    """Verify that the schema was created properly"""
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
        types = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        print(f"📋 Tables created: {tables}")
        print(f"🏷️  Types created: {types}")
        
        expected_tables = ['procrastinate_jobs', 'procrastinate_events']
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"⚠️  Missing tables: {missing_tables}")
            return False
        else:
            print("✅ All expected tables present!")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False

async def main():
    """Main function"""
    print("🚀 Starting Procrastinate schema initialization...")
    
    # Try async first
    success = await init_schema()
    
    if not success:
        print("🔄 Trying sync initialization...")
        success = init_schema_sync()
    
    if success:
        print("🔍 Verifying schema...")
        verified = await verify_schema()
        
        if verified:
            print("🎉 Procrastinate schema initialized successfully!")
            return 0
        else:
            print("❌ Schema verification failed")
            return 1
    else:
        print("❌ Schema initialization failed")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 