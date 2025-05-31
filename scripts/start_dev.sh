#!/bin/bash
set -e

# FastAPI Development Server with Gunicorn + Uvicorn
# This script starts the FastAPI application using Gunicorn with Uvicorn workers for development

echo "🚀 Starting FastAPI Development Server"
echo "======================================="

# Set development environment
export ENVIRONMENT=development
export LOG_DIR="$HOME/logs"
export USE_UNIX_SOCKET=false

# Ensure log directory exists
mkdir -p "$LOG_DIR/fastapi"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not detected. Attempting to activate..."
    if [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please run: python -m venv .venv && source .venv/bin/activate"
        exit 1
    fi
fi

# Check if dependencies are installed
if ! python -c "import fastapi, uvicorn, gunicorn" 2>/dev/null; then
    echo "❌ Missing dependencies. Installing..."
    pip install fastapi uvicorn gunicorn
fi

echo ""
echo "🔧 Configuration:"
echo "   - Environment: $ENVIRONMENT"
echo "   - Log Directory: $LOG_DIR"
echo "   - Config File: gunicorn.dev.conf.py"
echo "   - Bind Address: 127.0.0.1:8000"
echo ""

# Start the development server
echo "🏃 Starting server..."
echo "📖 API Documentation: http://127.0.0.1:8000/docs"
echo "🔍 Health Check: http://127.0.0.1:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================="

exec gunicorn -c gunicorn.dev.conf.py app.main:app 