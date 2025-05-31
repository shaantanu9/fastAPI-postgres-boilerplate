#!/bin/bash
set -euo pipefail

# FastAPI Production Deployment Script
# This script sets up a production-ready FastAPI application with process management

# Configuration
APP_NAME="fastapi"
APP_USER="www-data"
APP_GROUP="www-data"
APP_DIR="/var/www/fastapi"
VENV_DIR="${APP_DIR}/.venv"
CONFIG_DIR="${APP_DIR}/production_configs"
LOG_DIR="/var/log/fastapi"
RUN_DIR="/run/fastapi"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if script is run as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Use a sudo-enabled user instead."
        exit 1
    fi
}

# Check if required commands exist
check_dependencies() {
    log_step "Checking dependencies..."
    
    local deps=("python3" "pip" "systemctl" "nginx")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is not installed. Please install it first."
            exit 1
        fi
    done
    
    log_info "All dependencies are available"
}

# Install system packages
install_system_packages() {
    log_step "Installing system packages..."
    
    sudo apt update
    sudo apt install -y \
        python3-venv \
        python3-dev \
        python3-pip \
        build-essential \
        nginx \
        supervisor \
        curl \
        git \
        htop \
        logrotate
    
    log_info "System packages installed"
}

# Create application user and directories
setup_directories() {
    log_step "Setting up directories and permissions..."
    
    # Create application directories
    sudo mkdir -p "$APP_DIR" "$LOG_DIR" "$RUN_DIR"
    
    # Set ownership
    sudo chown -R "$APP_USER:$APP_GROUP" "$APP_DIR" "$LOG_DIR" "$RUN_DIR"
    
    # Set permissions
    sudo chmod 755 "$APP_DIR"
    sudo chmod 755 "$LOG_DIR"
    sudo chmod 755 "$RUN_DIR"
    
    log_info "Directories created and configured"
}

# Setup Python virtual environment
setup_python_environment() {
    log_step "Setting up Python virtual environment..."
    
    # Create virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
        log_info "Virtual environment created at $VENV_DIR"
    else
        log_warn "Virtual environment already exists"
    fi
    
    # Activate virtual environment and upgrade pip
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip setuptools wheel
    
    # Install production dependencies
    if [[ -f "${APP_DIR}/requirements.txt" ]]; then
        pip install -r "${APP_DIR}/requirements.txt"
        log_info "Requirements installed"
    else
        # Install basic FastAPI stack
        pip install \
            fastapi \
            uvicorn[standard] \
            gunicorn \
            uvicorn-worker \
            psutil \
            aiohttp \
            aioredis \
            sqlalchemy \
            asyncpg \
            python-multipart
        log_info "Basic FastAPI stack installed"
    fi
    
    deactivate
    
    # Set ownership of venv
    sudo chown -R "$APP_USER:$APP_GROUP" "$VENV_DIR"
}

# Configure Gunicorn
setup_gunicorn() {
    log_step "Configuring Gunicorn..."
    
    # Copy Gunicorn configuration if it doesn't exist
    if [[ ! -f "${APP_DIR}/gunicorn.conf.py" ]]; then
        if [[ -f "${CONFIG_DIR}/gunicorn.conf.py" ]]; then
            sudo cp "${CONFIG_DIR}/gunicorn.conf.py" "${APP_DIR}/"
            sudo chown "$APP_USER:$APP_GROUP" "${APP_DIR}/gunicorn.conf.py"
            log_info "Gunicorn configuration copied"
        else
            log_warn "Gunicorn configuration not found, using defaults"
        fi
    fi
}

# Setup systemd service
setup_systemd() {
    log_step "Setting up systemd service..."
    
    local service_file="/etc/systemd/system/${APP_NAME}.service"
    
    if [[ -f "${CONFIG_DIR}/systemd/fastapi.service" ]]; then
        sudo cp "${CONFIG_DIR}/systemd/fastapi.service" "$service_file"
        
        # Replace placeholders in service file
        sudo sed -i "s|/var/www/fastapi|${APP_DIR}|g" "$service_file"
        sudo sed -i "s|www-data|${APP_USER}|g" "$service_file"
        
        # Reload systemd and enable service
        sudo systemctl daemon-reload
        sudo systemctl enable "$APP_NAME"
        
        log_info "Systemd service configured and enabled"
    else
        log_error "Systemd service file not found at ${CONFIG_DIR}/systemd/fastapi.service"
        exit 1
    fi
}

# Setup supervisor (alternative to systemd)
setup_supervisor() {
    log_step "Setting up Supervisor configuration..."
    
    local supervisor_config="/etc/supervisor/conf.d/${APP_NAME}.conf"
    
    if [[ -f "${CONFIG_DIR}/supervisor/fastapi.conf" ]]; then
        sudo cp "${CONFIG_DIR}/supervisor/fastapi.conf" "$supervisor_config"
        
        # Replace placeholders
        sudo sed -i "s|/var/www/fastapi|${APP_DIR}|g" "$supervisor_config"
        sudo sed -i "s|www-data|${APP_USER}|g" "$supervisor_config"
        
        # Update supervisor
        sudo supervisorctl reread
        sudo supervisorctl update
        
        log_info "Supervisor configuration added"
    else
        log_warn "Supervisor configuration not found"
    fi
}

