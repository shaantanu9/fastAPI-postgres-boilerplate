#!/bin/bash
# FastAPI Deployment Script for Existing Server Setup
# Designed for servers with existing Nginx and other sites

set -e

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES BEFORE RUNNING
# ============================================================================

# Project Configuration
PROJECT_NAME="fastapi-app"                    # Your project name (used for directories/services)
DOMAIN="your-domain.com"                      # Your domain name
EMAIL="your-email@example.com"               # Your email for SSL certificates

# Repository Configuration  
REPO_URL="https://github.com/username/repo.git"  # Your repository URL
REPO_BRANCH="main"                            # Branch to deploy (main/master/production)

# For Private Repositories - Choose ONE method:
# Method 1: GitHub Token (Recommended)
GITHUB_TOKEN=""                               # Your GitHub personal access token
# Method 2: SSH Key (if you prefer SSH)
USE_SSH=false                                 # Set to true if using SSH instead of token

# Server Configuration
APP_USER="fastapi"                            # User to run the application
APP_DIR="/opt/${PROJECT_NAME}"                # Application directory
PYTHON_VERSION="python3"                     # Python command

# Database Configuration (will be added to .env)
DB_HOST="localhost"                           # Database host
DB_PORT="5432"                                # Database port  
DB_NAME="your_database_name"                  # Database name
DB_USER="your_db_username"                    # Database username
DB_PASSWORD="your_db_password"                # Database password

# Optional: Backup webhook for notifications
BACKUP_WEBHOOK_URL=""                         # Slack/Discord webhook URL (optional)

# Performance Settings
WORKERS="auto"                                # Number of Gunicorn workers (auto = CPU cores * 2 + 1)
PORT="8000"                                   # Port for this application

# ============================================================================
# COLORS AND HELPER FUNCTIONS
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_requirements() {
    print_status "Checking requirements..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
    
    # Check if nginx is installed and running
    if ! systemctl is-active --quiet nginx; then
        print_error "Nginx is not running. Please start nginx first: sudo systemctl start nginx"
        exit 1
    fi
    
    # Check required commands
    for cmd in git python3 curl; do
        if ! command -v $cmd &> /dev/null; then
            print_error "$cmd is not installed"
            exit 1
        fi
    done
    
    print_success "Requirements check passed"
}

# ============================================================================
# REPOSITORY FUNCTIONS
# ============================================================================

