#!/usr/bin/env python3
"""Check Procrastinate Jobs Status.

This script queries the Procrastinate database tables directly to see job status.
"""

import asyncio

import asyncpg

DATABASE_URL = "postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind"


async def check_procrastinate_jobs() -> None:
    """Check the status of Procrastinate jobs in the database."""
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
            return


        for _row in rows:
            pass

        # Get status summary
        status_query = """
        SELECT status, COUNT(*) as count
        FROM procrastinate_jobs
        GROUP BY status
        ORDER BY count DESC
        """

        status_rows = await conn.fetch(status_query)

        for _status_row in status_rows:
            pass

        # Get worker information
        worker_schema_query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'procrastinate_workers'
        ORDER BY ordinal_position
        """

        schema_rows = await conn.fetch(worker_schema_query)
        for _schema_row in schema_rows:
            pass

        # Get active workers
        workers_query = """
        SELECT * FROM procrastinate_workers
        ORDER BY id DESC
        LIMIT 5
        """

        worker_rows = await conn.fetch(workers_query)
        if worker_rows:
            for _worker_row in worker_rows:
                pass
        else:
            pass


        await conn.close()

    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(check_procrastinate_jobs())
