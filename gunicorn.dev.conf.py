"""
Gunicorn Configuration for FastAPI Development

This configuration provides development-friendly settings with automatic reloading,
simple logging, and no permission issues.
"""
import multiprocessing
import os
from pathlib import Path

# =============================================================================
# DEVELOPMENT CONFIGURATION
# =============================================================================

# Bind to localhost for development
bind = "127.0.0.1:8000"

# Single worker for development (easier debugging)
workers = 1

# Worker class - use uvicorn workers for async FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Enable reloading for development
reload = True
reload_engine = "auto"
reload_extra_files = ["app/"]

# Shorter timeouts for development
timeout = 120  # Longer for debugging
graceful_timeout = 60
kill_timeout = 30

# Memory management (restart workers less frequently in dev)
max_requests = 100
max_requests_jitter = 10

# =============================================================================
# LOGGING (DEVELOPMENT)
# =============================================================================
# Simple console logging for development
loglevel = "debug"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr

# Simple log format
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)s'

# Capture output from workers
capture_output = True

# =============================================================================
# DEVELOPMENT-FRIENDLY SETTINGS
# =============================================================================
# Don't preload app (allows better reloading)
preload_app = False

# Process naming
proc_name = "fastapi-dev"

# No daemon mode for development
daemon = False

# Simple PID file in current directory
pidfile = "./gunicorn.pid"

# =============================================================================
# UVICORN WORKER OPTIONS
# =============================================================================
# Development-friendly uvicorn options
uvicorn_options = {
    "loop": "auto",  # Let uvicorn choose the best loop
    "http": "auto",  # Let uvicorn choose the best HTTP implementation
    "lifespan": "on",
    "access_log": True,
    "use_colors": True,  # Enable colors for development
}

# =============================================================================
# DEVELOPMENT HOOKS
# =============================================================================
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 Starting FastAPI development server with Gunicorn + Uvicorn")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"✅ FastAPI development server ready at http://127.0.0.1:8000")
    server.log.info(f"📝 Running with {workers} worker (development mode)")
    server.log.info(f"🔄 Auto-reload enabled - watching: {reload_extra_files}")
    server.log.info(f"📖 API docs available at: http://127.0.0.1:8000/docs")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("👋 Shutting down FastAPI development server")

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info(f"🔧 Worker {worker.pid} initialized (development mode)") 