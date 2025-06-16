# 🔧 Gunicorn Configuration Guide

## Issue Resolution: "No such user: 'fastapi'"

### Problem

When running `gunicorn --config scripts/setup/gunicorn.conf.py app.main:app`, you encountered:

```
Invalid value for user: fastapi
Error: No such user: 'fastapi'
```

### Root Cause

The production Gunicorn configuration was trying to set `user = "fastapi"` and `group = "fastapi"`, which are production-specific settings that don't exist on development machines.

## ✅ Solutions Implemented

### 1. **Environment-Aware Production Configuration**

Updated `scripts/setup/gunicorn.conf.py` to be environment-aware:

```python
# User/Group settings - only for production
environment = os.getenv("ENVIRONMENT", "development").lower()
if environment == "production":
    user = "fastapi"
    group = "fastapi"
else:
    # In development, run as current user (don't set user/group)
    pass
```

### 2. **Dedicated Development Configuration**

Created `scripts/setup/gunicorn.dev.conf.py` with development-friendly settings:

- No user/group restrictions
- Reduced worker count for easier debugging
- Enhanced logging for development
- Development-specific hooks and settings

### 3. **Development Startup Script**

Created `scripts/start_dev_gunicorn.sh` for easy development server startup.

## 🚀 Usage Options

### Option 1: Use Development Configuration (Recommended for Development)

```bash
# Using the dedicated development config
gunicorn --config scripts/setup/gunicorn.dev.conf.py app.main:app

# Or use the convenient startup script
./scripts/start_dev_gunicorn.sh
```

### Option 2: Use Production Configuration in Development Mode

```bash
# Set environment variable to avoid user/group issues
ENVIRONMENT=development gunicorn --config scripts/setup/gunicorn.conf.py app.main:app
```

### Option 3: Quick Development Server (No Config File)

```bash
# Simple development server without config file
gunicorn --bind 0.0.0.0:8000 --workers 2 --worker-class uvicorn.workers.UvicornWorker app.main:app
```

## 📋 Configuration Comparison

| Feature          | Development Config      | Production Config (Dev Mode) | Production Config (Prod Mode) |
| ---------------- | ----------------------- | ---------------------------- | ----------------------------- |
| **User/Group**   | Current user            | Current user                 | `fastapi:fastapi`             |
| **Workers**      | 2                       | CPU count \* 2 + 1           | CPU count \* 2 + 1            |
| **Log Level**    | `debug`                 | `info`                       | `info`                        |
| **Bind**         | `0.0.0.0:8000`          | `0.0.0.0:8000`               | `0.0.0.0:8000`                |
| **PID File**     | `/tmp/gunicorn-dev.pid` | `/tmp/gunicorn.pid`          | `/tmp/gunicorn.pid`           |
| **Process Name** | `fastapi-dev`           | `saas-app`                   | `saas-app`                    |

## 🔧 Testing Configurations

### Test Development Configuration

```bash
ENVIRONMENT=development gunicorn --config scripts/setup/gunicorn.dev.conf.py app.main:app --check-config
```

### Test Production Configuration (Development Mode)

```bash
ENVIRONMENT=development gunicorn --config scripts/setup/gunicorn.conf.py app.main:app --check-config
```

### Test Production Configuration (Production Mode)

```bash
# This will fail on development machines without 'fastapi' user
ENVIRONMENT=production gunicorn --config scripts/setup/gunicorn.conf.py app.main:app --check-config
```

## 🎯 Recommendations

### For Development

1. **Use the development configuration**: `scripts/setup/gunicorn.dev.conf.py`
2. **Use the startup script**: `./scripts/start_dev_gunicorn.sh`
3. **Set environment variables**: `ENVIRONMENT=development`

### For Production

1. **Create the fastapi user/group** on production servers
2. **Use the production configuration**: `scripts/setup/gunicorn.conf.py`
3. **Set environment variables**: `ENVIRONMENT=production`

## 🔍 Validation

Both configurations have been tested and validated:

- ✅ Development configuration works without user/group issues
- ✅ Production configuration respects environment variables
- ✅ All imports and paths are correctly updated
- ✅ FastAPI application loads successfully

## 📚 Additional Resources

### Environment Variables

```bash
# Development
export ENVIRONMENT=development
export LOG_LEVEL=debug
export GUNICORN_WORKERS=2

# Production
export ENVIRONMENT=production
export LOG_LEVEL=info
export GUNICORN_WORKERS=8
```

### Production User Setup (for production servers)

```bash
# Create fastapi user and group on production servers
sudo groupadd fastapi
sudo useradd -g fastapi -s /bin/bash -m fastapi
```

### Docker Usage

The Docker configurations have been updated to use the correct paths:

```dockerfile
CMD ["gunicorn", "--config", "scripts/setup/gunicorn.conf.py", "app.main:app"]
```

---

**Status**: ✅ **RESOLVED** - Gunicorn configuration issues fixed with environment-aware settings and dedicated development configuration.
