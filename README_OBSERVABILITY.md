# 🔍 Free Observability Stack for FastAPI

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
