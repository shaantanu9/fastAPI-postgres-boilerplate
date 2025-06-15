# 🚀 FastAPI SaaS Deployment Guide

## 📋 Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Domain name (for production)
- SSL Certificate (Let's Encrypt recommended)

## 🛠️ Environment Configuration

### Required Environment Variables

```bash
# Application
APP_NAME="FastAPI SaaS"
ENVIRONMENT=production  # development, production, staging, test
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
JWT_SECRET_TOKEN=your-super-secret-jwt-key-change-this-min-32-chars
EMAIL_SECRET_KEY=your-super-secret-email-key-change-this-min-32-chars

# External Services
REDIS_URL=redis://localhost:6379/0
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FRONTEND_URL=https://yourdomain.com

# Production Specific
DOMAIN=yourdomain.com
ACME_EMAIL=admin@yourdomain.com
POSTGRES_PASSWORD=super-secure-production-password
```

## 🏗️ Development Setup

### 1. Clone and Setup

```bash
git clone <repository>
cd fastapi-saas
cp .env.example .env  # Update with your values
```

### 2. Start Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Access services
# - App: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Database Admin: http://localhost:8080
# - Redis Admin: http://localhost:8081
```

### 3. Run Migrations

```bash
# Create migration (if needed)
docker-compose exec app alembic revision --autogenerate -m "Add organizations"

# Apply migrations
docker-compose exec app alembic upgrade head
```

## 🎯 Production Deployment

### 1. Server Setup

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
sudo mkdir -p /opt/fastapi-saas
cd /opt/fastapi-saas
```

### 2. Environment Configuration

Create production environment file:

```bash
# Create .env.production
cat > .env.production << EOF
APP_NAME="FastAPI SaaS"
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://saas_user:${DB_PASSWORD}@db:5432/fastapi_saas_prod
DATABASE_URL_WITHOUT_ASYNC=postgresql://saas_user:${DB_PASSWORD}@db:5432/fastapi_saas_prod
POSTGRES_DB=fastapi_saas_prod
POSTGRES_USER=saas_user
POSTGRES_PASSWORD=${DB_PASSWORD}

# Security
JWT_SECRET_TOKEN=${JWT_SECRET}
EMAIL_SECRET_KEY=${EMAIL_SECRET}

# External Services
REDIS_URL=redis://redis:6379/0
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASS}
EMAIL_FROM="FastAPI SaaS <noreply@${DOMAIN}>"

# Domain
DOMAIN=${DOMAIN}
FRONTEND_URL=https://${DOMAIN}
ACME_EMAIL=admin@${DOMAIN}

# Monitoring
GRAFANA_PASSWORD=${GRAFANA_PASS}
TRAEFIK_AUTH=${TRAEFIK_AUTH_HASH}

# Optional: External APIs
STRIPE_SECRET_KEY=${STRIPE_SECRET}
SENTRY_DSN=${SENTRY_DSN}
EOF
```

### 3. SSL and Traefik Setup

```bash
# Create Traefik network
docker network create traefik-network

# Create Let's Encrypt directory
mkdir -p ./letsencrypt
chmod 600 ./letsencrypt
```

### 4. Deploy Application

```bash
# Build and start production
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f app
```

### 5. Initial Setup

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec app migrate

# Seed initial data
docker-compose -f docker-compose.prod.yml exec app seed-data

# Create superuser (if needed)
docker-compose -f docker-compose.prod.yml exec app python -c "
import asyncio
from app.scripts.create_superuser import create_superuser
asyncio.run(create_superuser('admin@${DOMAIN}', 'secure-password'))
"
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and push Docker image
        run: |
          docker build -t ${{ secrets.DOCKER_REGISTRY }}/saas-app:${{ github.sha }} .
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin ${{ secrets.DOCKER_REGISTRY }}
          docker push ${{ secrets.DOCKER_REGISTRY }}/saas-app:${{ github.sha }}

      - name: Deploy to production
        uses: appleboy/ssh-action@v0.1.5
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/fastapi-saas
            export APP_VERSION=${{ github.sha }}
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker-compose -f docker-compose.prod.yml exec app migrate
```

## 📊 Monitoring & Maintenance

### 1. Health Monitoring

```bash
# Application health
curl https://yourdomain.com/api/v1/health/ready

# Service status
docker-compose -f docker-compose.prod.yml ps

# Resource usage
docker stats
```

### 2. Log Management

```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f app

# View specific service logs
docker-compose -f docker-compose.prod.yml logs -f db
docker-compose -f docker-compose.prod.yml logs -f redis

# Log rotation (add to crontab)
0 2 * * * docker system prune -f
```

### 3. Database Backup

```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U saas_user fastapi_saas_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker-compose -f docker-compose.prod.yml exec -T db psql -U saas_user fastapi_saas_prod < backup_file.sql
```

### 4. Performance Monitoring

Access monitoring dashboards:

- Grafana: `https://grafana.yourdomain.com`
- Traefik: `https://traefik.yourdomain.com`
- Prometheus: `http://server-ip:9090`

## 🔧 Common Operations

### Scaling

```bash
# Scale application replicas
docker-compose -f docker-compose.prod.yml up -d --scale app=5

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=3
```

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Run any new migrations
docker-compose -f docker-compose.prod.yml exec app migrate
```

### Troubleshooting

```bash
# Check container health
docker-compose -f docker-compose.prod.yml exec app health-check

# Interactive shell
docker-compose -f docker-compose.prod.yml exec app shell

# Database connection test
docker-compose -f docker-compose.prod.yml exec app python -c "
import asyncio
from app.db.session import test_connection
asyncio.run(test_connection())
"
```

## 🔐 Security Checklist

- [ ] Strong, unique passwords for all services
- [ ] JWT secrets are 32+ characters and random
- [ ] SSL certificates are properly configured
- [ ] Database access is restricted
- [ ] Regular security updates
- [ ] Backup and disaster recovery plan
- [ ] Monitoring and alerting configured
- [ ] Rate limiting enabled
- [ ] Input validation implemented
- [ ] CORS properly configured

## 🌐 Domain Setup

### DNS Configuration

```
# A Records
yourdomain.com       -> SERVER_IP
*.yourdomain.com     -> SERVER_IP

# Or specific subdomains
api.yourdomain.com   -> SERVER_IP
app.yourdomain.com   -> SERVER_IP
grafana.yourdomain.com -> SERVER_IP
```

### SSL Certificate

Traefik automatically handles Let's Encrypt certificates for all configured domains.

## 📈 Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes for organization queries
CREATE INDEX CONCURRENTLY idx_org_memberships_user_id ON organization_memberships(user_id);
CREATE INDEX CONCURRENTLY idx_org_memberships_org_id ON organization_memberships(organization_id);
CREATE INDEX CONCURRENTLY idx_organizations_slug ON organizations(slug);
```

### 2. Redis Optimization

```bash
# Redis memory optimization in docker-compose.prod.yml
redis:
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
```

### 3. Application Optimization

- Enable response caching
- Use connection pooling
- Implement database query optimization
- Configure proper logging levels
- Use CDN for static assets

## 🆘 Emergency Procedures

### 1. Rollback Deployment

```bash
# Rollback to previous version
export APP_VERSION=previous-working-sha
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Database Recovery

```bash
# Stop application
docker-compose -f docker-compose.prod.yml stop app worker

# Restore database
docker-compose -f docker-compose.prod.yml exec -T db psql -U saas_user fastapi_saas_prod < latest_backup.sql

# Start application
docker-compose -f docker-compose.prod.yml start app worker
```

### 3. Emergency Maintenance Mode

```bash
# Enable maintenance mode in Traefik
# Add maintenance middleware to block traffic
```

---

## 📞 Support

For deployment issues:

1. Check logs: `docker-compose logs -f`
2. Verify environment variables
3. Test database connectivity
4. Check disk space and memory usage
5. Review monitoring dashboards

Remember to test all deployments in a staging environment first!
