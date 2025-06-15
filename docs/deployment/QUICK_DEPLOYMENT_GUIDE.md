# 🚀 Quick Production Deployment (No Docker)

## **Option 1: Automated Deployment (Recommended)**

### 1. Edit Configuration

```bash
# Edit the deployment script
vim scripts/deploy_to_server.sh

# Update these variables:
DOMAIN="your-domain.com"
EMAIL="your-email@example.com"
REPO_URL="https://github.com/your-username/your-repo.git"
```

### 2. Run Deployment Script

```bash
# Copy script to your server
scp scripts/deploy_to_server.sh user@your-server:~/

# SSH to your server
ssh user@your-server

# Make executable and run
chmod +x deploy_to_server.sh
sudo ./deploy_to_server.sh deploy
```

### 3. Configure Database

```bash
# Edit environment file
sudo nano /opt/fastapi-app/.env

# Update DATABASE_URL with your PostgreSQL credentials
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/your_db
```

### 4. Restart and Test

```bash
# Restart the application
sudo systemctl restart fastapi-app.service

# Test your deployment
curl http://your-domain.com/health/health
```

**Done! Your app is live in ~10 minutes! 🎉**

---

## **Option 2: Manual Step-by-Step**

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx postgresql-client git

# Create app user
sudo adduser --system --group --home /opt/fastapi-app fastapi
sudo mkdir -p /opt/fastapi-app
sudo chown fastapi:fastapi /opt/fastapi-app
```

### 2. Deploy Application

```bash
# Clone your repository
sudo -u fastapi git clone https://github.com/your-username/your-repo.git /opt/fastapi-app
cd /opt/fastapi-app

# Setup Python environment
sudo -u fastapi python3 -m venv venv
sudo -u fastapi venv/bin/pip install -r requirements.txt
sudo -u fastapi venv/bin/pip install gunicorn psutil

# Create directories
sudo -u fastapi mkdir -p logs backups
```

### 3. Create Configuration Files

**Environment file:**

```bash
sudo -u fastapi cat > /opt/fastapi-app/.env << 'EOF'
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/your_db
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-super-secret-key-here
HOST=127.0.0.1
PORT=8000
WORKERS=4
EOF
sudo chmod 600 /opt/fastapi-app/.env
```

**Gunicorn config:**

```bash
sudo -u fastapi cat > /opt/fastapi-app/gunicorn.prod.conf.py << 'EOF'
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
user = "fastapi"
group = "fastapi"
accesslog = "/opt/fastapi-app/logs/access.log"
errorlog = "/opt/fastapi-app/logs/error.log"
preload_app = True
EOF
```

### 4. Create Systemd Service

```bash
sudo cat > /etc/systemd/system/fastapi-app.service << 'EOF'
[Unit]
Description=FastAPI Application
After=network.target

[Service]
Type=exec
User=fastapi
Group=fastapi
WorkingDirectory=/opt/fastapi-app
Environment=PATH=/opt/fastapi-app/venv/bin
EnvironmentFile=/opt/fastapi-app/.env
ExecStart=/opt/fastapi-app/venv/bin/gunicorn --config gunicorn.prod.conf.py app.main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable fastapi-app.service
sudo systemctl start fastapi-app.service
```

### 5. Configure Nginx

```bash
sudo cat > /etc/nginx/sites-available/fastapi-app << 'EOF'
upstream fastapi_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health/ {
        proxy_pass http://fastapi_backend;
        access_log off;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/fastapi-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Setup SSL (Optional but Recommended)

```bash
# Get free SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

## **Management Commands**

### Service Management

```bash
# Start/Stop/Restart
sudo systemctl start fastapi-app.service
sudo systemctl stop fastapi-app.service
sudo systemctl restart fastapi-app.service

# Check status
sudo systemctl status fastapi-app.service

# View logs
sudo journalctl -u fastapi-app.service -f
```

### Application Updates

```bash
cd /opt/fastapi-app
sudo -u fastapi git pull origin main
sudo -u fastapi venv/bin/pip install -r requirements.txt
sudo systemctl restart fastapi-app.service
```

### Health Checks

```bash
# Test endpoints
curl http://your-domain.com/health/health
curl http://your-domain.com/health/ready
curl http://your-domain.com/health/live

# Performance test
ab -n 1000 -c 10 http://your-domain.com/health/health
```

### Monitor Logs

```bash
# Application logs
sudo tail -f /opt/fastapi-app/logs/access.log
sudo tail -f /opt/fastapi-app/logs/error.log

# Error tracking (your lightweight system)
sudo tail -f /opt/fastapi-app/logs/errors.jsonl | jq .

# Nginx logs
sudo tail -f /var/log/nginx/fastapi_access.log
sudo tail -f /var/log/nginx/fastapi_error.log

# System logs
sudo journalctl -u fastapi-app.service -f
sudo journalctl -u nginx.service -f
```

---

## **Performance & Security Features**

✅ **Automatic scaling** with Gunicorn workers  
✅ **Rate limiting** built into Nginx  
✅ **SSL/HTTPS** with Let's Encrypt  
✅ **Security headers** for protection  
✅ **Lightweight error tracking** (no Sentry overhead)  
✅ **Automated database backups**  
✅ **Health monitoring** endpoints  
✅ **Process management** with systemd  
✅ **Log rotation** and management  
✅ **Zero Docker overhead** = maximum performance

---

## **Troubleshooting**

### App Won't Start

```bash
# Check service status
sudo systemctl status fastapi-app.service

# Check logs
sudo journalctl -u fastapi-app.service -n 50

# Test app manually
sudo -u fastapi /opt/fastapi-app/venv/bin/python -m app.main
```

### Nginx Issues

```bash
# Test nginx config
sudo nginx -t

# Check nginx status
sudo systemctl status nginx

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Database Connection Issues

```bash
# Test database connection
sudo -u fastapi /opt/fastapi-app/venv/bin/python -c "
import asyncio
from app.db.session import get_db

async def test():
    async for db in get_db():
        print('Database connected!')
        break

asyncio.run(test())
"
```

---

## **File Locations**

```
/opt/fastapi-app/              # Application directory
├── app/                       # Your FastAPI code
├── venv/                      # Python virtual environment
├── logs/                      # Application logs
├── backups/                   # Database backups
├── .env                       # Environment configuration
├── gunicorn.prod.conf.py      # Gunicorn configuration
└── scripts/                   # Utility scripts

/etc/systemd/system/fastapi-app.service  # Systemd service
/etc/nginx/sites-available/fastapi-app   # Nginx configuration
```

---

This setup gives you **enterprise-grade performance** without Docker complexity. Your FastAPI app will handle thousands of concurrent users with ease! 🚀
