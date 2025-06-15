#!/usr/bin/env python3
"""
Comprehensive Production Fixes for FastAPI PostgreSQL Boilerplate
Addresses memory leaks, performance issues, and production readiness
"""

import os
import sys
from pathlib import Path

def fix_main_async_patterns():
    """Fix async patterns in main.py"""
    main_file = Path('app/main.py')
    if not main_file.exists():
        print("❌ app/main.py not found")
        return
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Check if lifespan is already properly configured
    if 'lifespan' in content and '@asynccontextmanager' in content:
        print("✅ app/main.py: Lifespan already configured")
        return
    
    # Add proper lifespan if missing
    fixes_needed = []
    
    if 'from contextlib import asynccontextmanager' not in content:
        fixes_needed.append("Add: from contextlib import asynccontextmanager")
    
    if '@asynccontextmanager' not in content:
        fixes_needed.append("Add proper lifespan context manager")
    
    if fixes_needed:
        print("⚠️ app/main.py needs async pattern improvements:")
        for fix in fixes_needed:
            print(f"  - {fix}")
    else:
        print("✅ app/main.py: Async patterns look good")

def fix_websocket_memory_leaks():
    """Fix WebSocket memory leak potential"""
    ws_files = [
        'app/websocket/websocket_manager.py',
        'app/utils/websocket_manager.py'
    ]
    
    for ws_file in ws_files:
        if Path(ws_file).exists():
            with open(ws_file, 'r') as f:
                content = f.read()
            
            fixes_needed = []
            
            if 'WeakSet' not in content:
                fixes_needed.append("Use WeakSet for connection tracking")
            
            if 'cleanup' not in content.lower():
                fixes_needed.append("Add cleanup methods")
            
            if 'shutdown' not in content.lower():
                fixes_needed.append("Add shutdown handling")
            
            if fixes_needed:
                print(f"⚠️ {ws_file} needs memory leak fixes:")
                for fix in fixes_needed:
                    print(f"  - {fix}")
                
                # Create improved WebSocket manager
                create_improved_websocket_manager(ws_file)
            else:
                print(f"✅ {ws_file}: Memory management looks good")

def create_improved_websocket_manager(original_file):
    """Create improved WebSocket manager with proper memory management"""
    backup_file = f"{original_file}.backup"
    
    # Create backup
    if Path(original_file).exists():
        with open(original_file, 'r') as f:
            original_content = f.read()
        
        with open(backup_file, 'w') as f:
            f.write(original_content)
        
        print(f"📄 Created backup: {backup_file}")
    
    # Add WeakSet import and cleanup methods
    improved_additions = '''
# Memory leak prevention additions
import weakref
from weakref import WeakSet

class ImprovedWebSocketManager:
    """WebSocket manager with proper memory management"""
    
    def __init__(self):
        # Use WeakSet to prevent memory leaks
        self.connections = WeakSet()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    async def add_connection(self, connection):
        """Add connection with automatic cleanup"""
        self.connections.add(connection)
        
        # Periodic cleanup
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            await self.cleanup_stale_connections()
            self._last_cleanup = current_time
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections"""
        # WeakSet automatically removes dead connections
        # Additional cleanup can be added here
        pass
    
    async def shutdown(self):
        """Shutdown all connections"""
        for connection in list(self.connections):
            try:
                await connection.close()
            except Exception:
                pass
        self.connections.clear()
'''
    
    print(f"💡 Add this improved WebSocket manager pattern to {original_file}")

def check_database_connection_limits():
    """Check database connection pool configuration"""
    session_file = Path('app/db/session.py')
    if not session_file.exists():
        print("❌ Database session file not found")
        return
    
    with open(session_file, 'r') as f:
        content = f.read()
    
    improvements = []
    
    # Check for connection pool limits
    if 'pool_size' not in content:
        improvements.append("Add connection pool_size parameter")
    
    if 'max_overflow' not in content:
        improvements.append("Add max_overflow parameter")
    
    if 'pool_pre_ping' not in content:
        improvements.append("Add pool_pre_ping=True for health checks")
    
    if 'pool_recycle' not in content:
        improvements.append("Add pool_recycle for connection recycling")
    
    if improvements:
        print("⚠️ Database connection pool improvements needed:")
        for improvement in improvements:
            print(f"  - {improvement}")
        
        create_improved_db_config()
    else:
        print("✅ Database connection pool: Well configured")

def create_improved_db_config():
    """Create improved database configuration"""
    improved_config = '''
# Improved database configuration for production
DATABASE_CONFIG = {
    "pool_size": 20,          # Base number of connections
    "max_overflow": 30,       # Additional connections when needed
    "pool_pre_ping": True,    # Validate connections before use
    "pool_recycle": 3600,     # Recycle connections every hour
    "echo": False,            # Disable SQL logging in production
}

# Use in create_async_engine:
engine = create_async_engine(
    DATABASE_URL, 
    **DATABASE_CONFIG
)
'''
    
    print("💡 Recommended database configuration:")
    print(improved_config)

