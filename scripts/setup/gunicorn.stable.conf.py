# Stable Gunicorn Configuration for FastAPI SaaS
import multiprocessing
import os
import platform

# Server socket
bind = "127.0.0.1:8000"  # Use localhost for local development
backlog = 2048

# Worker processes - reduced for stability
workers = int(os.getenv("GUNICORN_WORKERS", min(4, multiprocessing.cpu_count() + 1)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# CRITICAL: Disable preload_app to prevent plugin initialization issues
preload_app = False

# Timeouts - increased for complex app initialization
timeout = 120  # Increased timeout for plugin loading
keepalive = 60
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
loglevel = os.getenv("LOG_LEVEL", "info")

# Process naming
proc_name = "saas-app"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"

# User/Group settings - only for production
environment = os.getenv("ENVIRONMENT", "development").lower()
if environment == "production" and platform.system() == "Linux":
    # Only set user/group on Linux production servers
    user = os.getenv("GUNICORN_USER", "fastapi")
    group = os.getenv("GUNICORN_GROUP", "fastapi")

# Performance tuning
if platform.system() == "Linux" and os.path.exists("/dev/shm"):
    worker_tmp_dir = "/dev/shm"
else:
    worker_tmp_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

forwarded_allow_ips = "*"
secure_scheme_headers = {
    "X-FORWARDED-PROTOCOL": "ssl",
    "X-FORWARDED-PROTO": "https",
    "X-FORWARDED-SSL": "on",
}

# Simplified hooks to reduce logging noise
def on_starting(server) -> None:
    """Called just before the master process is initialized."""
    server.log.info("🚀 Starting FastAPI SaaS application...")

def when_ready(server) -> None:
    """Called just after the server is started."""
    server.log.info("✅ FastAPI SaaS application ready to serve requests")
    server.log.info(f"📊 Workers: {workers}, Environment: {environment}")

def on_exit(server) -> None:
    """Called just before exiting Gunicorn."""
    server.log.info("🛑 Shutting down FastAPI SaaS application...")

def worker_abort(worker) -> None:
    """Called when a worker received the SIGABRT signal."""
    worker.log.error(f"💥 Worker aborted (pid: {worker.pid})")

def child_exit(server, worker) -> None:
    """Called just after a worker has been exited, in the master process."""
    server.log.warning(f"⚠️ Worker exited (pid: {worker.pid})")

# Environment variables for configuration
raw_env = [
    f"GUNICORN_WORKERS={workers}", 
    f"LOG_LEVEL={loglevel}",
    f"ENVIRONMENT={environment}"
] 