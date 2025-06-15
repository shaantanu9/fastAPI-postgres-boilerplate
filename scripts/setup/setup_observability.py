#!/usr/bin/env python3
"""Free Observability Stack Setup for FastAPI
- Installs all free/open-source dependencies
- Creates monitoring directories
- Sets up configuration files
- Provides deployment instructions.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, check: bool = True) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            command, shell=True, check=check, capture_output=True, text=True,
        )
        if result.stdout:
            pass
        return True
    except subprocess.CalledProcessError:
        return False


def create_directories() -> None:
    """Create necessary directories for observability."""
    directories = [
        "logs",
        "monitoring/prometheus",
        "monitoring/grafana/provisioning/dashboards",
        "monitoring/grafana/provisioning/datasources",
        "monitoring/grafana/dashboards",
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def install_dependencies() -> bool:
    """Install observability dependencies."""
    # Install core dependencies
    if run_command("pip install -r requirements-observability.txt"):
        pass
    else:
        return False

    return True


def create_grafana_datasource() -> None:
    """Create Grafana datasource configuration."""
    datasource_config = """
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    orgId: 1
    url: http://prometheus:9090
    basicAuth: false
    isDefault: true
    editable: true
"""

    with Path("monitoring/grafana/provisioning/datasources/prometheus.yml").open("w") as f:
        f.write(datasource_config)


def create_grafana_dashboard_config() -> None:
    """Create Grafana dashboard configuration."""
    dashboard_config = """
apiVersion: 1

providers:
  - name: 'fastapi-dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
"""

    with Path("monitoring/grafana/provisioning/dashboards/dashboards.yml").open("w") as f:
        f.write(dashboard_config)


def create_basic_dashboard() -> None:
    """Create a basic FastAPI dashboard."""
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "FastAPI Application Metrics",
            "tags": ["fastapi", "python"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Request Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total[5m])",
                            "legendFormat": "{{method}} {{path}}",
                        },
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                },
                {
                    "id": 2,
                    "title": "Response Time",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "95th percentile",
                        },
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                },
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "5s",
        },
    }

    import json

    with Path("monitoring/grafana/dashboards/fastapi-dashboard.json").open("w") as f:
        json.dump(dashboard, f, indent=2)


def create_deployment_script() -> None:
    """Create deployment scripts."""
    # Start monitoring stack
    start_script = """#!/bin/bash
echo "🚀 Starting Free Observability Stack..."

# Start core monitoring (Prometheus + Grafana + Redis + MinIO)
docker-compose -f docker-compose.monitoring.yml up -d prometheus grafana redis minio

echo "⏳ Waiting for services to start..."
sleep 10

echo "✅ Monitoring stack is running!"
echo ""
echo "🔗 Available Services:"
echo "  📊 Grafana Dashboard: http://localhost:3000 (admin/grafana123)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  🗄️  Redis: localhost:6379"
echo "  💾 MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)"
echo ""
echo "🚀 Start your FastAPI app with: uvicorn app.main:app --reload"
"""

    with Path("start_monitoring.sh").open("w") as f:
        f.write(start_script)
    Path("start_monitoring.sh").chmod(0o755)

    # Stop monitoring stack
    stop_script = """#!/bin/bash
echo "🛑 Stopping monitoring stack..."
docker-compose -f docker-compose.monitoring.yml down
echo "✅ Monitoring stack stopped"
"""

    with Path("stop_monitoring.sh").open("w") as f:
        f.write(stop_script)
    Path("stop_monitoring.sh").chmod(0o755)


def create_readme() -> None:
    """Create comprehensive README for observability."""
    readme_content = """# 🔍 Free Observability Stack for FastAPI

A complete monitoring and observability solution using **100% free and open-source tools**.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│   Prometheus    │───▶│     Grafana     │
│  (Metrics API)  │    │  (Metrics DB)   │    │ (Visualization) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │     MinIO       │    │ Digital Ocean   │
│ (Cache/Queue)   │    │ (File Storage)  │    │    Droplet      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   python setup_observability.py
   ```

2. **Start Monitoring Stack**:
   ```bash
   ./start_monitoring.sh
   ```

3. **Start FastAPI Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Access Dashboards**:
   - 📊 **Grafana**: http://localhost:3000 (admin/grafana123)
   - 📈 **Prometheus**: http://localhost:9090
   - 💾 **MinIO**: http://localhost:9001 (minioadmin/minioadmin123)

## 📊 Available Metrics

### Application Metrics
- ✅ HTTP request duration and count
- ✅ Authentication attempts
- ✅ Database query performance
- ✅ Error rates and types
- ✅ Active user sessions

### System Metrics
- ✅ CPU usage and load average
- ✅ Memory consumption
- ✅ Disk space utilization
- ✅ Network I/O

### Business Metrics
- ✅ User registrations
- ✅ API operation counts
- ✅ Background task performance

## 🔍 Health Checks

The application provides comprehensive health endpoints:

- `/health` - Full system health check
- `/health/ready` - Kubernetes readiness probe
- `/health/live` - Kubernetes liveness probe
- `/metrics` - Prometheus metrics endpoint

## 📝 Structured Logging

All requests are logged with:
- ✅ Correlation IDs for request tracing
- ✅ JSON format for easy parsing
- ✅ Security event detection
- ✅ Performance timing
- ✅ User context tracking

## 🎯 Production Deployment

### Digital Ocean Droplet Setup

1. **Create Droplet** (minimum 2GB RAM recommended)
2. **Install Docker & Docker Compose**
3. **Clone repository and run setup**
4. **Configure firewall** (ports 8000, 3000, 9090)
5. **Set up reverse proxy** (Nginx/Caddy)

### Environment Variables
```bash
# .env file
LOG_LEVEL=INFO
ENVIRONMENT=production
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379
```

## 💰 Cost Breakdown

**Monthly costs for Digital Ocean hosting:**
- Basic Droplet (2GB): $12/month
- Block Storage (if needed): $1/month per 10GB
- **Total**: ~$13-15/month

**All monitoring tools**: $0 (100% open source)

## 🔧 Customization

### Adding Custom Metrics
```python
from app.core.metrics import metrics

# Record custom business metric
metrics.record_api_operation("order_created", "orders", success=True)
```

### Adding Health Checks
```python
from app.core.health import register_health_check

async def custom_health_check():
    # Your custom check logic
    return HealthCheck(name="service", status=HealthStatus.HEALTHY, ...)

register_health_check("my_service", custom_health_check)
```

## 📚 Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [FastAPI Monitoring Guide](https://fastapi.tiangolo.com/advanced/monitoring/)

## 🆘 Troubleshooting

### Common Issues
1. **Metrics not appearing**: Check `/metrics` endpoint accessibility
2. **Grafana login issues**: Default admin/grafana123
3. **Docker connection**: Ensure Docker Desktop is running

### Support
- Check logs: `docker-compose logs <service-name>`
- Restart services: `./stop_monitoring.sh && ./start_monitoring.sh`
"""

    with Path("README_OBSERVABILITY.md").open("w") as f:
        f.write(readme_content)


def main() -> None:
    """Main setup function."""
    # Create directories
    create_directories()

    # Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Create configuration files
    create_grafana_datasource()
    create_grafana_dashboard_config()
    create_basic_dashboard()

    # Create deployment scripts
    create_deployment_script()

    # Create documentation
    create_readme()



if __name__ == "__main__":
    main()
