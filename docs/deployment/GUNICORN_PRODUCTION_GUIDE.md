# FastAPI Gunicorn Production Guide

## 🎯 **Overview**

This guide provides a comprehensive setup and configuration for running FastAPI applications with Gunicorn + Uvicorn workers in production environments. Our implementation includes enterprise-grade features, development tools, and automated deployment capabilities.

---

## 📋 **Table of Contents**

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Configuration Files](#configuration-files)
4. [Issues Found & Fixes](#issues-found--fixes)
5. [Development Setup](#development-setup)
6. [Production Deployment](#production-deployment)
7. [Testing & Validation](#testing--validation)
8. [Performance Tuning](#performance-tuning)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## 🚀 **Quick Start**

### **Development (Local Testing)**

```bash
# Test all configurations
./scripts/test_gunicorn.sh

# Start development server
./scripts/start_dev.sh
```

### **Production Deployment**

```bash
# Automated deployment
./production_configs/scripts/deploy.sh

# Manual service management
sudo systemctl start fastapi
sudo systemctl status fastapi
```

---

## 🏗️ **Architecture Overview**

### **Process Architecture**

```mermaid
graph TD
    A[Nginx Reverse Proxy] --> B[Gunicorn Master Process]
    B --> C[Uvicorn Worker 1]
    B --> D[Uvicorn Worker 2]
    B --> E[Uvicorn Worker N]

    F[Systemd/Supervisor] --> B
    F --> G[Health Monitor]
    F --> H[Log Manager]

    C --> I[FastAPI Application]
    D --> I
    E --> I

    I --> J[PostgreSQL Database]
    I --> K[Background Tasks]
    I --> L[Concurrent Processing]
```

### **Configuration Hierarchy**

```
├── gunicorn.dev.conf.py          # Development configuration
├── production_configs/
│   └── gunicorn.conf.py          # Production configuration
├── scripts/
│   ├── start_dev.sh              # Development startup
│   └── test_gunicorn.sh          # Configuration testing
└── production_configs/
    ├── systemd/fastapi.service   # Systemd service
    ├── supervisor/fastapi.conf   # Supervisor config
    └── scripts/deploy.sh         # Automated deployment
```

---

## ⚙️ **Configuration Files**

### **1. Production Configuration** (`production_configs/gunicorn.conf.py`)

**Key Features:**

- Environment-aware worker scaling
- Smart path resolution with fallbacks
- Unix socket with TCP fallback
- Comprehensive logging
- Security settings
- Performance optimization

**Configuration Highlights:**

```python
# Auto-scaling workers based on CPU cores
workers = multiprocessing.cpu_count() * 2 + 1

# Environment-aware binding
bind = get_bind_address()  # Unix socket or TCP based on environment

# Smart log directory with fallbacks
log_dir = get_log_dir()    # /var/log/fastapi or $HOME/logs

# Uvicorn workers for async FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Performance settings
preload_app = True
max_requests = 1000
timeout = 30
graceful_timeout = 30
```

### **2. Development Configuration** (`gunicorn.dev.conf.py`)

**Key Features:**

- Single worker for easier debugging
- Auto-reload on code changes
- Console logging
- Development-friendly timeouts

**Configuration Highlights:**

```python
# Development settings
bind = "127.0.0.1:8000"
workers = 1
reload = True
reload_engine = "auto"
reload_extra_files = ["app/"]

# Development logging
loglevel = "debug"
accesslog = "-"  # stdout
errorlog = "-"   # stderr

# No preload for better reloading
preload_app = False
```

### **3. Systemd Service** (`production_configs/systemd/fastapi.service`)

**Key Features:**

- Auto-restart on failure
- Security hardening
- Resource limits
- Graceful shutdown

```ini
[Unit]
Description=FastAPI Production Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/fastapi
ExecStart=/var/www/fastapi/.venv/bin/gunicorn \
    --config /var/www/fastapi/production_configs/gunicorn.conf.py \
    app.main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## ❌ **Issues Found & Fixes**

### **1. Permission Errors** ❌ → ✅

**Problem:**

```bash
PermissionError: [Errno 13] Permission denied: '/var/log/fastapi'
```

**Root Cause:** Hardcoded production paths in development environment

**Solution:** Smart path resolution with graceful fallbacks

```python
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
        print(f"Warning: Cannot write to {preferred_log_dir}, using {fallback_dir}")
        return fallback_dir
```

### **2. Duplicate Configuration Variables** ❌ → ✅

**Problem:** Configuration variables defined multiple times

- `timeout` defined twice
- `max_requests` defined twice

**Solution:** Removed duplicates, kept single authoritative definitions

### **3. Inflexible Socket Configuration** ❌ → ✅

**Problem:** Unix socket paths hardcoded for production only

**Solution:** Environment-aware socket configuration

```python
def get_bind_address():
    """Get appropriate bind address based on environment."""
    environment = os.getenv("ENVIRONMENT", "production").lower()

    if environment == "development":
        # Use localhost for development
        return "127.0.0.1:8000"
    elif os.getenv("USE_UNIX_SOCKET", "true").lower() == "true":
        # Use Unix socket for production (better performance with reverse proxy)
        socket_dir = Path(os.getenv("RUN_DIR", "/run/fastapi"))
        try:
            socket_dir.mkdir(parents=True, exist_ok=True)
            return f"unix:{socket_dir}/gunicorn.sock"
        except (PermissionError, OSError):
            # Fallback to TCP if socket creation fails
            print(f"Warning: Cannot create socket directory {socket_dir}, using TCP")
            return "0.0.0.0:8000"
    else:
        # Use TCP
        return "0.0.0.0:8000"
```

### **4. Missing Development Tools** ❌ → ✅

**Problem:** No easy way to run Gunicorn locally for development

**Solution:** Created comprehensive development tools

- `gunicorn.dev.conf.py` - Development configuration
- `scripts/start_dev.sh` - Development startup script
- `scripts/test_gunicorn.sh` - Configuration testing

### **5. PID File Permission Issues** ❌ → ✅

**Problem:** PID file path hardcoded to `/run/fastapi/gunicorn.pid`

**Solution:** Smart PID file path resolution

```python
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
        print(f"Warning: Cannot write to {preferred_pidfile}, using {fallback_pidfile}")
        return str(fallback_pidfile)
```

---

## 💻 **Development Setup**

### **1. Development Configuration Features**

```python
# Development-optimized settings
bind = "127.0.0.1:8000"           # Localhost only
workers = 1                        # Single worker for debugging
reload = True                      # Auto-reload on changes
reload_engine = "auto"             # Auto-detect changes
reload_extra_files = ["app/"]      # Watch app directory
loglevel = "debug"                 # Verbose logging
preload_app = False                # Better for development
timeout = 120                      # Longer for debugging
```

### **2. Development Startup Script** (`scripts/start_dev.sh`)

**Features:**

- Virtual environment detection/activation
- Dependency checking
- Environment variable setup
- User-friendly output

**Usage:**

```bash
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

**Output:**

```bash
🚀 Starting FastAPI Development Server
=======================================

🔧 Configuration:
   - Environment: development
   - Log Directory: /Users/user/logs
   - Config File: gunicorn.dev.conf.py
   - Bind Address: 127.0.0.1:8000

🏃 Starting server...
📖 API Documentation: http://127.0.0.1:8000/docs
🔍 Health Check: http://127.0.0.1:8000/health
```

### **3. Alternative Development Methods**

```bash
# Method 1: Development script (Recommended)
./scripts/start_dev.sh

# Method 2: Direct Gunicorn command
gunicorn -c gunicorn.dev.conf.py app.main:app

# Method 3: Traditional Uvicorn (still works)
uvicorn app.main:app --reload

# Method 4: Production config in development mode
ENVIRONMENT=development gunicorn -c production_configs/gunicorn.conf.py app.main:app
```

---

## 🏭 **Production Deployment**

### **1. Automated Deployment**

Use the comprehensive deployment script:

```bash
# Full automated deployment
./production_configs/scripts/deploy.sh

# Deployment with options
./production_configs/scripts/deploy.sh --process-manager systemd
./production_configs/scripts/deploy.sh --skip-nginx
```

**Deployment Script Features:**

- System package installation
- User and directory setup
- Python virtual environment configuration
- Gunicorn configuration
- Systemd/Supervisor service setup
- Nginx reverse proxy configuration
- SSL/TLS setup with security headers
- Log rotation configuration
- Firewall setup
- Health check script creation

### **2. Manual Deployment Steps**

#### Step 1: System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-venv python3-dev nginx supervisor
```

#### Step 2: Application Setup

```bash
# Create directories
sudo mkdir -p /var/www/fastapi /var/log/fastapi /run/fastapi

# Set permissions
sudo chown -R www-data:www-data /var/www/fastapi /var/log/fastapi /run/fastapi

# Deploy application code
sudo cp -r . /var/www/fastapi/
sudo chown -R www-data:www-data /var/www/fastapi/
```

#### Step 3: Python Environment

```bash
cd /var/www/fastapi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Step 4: Service Configuration

```bash
# Systemd service
sudo cp production_configs/systemd/fastapi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi

# Or Supervisor
sudo cp production_configs/supervisor/fastapi.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start fastapi
```

### **3. Environment Variables**

**Production Environment Variables:**

```bash
# Environment
export ENVIRONMENT=production
export LOG_DIR=/var/log/fastapi
export RUN_DIR=/run/fastapi
export USE_UNIX_SOCKET=true

# Gunicorn tuning
export GUNICORN_WORKERS=8
export GUNICORN_MAX_REQUESTS=1000
export GUNICORN_TIMEOUT=30
export GUNICORN_LOG_LEVEL=warning

# Application
export DATABASE_URL=postgresql://user:pass@localhost/db
export SECRET_KEY=your-secret-key
```

---

## 🧪 **Testing & Validation**

### **1. Configuration Testing Script** (`scripts/test_gunicorn.sh`)

**Features:**

- Tests all configuration files
- Validates FastAPI app import
- Checks dependencies
- Provides detailed output

**Usage:**

```bash
chmod +x scripts/test_gunicorn.sh
./scripts/test_gunicorn.sh
```

**Test Results:**

```bash
🧪 Testing Gunicorn Configurations
====================================
✅ PASSED: Development Config Check
✅ PASSED: Production Config (Dev Mode)
✅ PASSED: Production Config (Staging Mode)
✅ PASSED: Production Config (Production TCP)
✅ PASSED: FastAPI App Import
✅ PASSED: Uvicorn Worker Import
✅ PASSED: Gunicorn Installation
✅ PASSED: Required Dependencies
====================================
✅ Tests Passed: 8
❌ Tests Failed: 0
====================================
🎉 All tests passed! Gunicorn configuration is ready.
```

### **2. Individual Configuration Testing**

```bash
# Test development configuration
gunicorn --check-config -c gunicorn.dev.conf.py app.main:app

# Test production configuration (development mode)
ENVIRONMENT=development LOG_DIR=$HOME/logs gunicorn --check-config -c production_configs/gunicorn.conf.py app.main:app

# Test production configuration (staging mode)
ENVIRONMENT=staging LOG_DIR=$HOME/logs gunicorn --check-config -c production_configs/gunicorn.conf.py app.main:app

# Test production configuration (production mode with TCP)
ENVIRONMENT=production LOG_DIR=$HOME/logs USE_UNIX_SOCKET=false gunicorn --check-config -c production_configs/gunicorn.conf.py app.main:app
```

### **3. Application Testing**

```bash
# Test FastAPI app import
python -c "from app.main import app; print('FastAPI app imported successfully')"

# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/detailed

# Test API documentation
curl http://localhost:8000/docs
curl http://localhost:8000/redoc
```

---

## ⚡ **Performance Tuning**

### **1. Worker Configuration**

```python
# CPU-bound applications
workers = multiprocessing.cpu_count() * 2 + 1

# I/O-bound applications
workers = multiprocessing.cpu_count() + 1
worker_connections = 2000

# Memory-constrained environments
workers = 2
max_requests = 500
max_requests_jitter = 50
```

### **2. Environment-Specific Tuning**

```python
# Development
if os.getenv("ENVIRONMENT") == "development":
    workers = 1                    # Single worker for debugging
    reload = True                  # Auto-reload
    preload_app = False           # Better for development
    loglevel = "debug"            # Verbose logging

# Staging
elif os.getenv("ENVIRONMENT") == "staging":
    workers = max(2, multiprocessing.cpu_count())
    loglevel = "info"
    max_requests = 500

# Production
else:
    workers = multiprocessing.cpu_count() * 2 + 1
    loglevel = "warning"
    max_requests = 1000
    preload_app = True            # Better performance
```

### **3. Memory Management**

```python
# Worker restart settings
max_requests = 1000               # Restart after N requests
max_requests_jitter = 100         # Add randomness

# Timeout settings
timeout = 30                      # Worker timeout
graceful_timeout = 30             # Graceful shutdown timeout
kill_timeout = 10                 # Force kill timeout
```

### **4. Performance Monitoring**

```bash
# Monitor worker processes
ps aux | grep gunicorn

# Check memory usage
ps aux | grep gunicorn | awk '{sum+=$6} END {print "Total Memory:", sum/1024, "MB"}'

# Monitor connections
ss -tuln | grep :8000

# Check logs for performance issues
tail -f /var/log/fastapi/access.log
tail -f /var/log/fastapi/error.log
```

---

## 🔧 **Troubleshooting**

### **1. Common Issues**

#### Service Won't Start

```bash
# Check service status
sudo systemctl status fastapi

# Check logs
sudo journalctl -u fastapi --no-pager -n 50

# Test configuration
gunicorn --check-config -c production_configs/gunicorn.conf.py app.main:app

# Test app import
python -c "from app.main import app; print('OK')"
```

#### Permission Errors

```bash
# Check file permissions
ls -la /var/www/fastapi/
ls -la /var/log/fastapi/
ls -la /run/fastapi/

# Fix permissions
sudo chown -R www-data:www-data /var/www/fastapi/
sudo chown -R www-data:www-data /var/log/fastapi/
sudo chown -R www-data:www-data /run/fastapi/
```

#### High Memory Usage

```bash
# Check memory per worker
ps aux | grep gunicorn

# Reduce max_requests
export GUNICORN_MAX_REQUESTS=500

# Restart service
sudo systemctl restart fastapi
```

#### Slow Response Times

```bash
# Check worker count
ps aux | grep uvicorn | wc -l

# Increase workers
export GUNICORN_WORKERS=12

# Check database connections
# Monitor health endpoint: /health/detailed
```

### **2. Debugging Commands**

```bash
# Check Gunicorn version
gunicorn --version

# Test configurations
./scripts/test_gunicorn.sh

# Check process tree
pstree -p $(pgrep -f gunicorn)

# Monitor real-time logs
tail -f /var/log/fastapi/error.log

# Check system resources
htop
free -h
df -h
```

### **3. Log Analysis**

```bash
# Access log analysis
grep "POST" /var/log/fastapi/access.log | wc -l
grep "500" /var/log/fastapi/access.log
grep "slow" /var/log/fastapi/error.log

# Error patterns
grep -i "error" /var/log/fastapi/error.log | tail -10
grep -i "timeout" /var/log/fastapi/error.log
grep -i "memory" /var/log/fastapi/error.log
```

---

## 💡 **Best Practices**

### **1. Configuration Management**

- ✅ Use environment variables for configuration
- ✅ Separate development and production configs
- ✅ Implement smart fallbacks for paths
- ✅ Test configurations before deployment
- ✅ Use version control for configurations

### **2. Security**

- ✅ Run as non-root user (www-data)
- ✅ Use Unix sockets when possible
- ✅ Implement request size limits
- ✅ Set appropriate timeouts
- ✅ Use security headers in Nginx

### **3. Performance**

- ✅ Use appropriate worker count for workload
- ✅ Enable preload_app for production
- ✅ Configure worker recycling
- ✅ Monitor resource usage
- ✅ Implement health checks

### **4. Monitoring**

- ✅ Set up structured logging
- ✅ Implement log rotation
- ✅ Monitor health endpoints
- ✅ Track performance metrics
- ✅ Set up alerting

### **5. Deployment**

- ✅ Use automated deployment scripts
- ✅ Test in staging environment
- ✅ Implement graceful restarts
- ✅ Have rollback procedures
- ✅ Document deployment process

---

## 📚 **Reference**

### **Commands Quick Reference**

```bash
# Development
./scripts/start_dev.sh                    # Start development server
./scripts/test_gunicorn.sh               # Test configurations

# Production
./production_configs/scripts/deploy.sh   # Deploy to production
sudo systemctl start fastapi            # Start service
sudo systemctl stop fastapi             # Stop service
sudo systemctl restart fastapi          # Restart service
sudo systemctl status fastapi           # Check status
sudo journalctl -u fastapi -f           # Follow logs

# Testing
gunicorn --check-config -c gunicorn.dev.conf.py app.main:app
curl http://localhost:8000/health
```

### **Environment Variables**

```bash
# Core settings
ENVIRONMENT=development|staging|production
LOG_DIR=/path/to/logs
RUN_DIR=/path/to/run
USE_UNIX_SOCKET=true|false

# Gunicorn settings
GUNICORN_WORKERS=8
GUNICORN_MAX_REQUESTS=1000
GUNICORN_TIMEOUT=30
GUNICORN_LOG_LEVEL=debug|info|warning|error
```

### **File Locations**

```
Configuration Files:
├── gunicorn.dev.conf.py                 # Development config
├── production_configs/gunicorn.conf.py  # Production config
├── production_configs/systemd/fastapi.service
├── production_configs/supervisor/fastapi.conf

Scripts:
├── scripts/start_dev.sh                 # Development startup
├── scripts/test_gunicorn.sh            # Configuration testing
└── production_configs/scripts/deploy.sh # Production deployment

Logs (Production):
├── /var/log/fastapi/access.log
├── /var/log/fastapi/error.log
└── /var/log/supervisor/fastapi_*.log

Runtime (Production):
├── /run/fastapi/gunicorn.sock           # Unix socket
└── /run/fastapi/gunicorn.pid           # PID file
```

---

## 🎉 **Conclusion**

This FastAPI Gunicorn setup provides:

✅ **Enterprise-Grade Configuration** - Production-ready with all best practices  
✅ **Development Tools** - Easy local development and testing  
✅ **Automated Deployment** - One-command production deployment  
✅ **Comprehensive Monitoring** - Health checks and logging  
✅ **Security Hardening** - Process isolation and security headers  
✅ **Performance Optimization** - Tuned for high-traffic applications

Your setup is ready for production deployment with confidence! 🚀
