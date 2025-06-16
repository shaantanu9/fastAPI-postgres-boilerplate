#!/bin/bash
# FastAPI PostgreSQL Boilerplate - Quick Start Script
# This script sets up the development environment quickly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🚀 FastAPI PostgreSQL Boilerplate - Quick Start Setup      ║
║                                                               ║
║   Enterprise-grade FastAPI application with PostgreSQL,      ║
║   Redis, plugin system, and production-ready features        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

log "Starting FastAPI PostgreSQL Boilerplate setup..."

# Step 1: Check prerequisites
log "Step 1: Checking prerequisites..."

# Check Python version
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log "Python version: $PYTHON_VERSION"
else
    error "Python 3 is required but not installed."
    exit 1
fi

# Check if Docker is available
if command -v docker >/dev/null 2>&1; then
    log "Docker is available"
    DOCKER_AVAILABLE=true
else
    warn "Docker not found. You'll need to install PostgreSQL and Redis manually."
    DOCKER_AVAILABLE=false
fi

# Check if uv is available
if command -v uv >/dev/null 2>&1; then
    log "uv package manager found"
    USE_UV=true
else
    warn "uv not found. Installing uv for faster package management..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    if command -v uv >/dev/null 2>&1; then
        log "uv installed successfully"
        USE_UV=true
    else
        warn "Failed to install uv. Falling back to pip."
        USE_UV=false
    fi
fi

# Step 2: Set up environment file
log "Step 2: Setting up environment configuration..."

if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        cp env.example .env
        log "Created .env file from env.example"
    else
        error "env.example file not found. Please create a .env file manually."
        exit 1
    fi
else
    warn ".env file already exists. Skipping environment setup."
fi

# Step 3: Create virtual environment and install dependencies
log "Step 3: Setting up Python environment..."

if [ "$USE_UV" = true ]; then
    log "Creating virtual environment with uv..."
    uv venv
    log "Installing dependencies with uv..."
    uv pip install -e .
else
    log "Creating virtual environment with venv..."
    python3 -m venv .venv
    log "Installing dependencies with pip..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
fi

log "Python environment setup complete"

# Step 4: Start database services
log "Step 4: Starting database services..."

if [ "$DOCKER_AVAILABLE" = true ]; then
    log "Starting PostgreSQL and Redis with Docker Compose..."
    docker-compose up -d db redis
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps db | grep -q "Up"; then
        log "PostgreSQL is running"
    else
        error "Failed to start PostgreSQL"
        exit 1
    fi
    
    if docker-compose ps redis | grep -q "Up"; then
        log "Redis is running"
    else
        error "Failed to start Redis"
        exit 1
    fi
else
    warn "Docker not available. Please ensure PostgreSQL and Redis are running manually."
    warn "PostgreSQL should be running on localhost:5432"
    warn "Redis should be running on localhost:6379"
    read -p "Press Enter when your services are ready..."
fi

# Step 5: Run database migrations
log "Step 5: Setting up database..."

if [ "$USE_UV" = true ]; then
    log "Running database migrations..."
    uv run alembic upgrade head
else
    source .venv/bin/activate
    log "Running database migrations..."
    alembic upgrade head
fi

log "Database setup complete"

# Step 6: Seed initial data (optional)
log "Step 6: Seeding initial data..."

read -p "Do you want to seed initial RBAC data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ "$USE_UV" = true ]; then
        uv run python -c "
import asyncio
from app.scripts.seed_rbac import seed_rbac
try:
    asyncio.run(seed_rbac())
    print('✅ RBAC data seeded successfully')
except Exception as e:
    print(f'❌ RBAC seeding failed: {e}')
"
    else
        source .venv/bin/activate
        python -c "
import asyncio
from app.scripts.seed_rbac import seed_rbac
try:
    asyncio.run(seed_rbac())
    print('✅ RBAC data seeded successfully')
except Exception as e:
    print(f'❌ RBAC seeding failed: {e}')
"
    fi
else
    info "Skipping data seeding"
fi

# Step 7: Run tests (optional)
log "Step 7: Running tests..."

read -p "Do you want to run the test suite? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ "$USE_UV" = true ]; then
        uv run pytest --tb=short
    else
        source .venv/bin/activate
        pytest --tb=short
    fi
else
    info "Skipping tests"
fi

# Step 8: Setup complete
log "Step 8: Setup complete! 🎉"

echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ✅ Setup Complete! Your FastAPI app is ready to go!        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}🚀 Quick Start Commands:${NC}"
echo ""
echo -e "${GREEN}Development Server:${NC}"
if [ "$USE_UV" = true ]; then
    echo "  uv run fastapi dev"
else
    echo "  source .venv/bin/activate && uvicorn app.main:app --reload"
fi
echo ""
echo -e "${GREEN}Production Server:${NC}"
echo "  ./scripts/start_production.sh"
echo "  # or"
echo "  gunicorn --config scripts/setup/gunicorn.stable.conf.py app.main:app"
echo ""
echo -e "${GREEN}Background Worker:${NC}"
if [ "$USE_UV" = true ]; then
    echo "  uv run python -m procrastinate worker"
else
    echo "  source .venv/bin/activate && python -m procrastinate worker"
fi
echo ""
echo -e "${GREEN}Run Tests:${NC}"
if [ "$USE_UV" = true ]; then
    echo "  uv run pytest"
else
    echo "  source .venv/bin/activate && pytest"
fi
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • ReDoc: http://localhost:8000/redoc"
echo "  • Health Check: http://localhost:8000/health"
echo "  • Plugin Status: http://localhost:8000/plugins/status"
echo ""
echo -e "${BLUE}🔧 Admin Interfaces:${NC}"
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo "  • Database Admin (Adminer): http://localhost:8080"
    echo "  • Redis Admin: http://localhost:8081"
fi
echo ""
echo -e "${BLUE}📖 Next Steps:${NC}"
echo "  1. Review and customize your .env file"
echo "  2. Start the development server"
echo "  3. Visit http://localhost:8000/docs to explore the API"
echo "  4. Create your first plugin with: python scaffold_generator_v4/main.py"
echo "  5. Read SETUP.md for detailed documentation"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "  • Change JWT_SECRET_TOKEN in .env for production"
echo "  • Review security settings before deploying"
echo "  • Check SETUP.md for production deployment guide"
echo ""
log "Happy coding! 🚀" 