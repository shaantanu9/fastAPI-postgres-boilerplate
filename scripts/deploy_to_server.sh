#!/bin/bash
# FastAPI Production Deployment Script (No Docker)
# Run this script on your Ubuntu/Debian server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration (modify these values)
APP_USER="fastapi"
APP_DIR="/opt/fastapi-app"
DOMAIN="your-domain.com"
EMAIL="your-email@example.com"
REPO_URL="https://github.com/your-username/your-repo.git"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

update_system() {
    print_status "Updating system packages..."
    apt update && apt upgrade -y
    apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx \
                   postgresql-client git curl htop apache2-utils jq psutil
    print_success "System updated successfully"
}

create_app_user() {
    print_status "Creating application user..."
    
    if id "$APP_USER" &>/dev/null; then
        print_warning "User $APP_USER already exists"
    else
        adduser --system --group --home $APP_DIR $APP_USER
        print_success "Created user $APP_USER"
    fi
    
    mkdir -p $APP_DIR
    chown $APP_USER:$APP_USER $APP_DIR
}

deploy_application() {
    print_status "Deploying application code..."
    
    if [ -d "$APP_DIR/.git" ]; then
        print_status "Updating existing repository..."
        cd $APP_DIR
        sudo -u $APP_USER git pull origin main
    else
        print_status "Cloning repository..."
        sudo -u $APP_USER git clone $REPO_URL $APP_DIR
        cd $APP_DIR
    fi
    
    # Setup Python environment
    print_status "Setting up Python environment..."
    sudo -u $APP_USER python3 -m venv venv
    sudo -u $APP_USER venv/bin/pip install --upgrade pip
    sudo -u $APP_USER venv/bin/pip install -r requirements.txt
    sudo -u $APP_USER venv/bin/pip install gunicorn psutil
    
    # Create directories
    sudo -u $APP_USER mkdir -p logs backups
    
    print_success "Application deployed successfully"
}

create_env_file() {
    print_status "Creating environment configuration..."
    
    cat > $APP_DIR/.env << EOF
# Database Configuration
DATABASE_URL=postgresql+asyncpg://fastapi_user:your_password@localhost:5432/fastapi_db

# Application Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
HOST=127.0.0.1
PORT=8000

# Performance Settings
WORKERS=4

# Optional: Webhook for notifications
# BACKUP_WEBHOOK_URL=https://hooks.slack.com/your-webhook-url
EOF
    
    chown $APP_USER:$APP_USER $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    
    print_warning "Please edit $APP_DIR/.env with your actual database credentials"
    print_success "Environment file created"
}

create_gunicorn_config() {
    print_status "Creating Gunicorn configuration..."
    
    cat > $APP_DIR/gunicorn.prod.conf.py << 'EOF'
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
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

# Process credentials
user = 'fastapi'
group = 'fastapi'

# Performance
preload_app = True
enable_stdio_inheritance = True
EOF
    
    chown $APP_USER:$APP_USER $APP_DIR/gunicorn.prod.conf.py
    print_success "Gunicorn configuration created"
}

create_systemd_service() {
    print_status "Creating systemd service..."
    
    cat > /etc/systemd/system/fastapi-app.service << EOF
[Unit]
Description=FastAPI Application
After=network.target
Wants=postgresql.service

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.prod.conf.py app.main:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=3

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/logs $APP_DIR/backups

# Resource limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable fastapi-app.service
    print_success "Systemd service created and enabled"
}

create_nginx_config() {
    print_status "Creating Nginx configuration..."
    
    cat > /etc/nginx/sites-available/fastapi-app << EOF
upstream fastapi_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=auth_limit:10m rate=5r/s;

client_max_body_size 10M;

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    location / {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    location /health/ {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        access_log off;
    }
    
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://fastapi_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /api/v1/auth/ {
        limit_req zone=auth_limit burst=10 nodelay;
        proxy_pass http://fastapi_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    server_tokens off;
    
    access_log /var/log/nginx/fastapi_access.log;
    error_log /var/log/nginx/fastapi_error.log;
}
EOF
    
    # Test nginx config
    nginx -t
    
    # Enable site
    ln -sf /etc/nginx/sites-available/fastapi-app /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    systemctl restart nginx
    systemctl enable nginx
    
    print_success "Nginx configured and started"
}

