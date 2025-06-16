# 🚀 FastAPI PostgreSQL Boilerplate - Complete Setup Guide

A production-ready, enterprise-grade FastAPI boilerplate with PostgreSQL, Redis, plugin system, and comprehensive tooling for rapid application development.

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [🔧 Prerequisites](#-prerequisites)
- [⚡ Quick Start](#-quick-start)
- [🛠️ Development Setup](#️-development-setup)
- [🐳 Docker Setup](#-docker-setup)
- [🏭 Production Deployment](#-production-deployment)
- [🔌 Plugin System](#-plugin-system)
- [📊 Monitoring & Observability](#-monitoring--observability)
- [🧪 Testing](#-testing)
- [📚 API Documentation](#-api-documentation)
- [🔒 Security](#-security)
- [🚨 Troubleshooting](#-troubleshooting)

## 🎯 Overview

This boilerplate provides a complete foundation for building scalable FastAPI applications with:

- **FastAPI** with async/await support
- **PostgreSQL** with SQLAlchemy ORM and Alembic migrations
- **Redis** for caching and session management
- **Procrastinate** for background task processing
- **Plugin System** for modular architecture
- **Authentication & Authorization** with JWT and RBAC
- **Production-ready** configurations with Gunicorn
- **Monitoring** with Prometheus metrics
- **Docker** support for all environments
- **Comprehensive testing** with pytest

## ✨ Features

### Core Features

- ✅ **FastAPI** with automatic OpenAPI documentation
- ✅ **Async PostgreSQL** with SQLAlchemy 2.0+ and asyncpg
- ✅ **Redis** integration for caching and sessions
- ✅ **JWT Authentication** with refresh tokens
- ✅ **RBAC** (Role-Based Access Control)
- ✅ **Database Migrations** with Alembic
- ✅ **Background Tasks** with Procrastinate
- ✅ **WebSocket** support with Redis pub/sub
- ✅ **File Upload** handling with validation
- ✅ **Rate Limiting** with Redis backend
- ✅ **CORS** configuration
- ✅ **Security Headers** and middleware

### Enterprise Features

- ✅ **Plugin System** for modular architecture
- ✅ **Multi-tenancy** support
- ✅ **Monitoring** with Prometheus metrics
- ✅ **Health Checks** for orchestration
- ✅ **Graceful Shutdown** handling
- ✅ **Error Aggregation** and tracking
- ✅ **Security Auditing** with automated scans
- ✅ **Performance Monitoring** and profiling
- ✅ **Email Integration** with AWS SES
- ✅ **S3 Integration** for file storage

### Development Features

- ✅ **Hot Reload** in development
- ✅ **Code Formatting** with Ruff
- ✅ **Pre-commit Hooks** for code quality
- ✅ **Comprehensive Testing** with pytest
- ✅ **API Testing** with automated test generation
- ✅ **Database Seeding** for development
- ✅ **Docker Compose** for local development
- ✅ **Admin Interfaces** (Adminer, Redis Commander)

## 🔧 Prerequisites

### Required Software

- **Python 3.13+** (recommended) or Python 3.11+
- **PostgreSQL 15+**
- **Redis 7+**
- **Docker & Docker Compose** (for containerized setup)
- **Git**

### Optional Tools

- **uv** (recommended Python package manager)
- **Node.js** (for frontend integration)
- **nginx** (for production reverse proxy)

## ⚡ Quick Start

### Option 1: Local Development (Recommended)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd fastapi-postgres

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# 5. Start PostgreSQL and Redis (using Docker)
docker-compose up -d db redis

# 6. Run database migrations
alembic upgrade head

# 7. Start the development server
uv run fastapi dev
```

### Option 2: Full Docker Setup

```bash
# 1. Clone and navigate
git clone <your-repo-url>
cd fastapi-postgres

# 2. Start all services
docker-compose up -d

# 3. Run migrations
docker-compose exec app alembic upgrade head

# 4. Access the application
open http://localhost:8000
```

## 🛠️ Development Setup

### 1. Environment Configuration

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/fastapi_db
DATABASE_URL_WITHOUT_ASYNC=postgresql://postgres:password@localhost:5432/fastapi_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_TOKEN=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Settings
ENVIRONMENT=development
PROJECT_NAME=FastAPI PostgreSQL Boilerplate
VERSION=1.0.0
API_V1_STR=/api/v1
LOG_LEVEL=DEBUG

# Email Configuration (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# AWS Configuration (Optional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Monitoring (Optional)
PROMETHEUS_ENABLED=true
METRICS_ENABLED=true
```

### 2. Database Setup

```bash
# Start PostgreSQL (if using Docker)
docker-compose up -d db

# Or install PostgreSQL locally and create database
createdb fastapi_db

# Run migrations
alembic upgrade head

# Seed initial data (optional)
python -c "
import asyncio
from app.scripts.seed_rbac import seed_rbac
asyncio.run(seed_rbac())
"
```

### 3. Development Commands

```bash
# Start development server with hot reload
uv run fastapi dev

# Alternative: Start with Uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run with production-like settings
gunicorn --config scripts/setup/gunicorn.stable.conf.py app.main:app

# Run background worker
python -m procrastinate worker

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Format code
ruff format .

# Lint code
ruff check .

# Run security audit
bandit -r app/
safety check
```

### 4. Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history

# View current revision
alembic current
```

## 🐳 Docker Setup

### Development with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Execute commands in container
docker-compose exec app bash
docker-compose exec app alembic upgrade head
docker-compose exec app python -m pytest

# Stop services
docker-compose down

# Rebuild and start
docker-compose up -d --build
```

### Production Docker Setup

```bash
# Build production image
docker build -f Dockerfile.prod -t fastapi-app:latest .

# Run production container
docker run -d \
  --name fastapi-app \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" \
  -e JWT_SECRET_TOKEN="your-secret-key" \
  -e ENVIRONMENT=production \
  fastapi-app:latest

# Use production docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Available Services

| Service         | Port | Description                   |
| --------------- | ---- | ----------------------------- |
| FastAPI App     | 8000 | Main application              |
| PostgreSQL      | 5432 | Database                      |
| Redis           | 6379 | Cache & sessions              |
| Adminer         | 8080 | Database admin                |
| Redis Commander | 8081 | Redis admin                   |
| Nginx           | 80   | Reverse proxy                 |
| Prometheus      | 9090 | Metrics (monitoring setup)    |
| Grafana         | 3000 | Dashboards (monitoring setup) |

## 🏭 Production Deployment

### 1. Production Environment Variables

```bash
# Required Production Variables
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
JWT_SECRET_TOKEN=your-super-secure-secret-key-at-least-32-characters
REDIS_URL=redis://host:6379/0

# Optional Production Variables
GUNICORN_WORKERS=4
GUNICORN_BIND=0.0.0.0:8000
LOG_LEVEL=info
PROMETHEUS_ENABLED=true
SENTRY_DSN=your-sentry-dsn
```

### 2. Production Startup Commands

```bash
# Option 1: Use production script (recommended)
./scripts/start_production.sh

# Option 2: Direct Gunicorn command
ENVIRONMENT=production gunicorn --config scripts/setup/gunicorn.conf.py app.main:app

# Option 3: Stable configuration for local production testing
gunicorn --config scripts/setup/gunicorn.stable.conf.py app.main:app

# Option 4: Docker production
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Production Checklist

- [ ] Set strong `JWT_SECRET_TOKEN` (32+ characters)
- [ ] Configure production database with connection pooling
- [ ] Set up Redis with persistence
- [ ] Configure reverse proxy (nginx/Apache)
- [ ] Set up SSL certificates
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Set up log aggregation
- [ ] Configure backup strategies
- [ ] Set up health checks
- [ ] Configure rate limiting
- [ ] Review security headers
- [ ] Set up error tracking (Sentry)

### 4. Deployment Scripts

```bash
# Deploy to server
./scripts/deploy_to_server.sh

# Deploy to existing server
./scripts/deploy_to_existing_server.sh

# Setup production environment
python scripts/production_setup.py

# Run security audit
python scripts/security_audit.py
```

## 🔌 Plugin System

### Creating a New Plugin

```bash
# Generate plugin scaffold
python scaffold_generator_v4/main.py

# Follow the prompts to create:
# - Model definitions
# - API endpoints
# - Business logic
# - Database migrations
```

### Plugin Structure

```
app/plugins/your_plugin/
├── __init__.py          # Plugin registration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── service.py           # Business logic
├── router.py            # API endpoints
└── tasks.py             # Background tasks
```

### Plugin Example

```python
# app/plugins/your_plugin/__init__.py
from app.core.plugin_system import BasePlugin

class YourPlugin(BasePlugin):
    name = "your_plugin"
    version = "1.0.0"
    description = "Your plugin description"

    def initialize(self):
        # Plugin initialization logic
        pass

    def get_routes(self):
        from .router import router
        return router
```

### Managing Plugins

```bash
# List all plugins
curl http://localhost:8000/plugins/status

# Enable/disable plugins via environment variables
PLUGIN_YOUR_PLUGIN_ENABLED=true
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Readiness check (with dependencies)
curl http://localhost:8000/ready

# Detailed health check
curl http://localhost:8000/api/v1/health/detailed
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Application metrics
curl http://localhost:8000/api/v1/metrics
```

### Monitoring Setup

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3000
# Default: admin/admin

# Access Prometheus
open http://localhost:9090
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto
```

### Test Categories

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# API tests
pytest tests/api/

# Plugin tests
pytest tests/plugins/
```

### Test Configuration

```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### API Endpoints

| Endpoint                | Method | Description          |
| ----------------------- | ------ | -------------------- |
| `/api/v1/auth/login`    | POST   | User login           |
| `/api/v1/auth/register` | POST   | User registration    |
| `/api/v1/auth/refresh`  | POST   | Refresh token        |
| `/api/v1/users/me`      | GET    | Current user profile |
| `/api/v1/users/`        | GET    | List users (admin)   |
| `/health`               | GET    | Health check         |
| `/ready`                | GET    | Readiness check      |
| `/metrics`              | GET    | Prometheus metrics   |

### Authentication

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/users/me"
```

## 🔒 Security

### Security Features

- ✅ **JWT Authentication** with secure token handling
- ✅ **Password Hashing** with bcrypt
- ✅ **CORS** configuration
- ✅ **Rate Limiting** to prevent abuse
- ✅ **Security Headers** (HSTS, CSP, etc.)
- ✅ **Input Validation** with Pydantic
- ✅ **SQL Injection Protection** with SQLAlchemy
- ✅ **XSS Protection** with secure headers
- ✅ **CSRF Protection** for forms

### Security Auditing

```bash
# Run security audit
python scripts/security_audit.py

# Check for vulnerabilities
safety check

# Static security analysis
bandit -r app/

# Dependency security check
pip-audit
```

### Security Configuration

```python
# Security headers middleware
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database status
docker-compose ps db

# View database logs
docker-compose logs db

# Test connection
psql -h localhost -U postgres -d fastapi_db

# Reset database
docker-compose down -v
docker-compose up -d db
alembic upgrade head
```

#### 2. Redis Connection Issues

```bash
# Check Redis status
docker-compose ps redis

# Test Redis connection
redis-cli -h localhost ping

# View Redis logs
docker-compose logs redis
```

#### 3. Gunicorn Issues

```bash
# Check for port conflicts
lsof -i :8000

# Kill existing processes
pkill -f "gunicorn.*app.main:app"

# Use stable configuration
gunicorn --config scripts/setup/gunicorn.stable.conf.py app.main:app
```

#### 4. Plugin Issues

```bash
# Check plugin status
curl http://localhost:8000/plugins/status

# View plugin logs
docker-compose logs app | grep -i plugin

# Disable problematic plugin
export PLUGIN_PROBLEMATIC_PLUGIN_ENABLED=false
```

#### 5. Migration Issues

```bash
# Check migration status
alembic current

# View migration history
alembic history

# Reset migrations (DANGER: loses data)
alembic downgrade base
alembic upgrade head
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug
python -m debugpy --listen 5678 --wait-for-client -m uvicorn app.main:app --reload
```

### Performance Issues

```bash
# Profile application
python -m cProfile -o profile.stats -m uvicorn app.main:app

# Monitor resources
docker stats

# Check slow queries
# Enable PostgreSQL slow query log
```

### Getting Help

1. **Check logs**: `docker-compose logs app`
2. **Review documentation**: `/docs` endpoint
3. **Check health**: `/health` and `/ready` endpoints
4. **Plugin status**: `/plugins/status`
5. **Metrics**: `/metrics` endpoint

### Environment-Specific Issues

#### Development

- Ensure `.env` file is properly configured
- Check that all services are running
- Verify database migrations are applied

#### Production

- Verify environment variables are set
- Check that production secrets are secure
- Ensure proper resource limits
- Monitor application metrics

---

## 🎉 You're Ready!

Your FastAPI PostgreSQL boilerplate is now set up and ready for development. Start building your application by:

1. **Creating new plugins** for your business logic
2. **Customizing authentication** and authorization
3. **Adding your API endpoints** and business logic
4. **Configuring integrations** (email, storage, etc.)
5. **Setting up monitoring** and alerting
6. **Deploying to production** with confidence

Happy coding! 🚀

---

**Need help?** Check the troubleshooting section or review the comprehensive documentation in the `/docs` directory.
