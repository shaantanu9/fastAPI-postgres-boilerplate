"""
Database Table Checker Utility

This utility script helps verify the existence of database tables, which is useful for:
- Verifying model removal operations
- Checking database state after migrations
- Debugging table existence issues
- Validating database cleanup operations

Usage Examples:
1. Check specific table: `python check_table.py --table users`
2. Check multiple tables: `python check_table.py --table users --table products`
3. List all tables: `python check_table.py --list-all`
4. Check tables matching pattern: `python check_table.py --pattern test_*`

Common Use Cases:
- After removing models to verify tables were dropped
- Before migrations to check current state
- Debugging database synchronization issues
- Validating cleanup operations
"""

import sys
sys.path.append('.')
from app.db.session import engine
from sqlalchemy import text
import asyncio
import fnmatch

async def check_table_exists(table_name: str) -> bool:
    """
    Check if a specific table exists in the database
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_name = :table_name"),
                {"table_name": table_name}
            )
            return result.fetchone() is not None
    except Exception as e:
        print(f"Error checking table '{table_name}': {e}")
        return False

async def list_all_tables() -> list:
    """
    Get a list of all tables in the database
    
    Returns:
        list: List of table names
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            )
            return [row[0] for row in result.fetchall()]
    except Exception as e:
        print(f"Error listing tables: {e}")
        return []

async def check_tables_by_pattern(pattern: str) -> dict:
    """
    Check tables matching a pattern (supports wildcards)
    
    Args:
        pattern: Pattern to match (e.g., 'test_*', '*_plugin', 'user*')
        
    Returns:
        dict: Dictionary of table_name -> exists status
    """
    try:
        all_tables = await list_all_tables()
        matching_tables = [table for table in all_tables if fnmatch.fnmatch(table, pattern)]
        
        results = {}
        for table in matching_tables:
            results[table] = await check_table_exists(table)
            
        return results
    except Exception as e:
        print(f"Error checking pattern '{pattern}': {e}")
        return {}

async def get_table_info(table_name: str) -> dict:
    """
    Get detailed information about a table
    
    Args:
        table_name: Name of the table
        
    Returns:
        dict: Table information including columns, constraints, etc.
    """
    try:
        async with engine.begin() as conn:
            # Check if table exists
            exists = await check_table_exists(table_name)
            if not exists:
                return {"exists": False}
            
            # Get column information
            columns_result = await conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = :table_name 
                    ORDER BY ordinal_position
                """),
                {"table_name": table_name}
            )
            columns = [dict(row._mapping) for row in columns_result.fetchall()]
            
            # Get row count
            count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = count_result.fetchone()[0]
            
            return {
                "exists": True,
                "columns": columns,
                "row_count": row_count
            }
            
    except Exception as e:
        print(f"Error getting table info for '{table_name}': {e}")
        return {"exists": False, "error": str(e)}

async def main():
    """Main function with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database table checker utility')
    parser.add_argument('--table', '-t', action='append', help='Table name to check (can be used multiple times)')
    parser.add_argument('--list-all', '-l', action='store_true', help='List all tables in database')
    parser.add_argument('--pattern', '-p', help='Check tables matching pattern (supports wildcards)')
    parser.add_argument('--info', '-i', help='Get detailed info about a specific table')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # If no arguments provided, use default behavior (check test_removal5s)
    if not any([args.table, args.list_all, args.pattern, args.info]):
        print("🔍 Default check: test_removal5s table")
        exists = await check_table_exists('test_removal5s')
        print(f"test_removal5s table exists: {exists}")
        return
    
    # List all tables
    if args.list_all:
        print("📋 All tables in database:")
        tables = await list_all_tables()
        for table in tables:
            print(f"  • {table}")
        print(f"\nTotal: {len(tables)} tables")
    
    # Check specific tables
    if args.table:
        print("🔍 Checking specific tables:")
        for table_name in args.table:
            exists = await check_table_exists(table_name)
            status = "✅ EXISTS" if exists else "❌ NOT FOUND"
            print(f"  {table_name}: {status}")
    
    # Check pattern
    if args.pattern:
        print(f"🔍 Checking tables matching pattern: {args.pattern}")
        results = await check_tables_by_pattern(args.pattern)
        if results:
            for table_name, exists in results.items():
                status = "✅ EXISTS" if exists else "❌ NOT FOUND"
                print(f"  {table_name}: {status}")
        else:
            print("  No tables found matching pattern")
    
    # Get detailed info
    if args.info:
        print(f"📊 Detailed info for table: {args.info}")
        info = await get_table_info(args.info)
        if info["exists"]:
            print(f"  ✅ Table exists")
            print(f"  📊 Row count: {info['row_count']}")
            print(f"  📋 Columns ({len(info['columns'])}):")
            for col in info['columns']:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"    • {col['column_name']}: {col['data_type']} {nullable}{default}")
        else:
            print(f"  ❌ Table does not exist")
            if "error" in info:
                print(f"  Error: {info['error']}")

if __name__ == "__main__":
    asyncio.run(main()) 