#!/bin/bash

# Ruff Linting Script for FastAPI Project
# Usage: ./scripts/lint.sh [--fix] [--check] [--format]

set -e

echo "🔍 Running Ruff on FastAPI project..."

# Default options
FIX=false
CHECK_ONLY=false
FORMAT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX=true
            shift
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --format)
            FORMAT=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--fix] [--check] [--format]"
            echo "  --fix     Automatically fix issues where possible"
            echo "  --check   Run linting without making changes"
            echo "  --format  Format code using Ruff formatter"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run linting
if [ "$CHECK_ONLY" = true ]; then
    echo "📊 Running lint check only..."
    uv run ruff check .
elif [ "$FIX" = true ]; then
    echo "🔧 Running lint with auto-fix..."
    uv run ruff check . --fix
    echo "✅ Linting complete with fixes applied"
else
    echo "📋 Running basic lint check..."
    uv run ruff check .
fi

# Run formatting if requested
if [ "$FORMAT" = true ]; then
    echo "🎨 Formatting code..."
    uv run ruff format .
    echo "✅ Code formatting complete"
fi

echo "🎉 Ruff operations completed!" 