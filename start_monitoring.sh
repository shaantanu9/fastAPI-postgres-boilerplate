#!/bin/bash
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