setup_private_repo_access() {
    if [[ -n "$GITHUB_TOKEN" ]]; then
        print_status "Setting up GitHub token access..."
        # Convert HTTPS URL to use token
        if [[ $REPO_URL == https://github.com/* ]]; then
            REPO_URL="https://${GITHUB_TOKEN}@github.com/${REPO_URL#https://github.com/}"
        fi
        print_success "GitHub token configured"
    elif [[ "$USE_SSH" == "true" ]]; then
        print_status "Using SSH key access..."
        # Convert HTTPS to SSH if needed
        if [[ $REPO_URL == https://github.com/* ]]; then
            REPO_URL="git@github.com:${REPO_URL#https://github.com/}"
        fi
        print_success "SSH access configured"
    else
        print_warning "No private repo access configured - assuming public repo"
    fi
}

# ============================================================================
# APPLICATION DEPLOYMENT
# ============================================================================

create_app_user() {
    print_status "Setting up application user..."
    
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
    print_status "Deploying application..."
    
    # Setup repository access
    setup_private_repo_access
    
    if [ -d "$APP_DIR/.git" ]; then
        print_status "Updating existing repository..."
        cd $APP_DIR
        sudo -u $APP_USER git fetch origin
        sudo -u $APP_USER git reset --hard origin/$REPO_BRANCH
        sudo -u $APP_USER git clean -fd
    else
        print_status "Cloning repository..."
        sudo -u $APP_USER git clone -b $REPO_BRANCH $REPO_URL $APP_DIR
        cd $APP_DIR
    fi
    
    # Setup Python environment
    print_status "Setting up Python environment..."
    sudo -u $APP_USER $PYTHON_VERSION -m venv venv
    sudo -u $APP_USER venv/bin/pip install --upgrade pip
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        sudo -u $APP_USER venv/bin/pip install -r requirements.txt
    else
        print_error "requirements.txt not found in repository"
        exit 1
    fi
    
    # Install production dependencies
    sudo -u $APP_USER venv/bin/pip install gunicorn psutil
    
    # Create necessary directories
    sudo -u $APP_USER mkdir -p logs backups static
    
    print_success "Application deployed successfully"
}

create_env_file() {
    print_status "Creating environment configuration..."
    
    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)
    
    cat > $APP_DIR/.env << EOF
# Database Configuration
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Application Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=${SECRET_KEY}
HOST=127.0.0.1
PORT=${PORT}

# Performance Settings
WORKERS=${WORKERS}

# Optional: Webhook for notifications
BACKUP_WEBHOOK_URL=${BACKUP_WEBHOOK_URL}

# Security Settings
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},localhost,127.0.0.1
CORS_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
EOF
    
    chown $APP_USER:$APP_USER $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    
    print_success "Environment file created"
}

create_gunicorn_config() {
    print_status "Creating Gunicorn configuration..."
    
    cat > $APP_DIR/gunicorn.prod.conf.py << 'EOF'
import multiprocessing
import os

# Server socket
bind = f"127.0.0.1:{os.getenv('PORT', '8000')}"
backlog = 2048

# Workers
workers_env = os.getenv('WORKERS', 'auto')
if workers_env == 'auto':
    workers = multiprocessing.cpu_count() * 2 + 1
else:
    workers = int(workers_env)

worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 30
keepalive = 2
graceful_timeout = 30

# Process naming
proc_name = os.getenv('PROJECT_NAME', 'fastapi_app')

# Logging
accesslog = '/opt/fastapi-app/logs/access.log'
errorlog = '/opt/fastapi-app/logs/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process credentials
user = 'fastapi'
group = 'fastapi'

# Performance
preload_app = True
enable_stdio_inheritance = True

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")
EOF
    
    # Update the config with actual values
    sed -i "s|/opt/fastapi-app|$APP_DIR|g" $APP_DIR/gunicorn.prod.conf.py
    sed -i "s|'fastapi'|'$APP_USER'|g" $APP_DIR/gunicorn.prod.conf.py
    sed -i "s|'fastapi_app'|'$PROJECT_NAME'|g" $APP_DIR/gunicorn.prod.conf.py
    
    chown $APP_USER:$APP_USER $APP_DIR/gunicorn.prod.conf.py
    print_success "Gunicorn configuration created"
}

create_systemd_service() {
    print_status "Creating systemd service..."
    
    cat > /etc/systemd/system/${PROJECT_NAME}.service << EOF
[Unit]
Description=${PROJECT_NAME} FastAPI Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
Environment=PROJECT_NAME=$PROJECT_NAME
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.prod.conf.py app.main:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=3

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/logs $APP_DIR/backups $APP_DIR/static
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable ${PROJECT_NAME}.service
    print_success "Systemd service created and enabled"
}

# ============================================================================
# NGINX CONFIGURATION
# ============================================================================

create_nginx_config() {
    print_status "Creating Nginx configuration..."
    
    cat > /etc/nginx/sites-available/${PROJECT_NAME} << EOF
# ${PROJECT_NAME} FastAPI Application
# Generated on $(date)

upstream ${PROJECT_NAME}_backend {
    server 127.0.0.1:${PORT} max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Rate limiting zones
limit_req_zone \$binary_remote_addr zone=${PROJECT_NAME}_api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=${PROJECT_NAME}_auth:10m rate=5r/s;

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    server_tokens off;
    
    # File upload size
    client_max_body_size 10M;
    
    # Health check endpoints (no rate limiting)
    location /health/ {
        proxy_pass http://${PROJECT_NAME}_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        access_log off;
    }
    
    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=${PROJECT_NAME}_api burst=20 nodelay;
        
        proxy_pass http://${PROJECT_NAME}_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
        
        # HTTP version and keep alive
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Auth endpoints with stricter rate limiting
    location /api/v1/auth/ {
        limit_req zone=${PROJECT_NAME}_auth burst=10 nodelay;
        
        proxy_pass http://${PROJECT_NAME}_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Static files
    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Main application
    location / {
        proxy_pass http://${PROJECT_NAME}_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        
        # HTTP version and keep alive
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Logs
    access_log /var/log/nginx/${PROJECT_NAME}_access.log;
    error_log /var/log/nginx/${PROJECT_NAME}_error.log;
}
EOF
    
    # Test nginx configuration
    nginx -t
    
    # Enable the site
    ln -sf /etc/nginx/sites-available/${PROJECT_NAME} /etc/nginx/sites-enabled/
    
    # Reload nginx
    systemctl reload nginx
    
    print_success "Nginx configuration created and enabled"
}

# ============================================================================
# SSL AND SECURITY
# ============================================================================

setup_ssl() {
    print_status "Setting up SSL certificate..."
    
    if [ "$DOMAIN" = "your-domain.com" ]; then
        print_warning "Domain not configured. Skipping SSL setup."
        print_warning "Run manually: sudo certbot --nginx -d yourdomain.com"
        return
    fi
    
    # Install certbot if not already installed
    if ! command -v certbot &> /dev/null; then
        apt install -y certbot python3-certbot-nginx
    fi
    
    # Get SSL certificate
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive
    
    # Test auto-renewal
    certbot renew --dry-run
    
    print_success "SSL certificate installed and auto-renewal configured"
}

# ============================================================================
# BACKUP AND MAINTENANCE
# ============================================================================

setup_backup() {
    print_status "Setting up database backup..."
    
    # Make backup script executable
    if [ -f "$APP_DIR/scripts/backup_database.sh" ]; then
        chmod +x $APP_DIR/scripts/backup_database.sh
        
        # Setup cron job for backups
        (sudo -u $APP_USER crontab -l 2>/dev/null; echo "0 2 * * * $APP_DIR/scripts/backup_database.sh >> $APP_DIR/logs/backup.log 2>&1") | sudo -u $APP_USER crontab -
        
        print_success "Database backup scheduled for 2 AM daily"
    else
        print_warning "Backup script not found in repository"
    fi
}

create_management_scripts() {
    print_status "Creating management scripts..."
    
    # Create deployment script
    cat > $APP_DIR/deploy.sh << EOF
#!/bin/bash
# Quick deployment script
cd $APP_DIR
sudo -u $APP_USER git pull origin $REPO_BRANCH
sudo -u $APP_USER venv/bin/pip install -r requirements.txt
sudo systemctl restart ${PROJECT_NAME}.service
echo "Deployment completed!"
EOF
    
    chmod +x $APP_DIR/deploy.sh
    
    # Create status script
    cat > $APP_DIR/status.sh << EOF
#!/bin/bash
echo "=== ${PROJECT_NAME} Status ==="
echo "Service Status:"
systemctl status ${PROJECT_NAME}.service --no-pager -l
echo ""
echo "Health Check:"
curl -s http://localhost:${PORT}/health/health | jq . || echo "Health check failed"
echo ""
echo "Recent Logs:"
journalctl -u ${PROJECT_NAME}.service --no-pager -n 10
EOF
    
    chmod +x $APP_DIR/status.sh
    
    print_success "Management scripts created"
}

# ============================================================================
# SERVICE MANAGEMENT
# ============================================================================

start_services() {
    print_status "Starting services..."
    
    # Start the application service
    systemctl start ${PROJECT_NAME}.service
    sleep 3
    
    if systemctl is-active --quiet ${PROJECT_NAME}.service; then
        print_success "${PROJECT_NAME} service started successfully"
    else
        print_error "Failed to start ${PROJECT_NAME} service"
        journalctl -u ${PROJECT_NAME}.service --no-pager -l
        exit 1
    fi
}

run_tests() {
    print_status "Running deployment tests..."
    
    # Wait for service to be fully ready
    sleep 5
    
    # Test health endpoint
    if curl -f http://localhost:${PORT}/health/health >/dev/null 2>&1; then
        print_success "Health endpoint test passed"
    else
        print_error "Health endpoint test failed"
        exit 1
    fi
    
    # Test through nginx
    if curl -f http://localhost/health/health >/dev/null 2>&1; then
        print_success "Nginx proxy test passed"
    else
        print_warning "Nginx proxy test failed (check nginx config)"
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

print_final_instructions() {
    print_success "🎉 Deployment completed successfully!"
    echo ""
    echo -e "${BLUE}Service Details:${NC}"
    echo "Service Name: ${PROJECT_NAME}.service"
    echo "App Directory: $APP_DIR"
    echo "Port: $PORT"
    echo "Domain: $DOMAIN"
    echo ""
    echo -e "${GREEN}URLs:${NC}"
    echo "Health Check: http://$DOMAIN/health/health"
    echo "API Documentation: http://$DOMAIN/docs"
    echo ""
    echo -e "${YELLOW}Management Commands:${NC}"
    echo "Status:     sudo systemctl status ${PROJECT_NAME}.service"
    echo "Restart:    sudo systemctl restart ${PROJECT_NAME}.service"
    echo "Logs:       sudo journalctl -u ${PROJECT_NAME}.service -f"
    echo "Deploy:     $APP_DIR/deploy.sh"
    echo "Status:     $APP_DIR/status.sh"
    echo ""
    echo -e "${BLUE}Configuration Files:${NC}"
    echo "Environment: $APP_DIR/.env"
    echo "Nginx:       /etc/nginx/sites-available/${PROJECT_NAME}"
    echo "Service:     /etc/systemd/system/${PROJECT_NAME}.service"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo "1. Test your application: curl http://$DOMAIN/health/health"
    echo "2. Setup SSL: sudo certbot --nginx -d $DOMAIN"
    echo "3. Monitor logs: sudo journalctl -u ${PROJECT_NAME}.service -f"
}

main() {
    print_status "Starting ${PROJECT_NAME} deployment..."
    
    check_requirements
    create_app_user
    deploy_application
    create_env_file
    create_gunicorn_config
    create_systemd_service
    create_nginx_config
    setup_backup
    create_management_scripts
    start_services
    run_tests
    setup_ssl
    
    print_final_instructions
}

# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

if [ $# -eq 0 ]; then
    echo "FastAPI Deployment Script for Existing Server Setup"
    echo ""
    echo "Before running, edit this script and update the configuration section at the top:"
    echo "- PROJECT_NAME, DOMAIN, EMAIL"
    echo "- REPO_URL, GITHUB_TOKEN (for private repos)"
    echo "- Database credentials"
    echo ""
    echo "Usage: sudo $0 deploy"
    echo ""
    echo "Commands:"
    echo "  deploy    - Deploy the application"
    echo "  update    - Update existing deployment"
    echo "  status    - Show deployment status"
    echo ""
    exit 1
fi

case "$1" in
    deploy)
        main
        ;;
    update)
        print_status "Updating ${PROJECT_NAME}..."
        deploy_application
        systemctl restart ${PROJECT_NAME}.service
        print_success "Update completed!"
        ;;
    status)
        systemctl status ${PROJECT_NAME}.service
        echo ""
        curl -s http://localhost:${PORT}/health/health | jq . || echo "Health check failed"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use: sudo $0 deploy|update|status"
        exit 1
        ;;
esac 