# Configure Nginx
setup_nginx() {
    log_step "Configuring Nginx..."
    
    local nginx_config="/etc/nginx/sites-available/${APP_NAME}"
    local nginx_enabled="/etc/nginx/sites-enabled/${APP_NAME}"
    
    # Create Nginx configuration
    sudo tee "$nginx_config" > /dev/null <<EOF
server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 100M;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    
    location / {
        proxy_pass http://unix:${RUN_DIR}/gunicorn.sock;
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
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://unix:${RUN_DIR}/gunicorn.sock;
        proxy_set_header Host \$host;
        access_log off;
    }
    
    # Static files (if any)
    location /static/ {
        alias ${APP_DIR}/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Security: deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
    
    # Enable the site
    sudo ln -sf "$nginx_config" "$nginx_enabled"
    
    # Remove default site if it exists
    if [[ -f "/etc/nginx/sites-enabled/default" ]]; then
        sudo rm "/etc/nginx/sites-enabled/default"
    fi
    
    # Test nginx configuration
    if sudo nginx -t; then
        sudo systemctl reload nginx
        log_info "Nginx configured and reloaded"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
}

# Setup log rotation
setup_log_rotation() {
    log_step "Setting up log rotation..."
    
    sudo tee "/etc/logrotate.d/${APP_NAME}" > /dev/null <<EOF
${LOG_DIR}/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 ${APP_USER} ${APP_GROUP}
    postrotate
        systemctl reload ${APP_NAME} > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "Log rotation configured"
}

# Setup firewall rules
setup_firewall() {
    log_step "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        sudo ufw --force enable
        sudo ufw allow ssh
        sudo ufw allow 'Nginx Full'
        sudo ufw --force reload
        log_info "UFW firewall configured"
    else
        log_warn "UFW not available, skipping firewall configuration"
    fi
}

# Create health check script
create_health_check() {
    log_step "Creating health check script..."
    
    sudo tee "${APP_DIR}/health_check.sh" > /dev/null <<'EOF'
#!/bin/bash
# Simple health check script for monitoring

HEALTH_URL="http://localhost/health"
TIMEOUT=10

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$HEALTH_URL")

if [[ "$response" == "200" ]]; then
    echo "OK: Application is healthy"
    exit 0
else
    echo "CRITICAL: Application health check failed (HTTP $response)"
    exit 2
fi
EOF
    
    sudo chmod +x "${APP_DIR}/health_check.sh"
    sudo chown "$APP_USER:$APP_GROUP" "${APP_DIR}/health_check.sh"
    
    log_info "Health check script created"
}

# Start services
start_services() {
    log_step "Starting services..."
    
    # Start the FastAPI application
    if sudo systemctl start "$APP_NAME"; then
        log_info "FastAPI service started"
    else
        log_error "Failed to start FastAPI service"
        sudo systemctl status "$APP_NAME" --no-pager
        exit 1
    fi
    
    # Check service status
    sleep 5
    if sudo systemctl is-active --quiet "$APP_NAME"; then
        log_info "FastAPI service is running"
    else
        log_error "FastAPI service failed to start"
        sudo systemctl status "$APP_NAME" --no-pager
        exit 1
    fi
    
    # Test the application
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_info "Application health check passed"
    else
        log_warn "Application health check failed - checking logs..."
        sudo journalctl -u "$APP_NAME" --no-pager -n 20
    fi
}

# Print deployment summary
print_summary() {
    log_step "Deployment Summary"
    
    echo
    echo "🎉 FastAPI application deployed successfully!"
    echo
    echo "Application Details:"
    echo "  - App Directory: $APP_DIR"
    echo "  - Log Directory: $LOG_DIR"
    echo "  - Runtime Directory: $RUN_DIR"
    echo "  - Service User: $APP_USER"
    echo
    echo "Service Management:"
    echo "  - Start:   sudo systemctl start $APP_NAME"
    echo "  - Stop:    sudo systemctl stop $APP_NAME"
    echo "  - Restart: sudo systemctl restart $APP_NAME"
    echo "  - Status:  sudo systemctl status $APP_NAME"
    echo "  - Logs:    sudo journalctl -u $APP_NAME -f"
    echo
    echo "Health Check:"
    echo "  - URL: http://localhost/health"
    echo "  - Script: ${APP_DIR}/health_check.sh"
    echo
    echo "Configuration Files:"
    echo "  - Systemd: /etc/systemd/system/${APP_NAME}.service"
    echo "  - Nginx: /etc/nginx/sites-available/${APP_NAME}"
    echo "  - Gunicorn: ${APP_DIR}/gunicorn.conf.py"
    echo
}

# Main deployment function
main() {
    echo "🚀 FastAPI Production Deployment"
    echo "================================"
    echo
    
    # Parse command line arguments
    local process_manager="systemd"
    local skip_nginx=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --process-manager)
                process_manager="$2"
                shift 2
                ;;
            --skip-nginx)
                skip_nginx=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --process-manager <systemd|supervisor>  Choose process manager (default: systemd)"
                echo "  --skip-nginx                            Skip Nginx configuration"
                echo "  --help                                  Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Run deployment steps
    check_root
    check_dependencies
    install_system_packages
    setup_directories
    setup_python_environment
    setup_gunicorn
    
    case $process_manager in
        systemd)
            setup_systemd
            ;;
        supervisor)
            setup_supervisor
            ;;
        *)
            log_error "Invalid process manager: $process_manager"
            exit 1
            ;;
    esac
    
    if [[ "$skip_nginx" != true ]]; then
        setup_nginx
    fi
    
    setup_log_rotation
    setup_firewall
    create_health_check
    start_services
    print_summary
    
    log_info "Deployment completed successfully! 🎉"
}

# Run main function with all arguments
main "$@" 