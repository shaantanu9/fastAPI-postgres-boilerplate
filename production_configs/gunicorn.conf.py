"""Gunicorn Configuration for FastAPI Production Deployment.

This configuration provides production-ready settings for Gunicorn with Uvicorn workers,
including proper worker management, logging, timeouts, and graceful shutdown handling.
"""

import multiprocessing
import os
import tempfile
from pathlib import Path


# =============================================================================
# SERVER SOCKET
# =============================================================================
def get_bind_address() -> str:
    """Get appropriate bind address based on environment."""
    environment = os.getenv("ENVIRONMENT", "production").lower()

    if environment == "development":
        # Use localhost for development
        return "127.0.0.1:8000"
    if os.getenv("USE_UNIX_SOCKET", "true").lower() == "true":
        # Use Unix socket for production (better performance with reverse proxy)
        socket_dir = Path(os.getenv("RUN_DIR", "/run/fastapi"))
        try:
            socket_dir.mkdir(parents=True, exist_ok=True)
            return f"unix:{socket_dir}/gunicorn.sock"
        except (PermissionError, OSError):
            # Fallback to TCP if socket creation fails
            return "0.0.0.0:8000"
    else:
        # Use TCP
        return "0.0.0.0:8000"


bind = get_bind_address()

# =============================================================================
# WORKER PROCESSES
# =============================================================================
# Number of worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Worker class - use uvicorn workers for async FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Maximum number of requests a worker will process before restarting
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 100))

# Worker timeout (seconds) - time to wait for requests on a Keep-Alive connection
timeout = int(os.getenv("GUNICORN_TIMEOUT", 30))

# Timeout for graceful worker restarts (seconds)
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 30))

# Time to wait for worker to handle request after receiving SIGTERM
kill_timeout = int(os.getenv("GUNICORN_KILL_TIMEOUT", 10))

# =============================================================================
# WORKER CONNECTIONS
# =============================================================================
# Maximum number of simultaneous clients per worker
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", 1000))


# =============================================================================
# LOGGING
# =============================================================================
# Log directory - handle permissions gracefully
def get_log_dir():
    """Get appropriate log directory based on environment and permissions."""
    preferred_log_dir = os.getenv("LOG_DIR", "/var/log/fastapi")

    try:
        # Try to create/access the preferred directory
        log_dir = Path(preferred_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        # Test write access
        test_file = log_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return log_dir
    except (PermissionError, OSError):
        # Fallback to user's home directory or temp directory
        if os.getenv("HOME"):
            fallback_dir = Path(os.getenv("HOME")) / "logs" / "fastapi"
        else:
            fallback_dir = Path(tempfile.gettempdir()) / "fastapi_logs"

        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


log_dir = get_log_dir()

# Access log file
accesslog = str(log_dir / "access.log")

# Error log file
errorlog = str(log_dir / "error.log")

# Log level
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Access log format
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Capture output from workers
capture_output = True

# Enable access logging
accesslog = (
    accesslog if os.getenv("GUNICORN_ACCESS_LOG", "true").lower() == "true" else None
)

# =============================================================================
# PROCESS NAMING
# =============================================================================
# Set the process title
proc_name = os.getenv("GUNICORN_PROC_NAME", "fastapi")

# =============================================================================
# WORKER PROCESS
# =============================================================================
# User to run workers as
user = os.getenv("GUNICORN_USER", None)
group = os.getenv("GUNICORN_GROUP", None)

# =============================================================================
# SSL
# =============================================================================
# SSL keyfile and certfile paths (if using HTTPS)
keyfile = os.getenv("GUNICORN_KEYFILE", None)
certfile = os.getenv("GUNICORN_CERTFILE", None)

# =============================================================================
# SERVER MECHANICS
# =============================================================================
# Daemonize the Gunicorn process
daemon = False


# PID file path - handle permissions gracefully
def get_pidfile_path():
    """Get appropriate PID file path based on environment and permissions."""
    preferred_pidfile = os.getenv("GUNICORN_PIDFILE", "/run/fastapi/gunicorn.pid")

    try:
        pidfile_dir = Path(preferred_pidfile).parent
        pidfile_dir.mkdir(parents=True, exist_ok=True)
        return preferred_pidfile
    except (PermissionError, OSError):
        # Fallback to temp directory
        fallback_pidfile = Path(tempfile.gettempdir()) / "gunicorn_fastapi.pid"
        return str(fallback_pidfile)


pidfile = get_pidfile_path()

# =============================================================================
# WORKER CLASS SETTINGS
# =============================================================================
# Uvicorn worker specific settings
worker_class = "uvicorn.workers.UvicornWorker"

# Additional uvicorn options
uvicorn_options = {
    "loop": "uvloop",  # Use uvloop for better performance
    "http": "httptools",  # Use httptools for better HTTP parsing
    "lifespan": "on",  # Enable lifespan events
    "access_log": True,
    "use_colors": False,  # Disable colors in production
}

# =============================================================================
# PERFORMANCE TUNING
# =============================================================================
# Pre-load application code before forking workers
preload_app = True

# Keep alive timeout
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 2))