setup_ssl() {
    print_status "Setting up SSL certificate..."
    
    if [ "$DOMAIN" = "your-domain.com" ]; then
        print_warning "Please update the DOMAIN variable in this script with your actual domain"
        print_warning "Skipping SSL setup - run 'sudo certbot --nginx -d yourdomain.com' manually"
        return
    fi
    
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive
    
    # Test auto-renewal
    certbot renew --dry-run
    
    print_success "SSL certificate installed and auto-renewal configured"
}

setup_backup() {
    print_status "Setting up database backup..."
    
    # Make backup script executable
    chmod +x $APP_DIR/scripts/backup_database.sh
    
    # Setup cron job
    sudo -u $APP_USER crontab -l 2>/dev/null | { cat; echo "0 2 * * * $APP_DIR/scripts/backup_database.sh >> $APP_DIR/logs/backup.log 2>&1"; } | sudo -u $APP_USER crontab -
    
    print_success "Database backup scheduled for 2 AM daily"
}

start_services() {
    print_status "Starting services..."
    
    systemctl start fastapi-app.service
    sleep 3
    
    if systemctl is-active --quiet fastapi-app.service; then
        print_success "FastAPI service started successfully"
    else
        print_error "Failed to start FastAPI service"
        journalctl -u fastapi-app.service --no-pager -l
        exit 1
    fi
}

run_tests() {
    print_status "Running deployment tests..."
    
    # Test health endpoint
    sleep 5
    if curl -f http://localhost/health/health >/dev/null 2>&1; then
        print_success "Health endpoint test passed"
    else
        print_error "Health endpoint test failed"
        exit 1
    fi
    
    # Performance test
    print_status "Running performance test..."
    ab -n 100 -c 5 http://localhost/health/health | grep "Requests per second"
}

print_final_instructions() {
    print_success "🎉 Deployment completed successfully!"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Edit $APP_DIR/.env with your database credentials"
    echo "2. Test your application: curl http://$DOMAIN/health/health"
    echo "3. Check service status: sudo systemctl status fastapi-app.service"
    echo "4. View logs: sudo journalctl -u fastapi-app.service -f"
    echo ""
    echo -e "${GREEN}Your FastAPI application is running at:${NC}"
    echo "HTTP:  http://$DOMAIN"
    echo "HTTPS: https://$DOMAIN (if SSL was configured)"
    echo ""
    echo -e "${YELLOW}Management commands:${NC}"
    echo "Start:   sudo systemctl start fastapi-app.service"
    echo "Stop:    sudo systemctl stop fastapi-app.service"
    echo "Restart: sudo systemctl restart fastapi-app.service"
    echo "Status:  sudo systemctl status fastapi-app.service"
    echo "Logs:    sudo journalctl -u fastapi-app.service -f"
    echo ""
    echo -e "${BLUE}Files locations:${NC}"
    echo "App:     $APP_DIR"
    echo "Logs:    $APP_DIR/logs/"
    echo "Backups: $APP_DIR/backups/"
    echo "Config:  $APP_DIR/.env"
}

# Main execution
main() {
    print_status "Starting FastAPI production deployment..."
    
    check_root
    update_system
    create_app_user
    deploy_application
    create_env_file
    create_gunicorn_config
    create_systemd_service
    create_nginx_config
    setup_backup
    start_services
    run_tests
    
    # Setup SSL last (requires domain to be pointing to server)
    setup_ssl
    
    print_final_instructions
}

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Before running, edit the configuration variables at the top of this script:"
    echo "- DOMAIN: Your domain name"
    echo "- EMAIL: Your email for SSL certificate"
    echo "- REPO_URL: Your git repository URL"
    echo ""
    echo "Then run: sudo $0 deploy"
    echo ""
    exit 1
fi

if [ "$1" = "deploy" ]; then
    main
else
    echo "Unknown command: $1"
    echo "Use: sudo $0 deploy"
    exit 1
fi 