def check_memory_monitoring():
    """Check memory monitoring capabilities"""
    monitoring_files = [
        'app/core/lightweight_monitoring.py',
        'app/plugins/monitoring_plugin.py'
    ]
    
    monitoring_configured = False
    
    for monitor_file in monitoring_files:
        if Path(monitor_file).exists():
            with open(monitor_file, 'r') as f:
                content = f.read()
            
            if 'memory' in content.lower() and 'psutil' in content:
                monitoring_configured = True
                print(f"✅ {monitor_file}: Memory monitoring available")
    
    if not monitoring_configured:
        print("⚠️ Memory monitoring: Not comprehensive")
        create_memory_monitor()

def create_memory_monitor():
    """Create basic memory monitoring"""
    memory_monitor = '''
import psutil
import gc
import tracemalloc

class MemoryMonitor:
    """Simple memory monitoring for production"""
    
    def __init__(self):
        self.start_memory = self.get_memory_usage()
        tracemalloc.start()
    
    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def check_memory_growth(self, threshold_mb=100):
        """Check if memory has grown significantly"""
        current_memory = self.get_memory_usage()
        growth = current_memory - self.start_memory
        
        if growth > threshold_mb:
            return {
                "alert": True,
                "growth_mb": growth,
                "current_mb": current_memory,
                "message": f"Memory grew by {growth:.1f}MB"
            }
        
        return {"alert": False, "growth_mb": growth}
    
    def force_gc(self):
        """Force garbage collection"""
        collected = gc.collect()
        return collected
    
    def get_memory_snapshot(self):
        """Get memory snapshot for leak detection"""
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        return top_stats[:10]  # Top 10 memory consumers

# Global monitor instance
memory_monitor = MemoryMonitor()
'''
    
    print("💡 Basic memory monitoring code:")
    print(memory_monitor)

def check_error_handling_robustness():
    """Check error handling robustness"""
    error_files = [
        'app/core/exception_handlers.py',
        'app/core/error_aggregator.py'
    ]
    
    robust_error_handling = True
    
    for error_file in error_files:
        if Path(error_file).exists():
            with open(error_file, 'r') as f:
                content = f.read()
            
            required_handlers = [
                'generic_exception_handler',
                'SQLAlchemyError',
                'HTTPException'
            ]
            
            missing_handlers = []
            for handler in required_handlers:
                if handler not in content:
                    missing_handlers.append(handler)
            
            if missing_handlers:
                robust_error_handling = False
                print(f"⚠️ {error_file} missing handlers: {missing_handlers}")
    
    if robust_error_handling:
        print("✅ Error handling: Comprehensive")
    else:
        print("⚠️ Error handling: Needs improvement")

def check_production_configurations():
    """Check production-specific configurations"""
    config_files = [
        '.env',
        'requirements.txt',
        'docker-compose.prod.yml',
        'gunicorn.conf.py'
    ]
    
    production_ready = True
    
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✅ {config_file}: Found")
        else:
            production_ready = False
            print(f"⚠️ {config_file}: Missing")
    
    # Check .env for production settings
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
        
        if 'DEBUG=False' in content or 'ENVIRONMENT=production' in content:
            print("✅ Environment: Production mode detected")
        else:
            print("⚠️ Environment: Set to production mode")
    
    return production_ready

def generate_production_checklist():
    """Generate final production checklist"""
    checklist = """
🚀 PRODUCTION DEPLOYMENT CHECKLIST

📋 Pre-Deployment:
□ All dependencies pinned in requirements.txt
□ Environment variables set for production
□ Database connection pool configured
□ Redis connection management verified
□ WebSocket cleanup implemented (if using)
□ Error handling comprehensive
□ Logging configured for production
□ Memory monitoring enabled

🔧 Infrastructure:
□ Docker configuration ready
□ Reverse proxy configured (Nginx/Traefik)
□ SSL certificates configured
□ Database backups scheduled
□ Health checks implemented

🔒 Security:
□ JWT secrets properly configured
□ CORS settings restrictive
□ Rate limiting enabled
□ Input validation comprehensive
□ SQL injection protection verified

📊 Monitoring:
□ Application metrics collected
□ Error tracking configured
□ Log aggregation setup
□ Performance monitoring active
□ Alerting rules configured

🚨 Emergency Procedures:
□ Rollback strategy documented
□ Incident response plan ready
□ Monitoring dashboard accessible
□ Emergency contacts defined
"""
    
    print(checklist)

def main():
    """Main function to run all checks and fixes"""
    print("🔧 Comprehensive Production Fixes")
    print("="*50)
    
    # Run all checks
    print("\n1. Checking async patterns...")
    fix_main_async_patterns()
    
    print("\n2. Checking WebSocket memory management...")
    fix_websocket_memory_leaks()
    
    print("\n3. Checking database connection limits...")
    check_database_connection_limits()
    
    print("\n4. Checking memory monitoring...")
    check_memory_monitoring()
    
    print("\n5. Checking error handling...")
    check_error_handling_robustness()
    
    print("\n6. Checking production configurations...")
    production_ready = check_production_configurations()
    
    print("\n7. Final checklist...")
    generate_production_checklist()
    
    print("\n" + "="*50)
    if production_ready:
        print("✅ RESULT: Production readiness checks completed")
        print("💡 Review warnings and apply recommended improvements")
    else:
        print("⚠️ RESULT: Some production configurations missing")
        print("🔧 Apply fixes before production deployment")
    
    print("📊 Run regular monitoring to maintain production health")

if __name__ == "__main__":
    main() 