# Production Deployment Guide: FastAPI + Nginx (No Docker)

## 🚀 **Production Setup Overview**

This guide shows you how to deploy your FastAPI application directly on a server using:

- **Gunicorn** + **Uvicorn** workers for running FastAPI
- **Nginx** as reverse proxy and load balancer
- **Systemd** for process management and auto-restart
- **SSL/HTTPS** with Let's Encrypt (free)
- **Your lightweight monitoring** (already setup)

**Total setup time: ~30 minutes**  
**Performance: Excellent** (often better than Docker)  
**Maintenance: Minimal**

---

## 📋 **Prerequisites**

- Ubuntu/Debian server (18.04+ recommended)
- Domain name pointing to your server
- Root/sudo access
- Python 3.11+ installed

---

## 🔧 **Step 1: Server Preparation (5 minutes)**

### Update System

```bash
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx postgresql-client
```

### Create Application User (Security Best Practice)

```bash
# Create dedicated user for your app
sudo adduser --system --group --home /opt/fastapi-app fastapi

# Create application directory
sudo mkdir -p /opt/fastapi-app
sudo chown fastapi:fastapi /opt/fastapi-app
```

---

## 📁 **Step 2: Deploy Your Application (10 minutes)**

### Upload Your Code

```bash
# Option 1: Git clone (recommended)
sudo -u fastapi git clone https://github.com/your-username/your-repo.git /opt/fastapi-app/
cd /opt/fastapi-app

# Option 2: SCP upload
# scp -r /local/path/to/your/app user@server:/opt/fastapi-app/
```

### Setup Python Environment

```bash
cd /opt/fastapi-app

# Create virtual environment
sudo -u fastapi python3 -m venv venv
sudo -u fastapi venv/bin/pip install --upgrade pip

# Install dependencies
sudo -u fastapi venv/bin/pip install -r requirements.txt
sudo -u fastapi venv/bin/pip install gunicorn

# Install additional production packages if needed
sudo -u fastapi venv/bin/pip install psutil  # For health monitoring
```

### Create Environment File

```bash
# Create production environment file
sudo -u fastapi cat > /opt/fastapi-app/.env << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/your_db

# App Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random

# Optional: Backup webhook for notifications
BACKUP_WEBHOOK_URL=https://hooks.slack.com/your-webhook-url

# Performance settings
WORKERS=4
HOST=127.0.0.1
PORT=8000
EOF

# Secure the environment file
sudo chmod 600 /opt/fastapi-app/.env
```

---

## ⚙️ **Step 3: Gunicorn Configuration (5 minutes)**

### Create Gunicorn Configuration

```bash
sudo -u fastapi cat > /opt/fastapi-app/gunicorn.prod.conf.py << 'EOF'
"""
Production Gunicorn Configuration
Optimized for performance and reliability
"""

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"  # Nginx will proxy to this
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Auto-scale based on CPU
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 30
keepalive = 2
graceful_timeout = 30

# Process naming
proc_name = 'fastapi_app'

# Logging
accesslog = '/opt/fastapi-app/logs/access.log'
errorlog = '/opt/fastapi-app/logs/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process credentials
user = 'fastapi'
group = 'fastapi'

# Server mechanics
daemon = False  # systemd will manage this
pidfile = '/opt/fastapi-app/gunicorn.pid'
tmp_upload_dir = None

# SSL (if terminating SSL at Gunicorn instead of Nginx)
# keyfile = '/path/to/private.key'
# certfile = '/path/to/certificate.crt'

# Performance tuning
preload_app = True
enable_stdio_inheritance = True

# Worker recycling for memory management
max_requests = 1000
max_requests_jitter = 50

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)
EOF
```

### Create Log Directory

```bash
sudo -u fastapi mkdir -p /opt/fastapi-app/logs
```

---

## 📋 **Step 4: Systemd Service (3 minutes)**

### Create Systemd Service File

