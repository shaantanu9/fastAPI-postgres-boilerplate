#!/usr/bin/env python3
"""
Check Procrastinate Jobs Status

This script queries the Procrastinate database tables directly to see job status.
"""

import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind"

async def check_procrastinate_jobs():
    """Check the status of Procrastinate jobs in the database"""
    
    print("🔍 CHECKING PROCRASTINATE JOBS STATUS")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Query recent jobs
        query = """
        SELECT 
            id,
            queue_name,
            task_name,
            status,
            priority,
            scheduled_at,
            attempts,
            args
        FROM procrastinate_jobs 
        ORDER BY id DESC 
        LIMIT 20
        """
        
        rows = await conn.fetch(query)
        
        if not rows:
            print("❌ No jobs found in the database")
            return
        
        print(f"📊 Found {len(rows)} recent jobs:")
        print()
        
        for row in rows:
            print(f"Job ID: {row['id']}")
            print(f"  Queue: {row['queue_name']}")
            print(f"  Task: {row['task_name']}")
            print(f"  Status: {row['status']}")
            print(f"  Priority: {row['priority']}")
            print(f"  Scheduled: {row['scheduled_at']}")
            print(f"  Attempts: {row['attempts']}")
            print(f"  Args: {row['args']}")
            print()
        
        # Get status summary
        status_query = """
        SELECT status, COUNT(*) as count
        FROM procrastinate_jobs
        GROUP BY status
        ORDER BY count DESC
        """
        
        status_rows = await conn.fetch(status_query)
        
        print("📈 JOB STATUS SUMMARY:")
        for status_row in status_rows:
            print(f"  {status_row['status']}: {status_row['count']} jobs")
        
        # Get worker information
        print("\n🤖 WORKER TABLE SCHEMA:")
        worker_schema_query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'procrastinate_workers'
        ORDER BY ordinal_position
        """
        
        schema_rows = await conn.fetch(worker_schema_query)
        for schema_row in schema_rows:
            print(f"  {schema_row['column_name']}: {schema_row['data_type']}")
        
        # Get active workers
        print("\n🤖 ACTIVE WORKERS:")
        workers_query = """
        SELECT * FROM procrastinate_workers 
        ORDER BY id DESC 
        LIMIT 5
        """
        
        worker_rows = await conn.fetch(workers_query)
        if worker_rows:
            for worker_row in worker_rows:
                print(f"Worker ID: {worker_row['id']}")
                print(f"  Name: {worker_row.get('name', 'N/A')}")
                print(f"  Start Time: {worker_row.get('start_time', worker_row.get('started_at', 'N/A'))}")
                print(f"  Heartbeat: {worker_row.get('last_heartbeat_at', worker_row.get('heartbeat_at', 'N/A'))}")
                print(f"  Queues: {worker_row.get('queues', 'N/A')}")
                print()
        else:
            print("  No workers found")
        
        print()
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error checking jobs: {e}")

if __name__ == "__main__":
    asyncio.run(check_procrastinate_jobs()) 