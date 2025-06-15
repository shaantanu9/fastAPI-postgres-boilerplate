#!/bin/bash

# FastAPI Development Server with Gunicorn
# This script starts the FastAPI application using Gunicorn with development-friendly settings

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting FastAPI Development Server with Gunicorn${NC}"
echo "=================================================================="

# Set development environment
export ENVIRONMENT=development
export LOG_LEVEL=debug

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo -e "${RED}❌ Error: app/main.py not found. Please run from project root.${NC}"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Warning: No virtual environment detected. Consider activating your venv.${NC}"
fi

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo -e "${RED}❌ Error: gunicorn not found. Please install it:${NC}"
    echo "pip install gunicorn"
    exit 1
fi

echo -e "${GREEN}✅ Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}✅ Log Level: ${LOG_LEVEL}${NC}"
echo -e "${GREEN}✅ Config: scripts/setup/gunicorn.dev.conf.py${NC}"
echo ""

# Start the server
echo -e "${BLUE}Starting server...${NC}"
echo "=================================================================="

# Use the development configuration
gunicorn --config scripts/setup/gunicorn.dev.conf.py app.main:app

echo ""
echo -e "${GREEN}👋 Server stopped${NC}" 