```bash
sudo cat > /etc/systemd/system/fastapi-app.service << 'EOF'
[Unit]
Description=FastAPI Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=exec
User=fastapi
Group=fastapi
WorkingDirectory=/opt/fastapi-app
Environment=PATH=/opt/fastapi-app/venv/bin
EnvironmentFile=/opt/fastapi-app/.env
ExecStart=/opt/fastapi-app/venv/bin/gunicorn --config gunicorn.prod.conf.py app.main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=3

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/fastapi-app/logs /opt/fastapi-app/backups
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable fastapi-app.service

# Start the service
sudo systemctl start fastapi-app.service

# Check status
sudo systemctl status fastapi-app.service

# Check logs
sudo journalctl -u fastapi-app.service -f
```

---

## 🌐 **Step 5: Nginx Configuration (5 minutes)**

### Create Nginx Site Configuration

```bash
sudo cat > /etc/nginx/sites-available/fastapi-app << 'EOF'
# FastAPI Production Configuration
# High-performance reverse proxy with security headers

upstream fastapi_backend {
    # Multiple workers for load balancing
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    # Add more servers if you scale horizontally:
    # server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;

    keepalive 32;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/s;

# File upload size limit
client_max_body_size 10M;

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS (will be added after SSL setup)
    # return 301 https://$server_name$request_uri;

    # For now, serve HTTP (we'll add HTTPS next)
    location / {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;

        # Keep alive
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # Health check endpoint (no rate limiting)
    location /health/ {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        access_log off;  # Don't log health checks
    }

    # API rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Auth endpoints with stricter rate limiting
    location /api/v1/auth/ {
        limit_req zone=auth_limit burst=10 nodelay;

        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (if you have any)
    location /static/ {
        alias /opt/fastapi-app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Hide Nginx version
    server_tokens off;

    # Log files
    access_log /var/log/nginx/fastapi_access.log;
    error_log /var/log/nginx/fastapi_error.log;
}
EOF
```

### Enable Site and Restart Nginx

```bash
# Test nginx configuration
sudo nginx -t

# Enable the site
sudo ln -s /etc/nginx/sites-available/fastapi-app /etc/nginx/sites-enabled/

# Remove default site if it exists
sudo rm -f /etc/nginx/sites-enabled/default

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

**Important:** Replace `your-domain.com` with your actual domain name in the Nginx config!

---

## 🔒 **Step 6: SSL/HTTPS Setup (5 minutes)**

### Get SSL Certificate with Let's Encrypt

```bash
# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# The certbot will automatically:
# 1. Get SSL certificates
# 2. Update your Nginx config
# 3. Setup auto-renewal
```

### Verify SSL Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer
```

---

## 💾 **Step 7: Database Backup Setup (2 minutes)**

### Setup Automated Backups

```bash
# Make backup script executable (already created by our production setup)
sudo chmod +x /opt/fastapi-app/scripts/backup_database.sh

# Test backup
sudo -u fastapi /opt/fastapi-app/scripts/backup_database.sh

# Setup cron job for automated backups
sudo -u fastapi crontab -e
# Add this line:
0 2 * * * /opt/fastapi-app/scripts/backup_database.sh >> /opt/fastapi-app/logs/backup.log 2>&1
```

---

## 🔧 **Step 8: Production Verification (3 minutes)**

### Test Your Deployment

```bash
# 1. Check if app is running
sudo systemctl status fastapi-app.service

# 2. Check Nginx status
sudo systemctl status nginx

# 3. Test health endpoints
curl http://your-domain.com/health/health
curl http://your-domain.com/health/ready
curl http://your-domain.com/health/live

# 4. Test HTTPS (after SSL setup)
curl https://your-domain.com/health/health

# 5. Check logs
sudo tail -f /opt/fastapi-app/logs/access.log
sudo tail -f /opt/fastapi-app/logs/error.log
sudo tail -f /var/log/nginx/fastapi_access.log
```

### Performance Test

```bash
# Install Apache Bench for testing
sudo apt install apache2-utils

# Test performance (adjust URL to your domain)
ab -n 1000 -c 10 http://your-domain.com/health/health

# You should see excellent performance (hundreds of requests per second)
```

