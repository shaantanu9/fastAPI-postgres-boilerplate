# Minimal Gunicorn Configuration for Debugging
import os

# Basic settings
bind = "127.0.0.1:8000"
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "debug"

# Disable problematic settings
preload_app = False
daemon = False

# No user/group settings
# No worker_tmp_dir settings
# No SSL settings

# Simple hooks for debugging
def on_starting(server):
    server.log.info("=== STARTING SERVER ===")

def when_ready(server):
    server.log.info("=== SERVER READY ===")

def on_exit(server):
    server.log.info("=== SHUTTING DOWN ===")

def worker_abort(worker):
    worker.log.error(f"=== WORKER ABORTED: {worker.pid} ===")

def child_exit(server, worker):
    server.log.info(f"=== WORKER EXITED: {worker.pid} ===") 