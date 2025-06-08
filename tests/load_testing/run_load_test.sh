#!/bin/bash
# Load Testing Runner Script

set -e

echo "🚀 Starting Load Testing Suite..."

# Configuration
HOST=${HOST:-"http://localhost:8000"}
USERS=${USERS:-50}
SPAWN_RATE=${SPAWN_RATE:-5}
RUN_TIME=${RUN_TIME:-"10m"}
OUTPUT_DIR="load_test_results"

# Create output directory
mkdir -p $OUTPUT_DIR
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "📋 Test Configuration:"
echo "  Host: $HOST"
echo "  Users: $USERS"
echo "  Spawn Rate: $SPAWN_RATE/sec"
echo "  Duration: $RUN_TIME"

# Run the load test
echo "🔄 Running load test..."
locust -f locust_config.py \
    --host=$HOST \
    --users=$USERS \
    --spawn-rate=$SPAWN_RATE \
    --run-time=$RUN_TIME \
    --headless \
    --html=$OUTPUT_DIR/report_$TIMESTAMP.html \
    --csv=$OUTPUT_DIR/results_$TIMESTAMP

echo "✅ Load test completed!"
echo "📊 Results saved to: $OUTPUT_DIR/"
