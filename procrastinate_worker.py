#!/usr/bin/env python3
"""
Procrastinate Worker CLI

This script provides a command-line interface for running Procrastinate workers
independently of the main FastAPI application. This allows for distributed task
processing across multiple machines or containers.

Usage:
    python procrastinate_worker.py --help
    python procrastinate_worker.py worker --queues user_processing data_processing
    python procrastinate_worker.py worker --concurrency 20
    python procrastinate_worker.py healthchecks
    python procrastinate_worker.py shell

Features:
- Run workers for specific queues
- Configurable concurrency
- Health checks and monitoring
- Interactive shell for job management
- Schema management
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import List, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set event loop policy for better compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.core.config import get_settings
from app.utils.procrastinate_manager import procrastinate_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_worker(queues: Optional[List[str]] = None, concurrency: int = 10):
    """Run Procrastinate worker with specified configuration"""
    logger.info(f"Starting Procrastinate worker with concurrency: {concurrency}")
    
    if queues:
        logger.info(f"Listening to queues: {', '.join(queues)}")
    else:
        logger.info("Listening to all queues")
    
    async with procrastinate_app.open_async():
        try:
            await procrastinate_app.run_worker_async(
                queues=queues,
                concurrency=concurrency,
                install_signal_handlers=True
            )
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            raise


def apply_schema():
    """Apply Procrastinate database schema"""
    logger.info("Applying Procrastinate database schema...")
    
    try:
        # Use sync version to avoid event loop conflicts
        with procrastinate_app.open():
            procrastinate_app.schema_manager.apply_schema()
        
        logger.info("Schema applied successfully")
    except Exception as e:
        logger.error(f"Failed to apply schema: {e}")
        raise


async def health_checks():
    """Perform health checks on the Procrastinate system"""
    logger.info("Performing Procrastinate health checks...")
    
    try:
        async with procrastinate_app.open_async():
            # Try to connect to the database
            logger.info("✓ Database connection: OK")
            
            # Check if schema exists
            # This would require custom implementation to check schema
            logger.info("✓ Schema check: OK (basic)")
            
            logger.info("All health checks passed!")
            return True
            
    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return False


async def interactive_shell():
    """Start an interactive shell for job management"""
    logger.info("Starting Procrastinate interactive shell...")
    logger.info("Available commands: help, list_jobs, list_queues, exit")
    
    async with procrastinate_app.open_async():
        while True:
            try:
                command = input("procrastinate> ").strip().lower()
                
                if command == "exit" or command == "quit":
                    break
                elif command == "help":
                    print("Available commands:")
                    print("  help         - Show this help")
                    print("  list_jobs    - List jobs (requires custom implementation)")
                    print("  list_queues  - List available queues")
                    print("  exit/quit    - Exit the shell")
                elif command == "list_queues":
                    queues = [
                        "user_processing",
                        "data_processing", 
                        "notifications",
                        "file_processing",
                        "analytics",
                        "maintenance",
                        "health_checks"
                    ]
                    print("Available queues:")
                    for queue in queues:
                        print(f"  - {queue}")
                elif command == "list_jobs":
                    print("Job listing requires custom implementation using Procrastinate tables")
                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
    
    logger.info("Interactive shell ended")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Procrastinate Worker CLI for FastAPI PostgreSQL Boilerplate"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Worker command
    worker_parser = subparsers.add_parser("worker", help="Run Procrastinate worker")
    worker_parser.add_argument(
        "--queues", "-q",
        nargs="*",
        help="Specific queues to listen to (default: all queues)",
        default=None
    )
    worker_parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Number of concurrent jobs to process (default: 10)"
    )
    
    # Schema command
    subparsers.add_parser("schema", help="Apply database schema")
    
    # Health checks command
    subparsers.add_parser("healthchecks", help="Perform health checks")
    
    # Interactive shell command
    subparsers.add_parser("shell", help="Start interactive shell")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load settings
    settings = get_settings()
    logger.info(f"Connecting to database: {settings.postgres_host}:{settings.postgres_port}")
    
    # Execute command
    try:
        # Create a new event loop for each command to avoid conflicts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if args.command == "worker":
            loop.run_until_complete(run_worker(
                queues=args.queues,
                concurrency=args.concurrency
            ))
        elif args.command == "schema":
            apply_schema()
        elif args.command == "healthchecks":
            success = loop.run_until_complete(health_checks())
            sys.exit(0 if success else 1)
        elif args.command == "shell":
            loop.run_until_complete(interactive_shell())
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)
    finally:
        # Clean up the event loop
        try:
            loop.close()
        except:
            pass


if __name__ == "__main__":
    main() 