# =============================================================================
# SECURITY
# =============================================================================
# Limit request line size
limit_request_line = int(os.getenv("GUNICORN_LIMIT_REQUEST_LINE", 4096))

# Limit request field size
limit_request_field_size = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELD_SIZE", 8190))

# Limit number of request header fields
limit_request_fields = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELDS", 100))


# =============================================================================
# HOOKS
# =============================================================================
def on_starting(server) -> None:
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn server")


def on_reload(server) -> None:
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn server")


def when_ready(server) -> None:
    """Called just after the server is started."""
    server.log.info(f"Gunicorn server started on {bind}")
    server.log.info(f"Running with {workers} workers")


def worker_int(worker) -> None:
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received interrupt signal")


def on_exit(server) -> None:
    """Called just before exiting."""
    server.log.info("Shutting down Gunicorn server")


def pre_fork(server, worker) -> None:
    """Called just before a worker is forked."""
    server.log.info(f"Forking worker {worker.pid}")


def post_fork(server, worker) -> None:
    """Called just after a worker has been forked."""
    worker.log.info(f"Worker {worker.pid} started")


def post_worker_init(worker) -> None:
    """Called just after a worker has initialized the application."""
    worker.log.info(f"Worker {worker.pid} initialized")


def worker_abort(worker) -> None:
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} aborted")


def pre_exec(server) -> None:
    """Called just before a new master process is forked."""
    server.log.info("Pre-exec hook called")


def pre_request(worker, req) -> None:
    """Called just before a worker processes the request."""
    worker.log.debug(f"Processing request: {req.method} {req.path}")


def post_request(worker, req, environ, resp) -> None:
    """Called after a worker processes the request."""
    worker.log.debug(f"Completed request: {req.method} {req.path} - {resp.status}")


# =============================================================================
# ENVIRONMENT-SPECIFIC CONFIGURATIONS
# =============================================================================
# Development configuration
if os.getenv("ENVIRONMENT", "production").lower() == "development":
    reload = True
    reload_engine = "auto"
    reload_extra_files = ["app/"]
    workers = 1
    loglevel = "debug"
    preload_app = False

# Staging configuration
elif os.getenv("ENVIRONMENT", "production").lower() == "staging":
    workers = max(2, multiprocessing.cpu_count())
    loglevel = "info"
    max_requests = 500

# Production configuration (default)
else:
    workers = multiprocessing.cpu_count() * 2 + 1
    loglevel = "warning"
    max_requests = 1000
    preload_app = True


# =============================================================================
# GUNICORN CONFIG VALIDATION
# =============================================================================
def validate_config() -> None:
    """Validate configuration settings."""
    if workers <= 0:
        msg = "Workers must be greater than 0"
        raise ValueError(msg)

    if timeout <= 0:
        msg = "Timeout must be greater than 0"
        raise ValueError(msg)

    if max_requests <= 0:
        msg = "Max requests must be greater than 0"
        raise ValueError(msg)


# Run validation
validate_config()

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
        },
        "access": {
            "format": "%(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "error_file": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": errorlog,
            "maxBytes": 50 * 1024 * 1024,  # 50MB
            "backupCount": 10,
        },
    },
    "loggers": {
        "gunicorn.error": {
            "level": loglevel.upper(),
            "handlers": ["default", "error_file"],
            "propagate": False,
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["access"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["access"],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
}
