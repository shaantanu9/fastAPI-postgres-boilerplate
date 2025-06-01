import asyncio
import asyncpg
from app.core.config import get_settings

async def check_tables():
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
        
        print('Database tables:')
        for row in result:
            print(f'  - {row["table_name"]}')
            
        # Check specific table structure
        for table in ['users', 'products', 'orders']:
            try:
                columns = await conn.fetch(f"""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)
                
                if columns:
                    print(f'\n{table.upper()} table structure:')
                    for col in columns:
                        print(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
                
                # Check row count
                count = await conn.fetchval(f'SELECT COUNT(*) FROM {table}')
                print(f"  Row count: {count}")
                
            except Exception as e:
                print(f'  Table {table} does not exist or error: {e}')
            
        # Check alembic version
        try:
            version = await conn.fetchval('SELECT version_num FROM alembic_version')
            print(f'\nAlembic version: {version}')
        except Exception as e:
            print(f'Alembic version error: {e}')
        
    except Exception as e:
        print(f'Error: {e}')
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tables()) 