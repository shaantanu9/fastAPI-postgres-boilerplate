#!/bin/bash
set -e

# Test Gunicorn Configuration Script
# This script validates Gunicorn configurations without starting the server

echo "🧪 Testing Gunicorn Configurations"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${BLUE}Testing:${NC} $test_name"
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED:${NC} $test_name"
        ((test_passed++))
    else
        echo -e "${RED}❌ FAILED:${NC} $test_name"
        echo -e "${YELLOW}Command:${NC} $test_command"
        ((test_failed++))
    fi
    echo
}

# Test 1: Development Configuration
export ENVIRONMENT=development
export LOG_DIR="$HOME/logs"
run_test "Development Config Check" "gunicorn --check-config -c gunicorn.dev.conf.py app.main:app"

# Test 2: Production Configuration (Development Mode)
run_test "Production Config (Dev Mode)" "ENVIRONMENT=development LOG_DIR=\$HOME/logs gunicorn --check-config -c production_configs/gunicorn.conf.py app.main:app"

# Test 3: Production Configuration (Staging Mode)
run_test "Production Config (Staging Mode)" "ENVIRONMENT=staging LOG_DIR=\$HOME/logs gunicorn --check-config -c production_configs/gunicorn.conf.py app.main:app"

# Test 4: Production Configuration (Production Mode with TCP)
run_test "Production Config (Production TCP)" "ENVIRONMENT=production LOG_DIR=\$HOME/logs USE_UNIX_SOCKET=false gunicorn --check-config -c production_configs/gunicorn.conf.py app.main:app"

# Test 5: FastAPI App Import
run_test "FastAPI App Import" "python -c 'from app.main import app; print(\"FastAPI app imported successfully\")'"

# Test 6: Uvicorn Worker Import
run_test "Uvicorn Worker Import" "python -c 'import uvicorn.workers; print(\"UvicornWorker available\")'"

# Test 7: Gunicorn Version Check
run_test "Gunicorn Installation" "gunicorn --version"

# Test 8: Dependencies Check
run_test "Required Dependencies" "python -c 'import fastapi, uvicorn, gunicorn, sqlalchemy, asyncpg; print(\"All dependencies available\")'"

echo "=================================="
echo -e "${GREEN}✅ Tests Passed: $test_passed${NC}"
echo -e "${RED}❌ Tests Failed: $test_failed${NC}"
echo "=================================="

if [ $test_failed -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Gunicorn configuration is ready.${NC}"
    echo
    echo "Next steps:"
    echo "1. Development: ./scripts/start_dev.sh"
    echo "2. Production: Use production_configs/scripts/deploy.sh"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please fix the issues above.${NC}"
    exit 1
fi 