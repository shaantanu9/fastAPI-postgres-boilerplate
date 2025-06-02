#!/bin/bash
echo "🛑 Stopping monitoring stack..."
docker-compose -f docker-compose.monitoring.yml down
echo "✅ Monitoring stack stopped"