---

## 📊 **Monitoring & Maintenance**

### Daily Operations

```bash
# Check application status
sudo systemctl status fastapi-app.service

# View logs
sudo journalctl -u fastapi-app.service --since="1 hour ago"

# Check resource usage
htop
df -h
free -h

# Monitor error logs
sudo tail -f /opt/fastapi-app/logs/errors.jsonl | jq .
```

### Regular Maintenance

```bash
# Update application (deployment process)
cd /opt/fastapi-app
sudo -u fastapi git pull origin main
sudo -u fastapi venv/bin/pip install -r requirements.txt
sudo systemctl restart fastapi-app.service

# Rotate logs (setup logrotate)
sudo cat > /etc/logrotate.d/fastapi-app << 'EOF'
/opt/fastapi-app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    copytruncate
}
EOF
```

---

## 🚨 **Troubleshooting**

### Common Issues

**1. App won't start:**

```bash
# Check service logs
sudo journalctl -u fastapi-app.service -f

# Check if port is in use
sudo netstat -tlnp | grep 8000

# Test app manually
sudo -u fastapi /opt/fastapi-app/venv/bin/python -m app.main
```

**2. Nginx errors:**

```bash
# Test nginx config
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log

# Restart nginx
sudo systemctl restart nginx
```

**3. Database connection issues:**

```bash
# Test database connection
sudo -u fastapi /opt/fastapi-app/venv/bin/python -c "
from app.db.session import get_db
import asyncio
async def test():
    async for db in get_db():
        print('Database connected successfully!')
        break
asyncio.run(test())
"
```

**4. SSL issues:**

```bash
# Check SSL status
sudo certbot certificates

# Renew SSL manually
sudo certbot renew
```

---

## 🎯 **Performance Optimization**

### Server Tuning

```bash
# Increase file descriptor limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize kernel parameters
sudo cat >> /etc/sysctl.conf << 'EOF'
# Network performance
net.core.somaxconn = 65536
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65536
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 400000

# Memory management
vm.swappiness = 10
EOF

# Apply changes
sudo sysctl -p
```

### Gunicorn Optimization

```bash
# For high-traffic sites, consider these optimizations in gunicorn.prod.conf.py:

# Increase workers based on your server specs
workers = 8  # For 4-core server

# Use different worker class for CPU-intensive tasks
# worker_class = "uvicorn.workers.UvicornH11Worker"

# Increase connections for high concurrency
worker_connections = 4000
```

---

## 📈 **Success Metrics**

After deployment, you should see:

- ✅ **Response times < 100ms** for health endpoints
- ✅ **Uptime > 99.9%** with systemd auto-restart
- ✅ **SSL A+ rating** with Let's Encrypt
- ✅ **Automatic backups** running daily
- ✅ **Rate limiting** protecting your API
- ✅ **Error tracking** with your lightweight system
- ✅ **Zero Docker overhead** - pure performance

---

## 🔄 **Deployment Workflow**

### Quick Deployment Script

```bash
# Create deployment script
cat > /opt/fastapi-app/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Deploying FastAPI application..."

# Pull latest code
git pull origin main

# Install/update dependencies
venv/bin/pip install -r requirements.txt

# Run any migrations if needed
# venv/bin/python -m alembic upgrade head

# Restart application
sudo systemctl restart fastapi-app.service

# Wait for health check
sleep 5
curl -f http://localhost/health/health || exit 1

echo "✅ Deployment successful!"
EOF

chmod +x /opt/fastapi-app/deploy.sh
```

Your FastAPI application is now production-ready with:

- **High performance** (no Docker overhead)
- **Auto-scaling** with Gunicorn workers
- **SSL/HTTPS** with automatic renewal
- **Rate limiting** and security headers
- **Automated backups** and monitoring
- **Process management** with systemd
- **Professional deployment** workflow

This setup can handle thousands of concurrent users and is used by many production applications!
