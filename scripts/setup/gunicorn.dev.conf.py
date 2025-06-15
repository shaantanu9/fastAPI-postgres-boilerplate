"""Gunicorn Configuration for FastAPI Development.

This configuration provides development-friendly settings with automatic reloading,
simple logging, and no permission issues.
"""

# =============================================================================
# DEVELOPMENT CONFIGURATION
# =============================================================================

# Bind to localhost for development
bind = "0.0.0.0:8000"
backlog = 2048

# Single worker for development (easier debugging)
workers = int(os.getenv("GUNICORN_WORKERS", 2))  # Reduced for development
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 30
keepalive = 60

# =============================================================================
# LOGGING (DEVELOPMENT)
# =============================================================================
# Simple console logging for development
loglevel = os.getenv("LOG_LEVEL", "debug")  # More verbose for development
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr

# Simple log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Capture output from workers
capture_output = True

# =============================================================================
# DEVELOPMENT-FRIENDLY SETTINGS
# =============================================================================
# Don't preload app (allows better reloading)
preload_app = True

# Process naming
proc_name = "fastapi-dev"

# No daemon mode for development
daemon = False

# Simple PID file in current directory
pidfile = "/tmp/gunicorn-dev.pid"

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
def on_starting(server) -> None:
    """Called just before the master process is initialized."""
    server.log.info("Starting FastAPI application (Development Mode)...")


def on_reload(server) -> None:
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading FastAPI application...")


def when_ready(server) -> None:
    """Called just after the server is started."""
    server.log.info("FastAPI application ready to serve requests (Development Mode)")


def worker_int(worker) -> None:
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")


def pre_fork(server, worker) -> None:
    """Called just before a worker is forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def post_fork(server, worker) -> None:
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def post_worker_init(worker) -> None:
    """Called just after a worker has initialized the application."""
    worker.log.info(f"Worker initialized (pid: {worker.pid})")


def worker_abort(worker) -> None:
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker aborted (pid: {worker.pid})")


def pre_exec(server) -> None:
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")


def pre_request(worker, req) -> None:
    """Called just before a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path}")


def post_request(worker, req, environ, resp) -> None:
    """Called after a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path} - {resp.status_code}")


def child_exit(server, worker) -> None:
    """Called just after a worker has been exited, in the master process."""
    server.log.info(f"Worker exited (pid: {worker.pid})")


def worker_exit(server, worker) -> None:
    """Called just after a worker has been exited, in the worker process."""
    worker.log.info(f"Worker exiting (pid: {worker.pid})")


def nworkers_changed(server, new_value, old_value) -> None:
    """Called just after num_workers has been changed."""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")


def on_exit(server) -> None:
    """Called just before exiting Gunicorn."""
    server.log.info("Shutting down FastAPI application...")


# Environment variables for configuration
raw_env = [f"GUNICORN_WORKERS={workers}", f"LOG_LEVEL={loglevel}"]
