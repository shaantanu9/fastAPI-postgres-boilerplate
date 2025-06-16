#!/bin/bash

# Setup script for production features: Security Headers, Distributed Tracing, and Log Aggregation
# This script sets up the infrastructure and configurations needed for enterprise-grade monitoring

set -e

echo "🚀 Setting up Production Features for FastAPI Application"
echo "========================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are available"
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    
    mkdir -p monitoring/logstash/config
    mkdir -p monitoring/logstash/pipeline
    mkdir -p monitoring/filebeat
    mkdir -p monitoring/otel-collector
    mkdir -p monitoring/grafana/dashboards
    mkdir -p monitoring/kibana/config
    mkdir -p logs
    
    print_status "Directories created"
}

# Create Logstash configuration
create_logstash_config() {
    print_info "Creating Logstash configuration..."
    
    cat > monitoring/logstash/config/logstash.yml << 'EOF'
http.host: "0.0.0.0"
xpack.monitoring.elasticsearch.hosts: [ "http://elasticsearch:9200" ]
path.config: /usr/share/logstash/pipeline
EOF
    
    print_status "Logstash configuration created"
}

# Create Grafana dashboard for tracing
create_grafana_dashboard() {
    print_info "Creating Grafana dashboard for distributed tracing..."
    
    cat > monitoring/grafana/dashboards/tracing-dashboard.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "FastAPI Distributed Tracing",
    "tags": ["fastapi", "tracing", "jaeger"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{path}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      }
    ],
    "time": {"from": "now-1h", "to": "now"},
    "refresh": "5s"
  }
}
EOF
    
    print_status "Grafana dashboard created"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies with uv..."
    
    if command -v uv &> /dev/null; then
        # Sync dependencies with uv
        uv sync
        print_status "Python dependencies installed with uv"
    elif command -v pip &> /dev/null; then
        # Fallback to pip if uv is not available
        pip install -r requirements.txt
        print_status "Python dependencies installed with pip (fallback)"
    else
        print_warning "Neither uv nor pip found. Please install dependencies manually:"
        print_info "uv sync"
        print_info "or"
        print_info "pip install -r requirements.txt"
    fi
}

# Start monitoring services
start_monitoring() {
    print_info "Starting monitoring services..."
    
    # Start basic monitoring (Prometheus, Grafana, Jaeger)
    docker-compose -f docker-compose.monitoring.yml up -d prometheus grafana jaeger redis
    
    print_status "Basic monitoring services started"
    print_info "Prometheus: http://localhost:9090"
    print_info "Grafana: http://localhost:3000 (admin/grafana123)"
    print_info "Jaeger UI: http://localhost:16686"
}

# Start ELK stack (optional)
start_elk_stack() {
    read -p "Do you want to start the ELK stack for log aggregation? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Starting ELK stack..."
        docker-compose -f docker-compose.monitoring.yml --profile elastic up -d
        print_status "ELK stack started"
        print_info "Elasticsearch: http://localhost:9200"
        print_info "Kibana: http://localhost:5601"
        print_info "Logstash: localhost:5044 (beats), localhost:5000 (tcp)"
    else
        print_info "Skipping ELK stack setup"
    fi
}

# Create environment file with production settings
create_env_file() {
    print_info "Creating environment configuration..."
    
    if [ ! -f .env.production ]; then
        cat > .env.production << 'EOF'
# Production Environment Configuration

# Security Headers
SECURITY_HEADERS_ENABLED=true
CSP_POLICY="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; media-src 'self'; object-src 'none'; child-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self';"
HSTS_MAX_AGE=31536000
HSTS_INCLUDE_SUBDOMAINS=true
REFERRER_POLICY="strict-origin-when-cross-origin"

# Distributed Tracing
TRACING_ENABLED=true
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
JAEGER_COLLECTOR_ENDPOINT=http://localhost:14268/api/traces
OTEL_SERVICE_NAME=fastapi-postgres-app
OTEL_SERVICE_VERSION=1.0.0
OTEL_ENVIRONMENT=production
OTEL_TRACES_SAMPLER_ARG=0.1

# Log Aggregation
LOG_AGGREGATION_ENABLED=true
LOG_FORMAT=json
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX_PREFIX=fastapi-logs
LOGSTASH_HOST=localhost
LOGSTASH_PORT=5044
LOG_LEVEL=INFO

# Sensitive Data Fields (will be masked in logs)
LOG_SENSITIVE_DATA_FIELDS=["password", "token", "secret", "key", "authorization", "jwt", "api_key"]
EOF
        print_status "Environment configuration created (.env.production)"
    else
        print_warning "Environment file already exists (.env.production)"
    fi
}

# Test the setup
test_setup() {
    print_info "Testing the setup..."
    
    # Test Jaeger
    if curl -s http://localhost:16686/api/services > /dev/null; then
        print_status "Jaeger is accessible"
    else
        print_warning "Jaeger may not be ready yet (this is normal on first startup)"
    fi
    
    # Test Prometheus
    if curl -s http://localhost:9090/-/healthy > /dev/null; then
        print_status "Prometheus is healthy"
    else
        print_warning "Prometheus may not be ready yet"
    fi
    
    # Test Grafana
    if curl -s http://localhost:3000/api/health > /dev/null; then
        print_status "Grafana is accessible"
    else
        print_warning "Grafana may not be ready yet"
    fi
}

# Display final instructions
show_final_instructions() {
    echo
    echo "🎉 Production Features Setup Complete!"
    echo "====================================="
    echo
    print_info "Services Available:"
    echo "  • Jaeger UI: http://localhost:16686"
    echo "  • Prometheus: http://localhost:9090"
    echo "  • Grafana: http://localhost:3000 (admin/grafana123)"
    echo "  • Redis: localhost:6379"
    
    if docker-compose -f docker-compose.monitoring.yml ps | grep -q elasticsearch; then
        echo "  • Elasticsearch: http://localhost:9200"
        echo "  • Kibana: http://localhost:5601"
        echo "  • Logstash: localhost:5044 (beats), localhost:5000 (tcp)"
    fi
    
    echo
    print_info "Next Steps:"
    echo "  1. Copy .env.production to .env and adjust settings as needed"
    echo "  2. Start your FastAPI application with the new features enabled"
    echo "  3. Visit the monitoring dashboards to see traces and logs"
    echo "  4. Configure alerts and additional dashboards as needed"
    echo
    print_info "To stop all services:"
    echo "  docker-compose -f docker-compose.monitoring.yml down"
    echo
    print_info "To view logs:"
    echo "  docker-compose -f docker-compose.monitoring.yml logs -f [service-name]"
    echo
}

# Main execution
main() {
    check_docker
    create_directories
    create_logstash_config
    create_grafana_dashboard
    create_env_file
    install_dependencies
    start_monitoring
    start_elk_stack
    
    # Wait a bit for services to start
    print_info "Waiting for services to start..."
    sleep 10
    
    test_setup
    show_final_instructions
}

# Run main function
main "$@" 