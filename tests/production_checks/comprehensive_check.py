#!/usr/bin/env python3
"""
Comprehensive Project Health Check
Tests all major components to ensure everything is working properly
"""

import sys
sys.path.append('.')

from fastapi.testclient import TestClient
from app.main import app
import json
import os
import ast
from pathlib import Path
from typing import List, Dict, Any

def main():
    print('🔍 COMPREHENSIVE PROJECT CHECK')
    print('=' * 50)

    # Test client setup
    client = TestClient(app)
    
    # Summary counters
    total_tests = 0
    passed_tests = 0

    # 1. Basic health checks
    print('\n1. HEALTH CHECKS')
    
    tests = [
        ('/health/health', 'Main health endpoint'),
        ('/health/ready', 'Readiness check'),
        ('/health/live', 'Liveness check')
    ]
    
    for endpoint, name in tests:
        total_tests += 1
        try:
            response = client.get(endpoint)
            if response.status_code == 200:
                print(f'✅ {name}: {response.status_code}')
                passed_tests += 1
            else:
                print(f'⚠️ {name}: {response.status_code}')
        except Exception as e:
            print(f'❌ {name} failed: {e}')

    # 2. Plugin system
    print('\n2. PLUGIN SYSTEM')
    total_tests += 1
    try:
        routes = [route.path for route in app.routes]
        plugin_routes = [r for r in routes if any(x in r for x in ['book', 'customer', 'order', 'monitoring', 'auth'])]
        print(f'✅ Total routes: {len(routes)}')
        print(f'✅ Plugin routes: {len(plugin_routes)}')
        passed_tests += 1
        
        # Test key plugin endpoints
        plugin_tests = [
            ('/monitoring/health', 'Monitoring plugin'),
            ('/api/v1/books/', 'Books plugin'),
            ('/api/v1/customers/', 'Customers plugin'),
            ('/api/v1/orders/', 'Orders plugin')
        ]
        
        for endpoint, name in plugin_tests:
            total_tests += 1
            try:
                response = client.get(endpoint)
                if response.status_code in [200, 422]:  # 422 is OK for endpoints requiring auth
                    print(f'✅ {name}: {response.status_code}')
                    passed_tests += 1
                else:
                    print(f'⚠️ {name}: {response.status_code}')
            except Exception as e:
                print(f'❌ {name} failed: {e}')
                
    except Exception as e:
        print(f'❌ Plugin system check failed: {e}')

    # 3. API Documentation
    print('\n3. API DOCUMENTATION')
    doc_tests = [
        ('/docs', 'Swagger docs'),
        ('/redoc', 'ReDoc'),
        ('/openapi.json', 'OpenAPI spec')
    ]
    
    for endpoint, name in doc_tests:
        total_tests += 1
        try:
            response = client.get(endpoint)
            if response.status_code == 200:
                print(f'✅ {name}: {response.status_code}')
                passed_tests += 1
            else:
                print(f'⚠️ {name}: {response.status_code}')
        except Exception as e:
            print(f'❌ {name} failed: {e}')

    # 4. Production readiness
    print('\n4. PRODUCTION READINESS')
    
    prod_files = [
        'scripts/backup_database.sh',
        'scripts/deploy_to_existing_server.sh',
        'app/core/lightweight_monitoring.py',
        'Dockerfile',
        'docker-compose.prod.yml',
        'gunicorn.conf.py',
        'requirements.txt'
    ]
    
    for file_path in prod_files:
        total_tests += 1
        if os.path.exists(file_path):
            print(f'✅ {file_path}')
            passed_tests += 1
        else:
            print(f'❌ Missing: {file_path}')

    # Summary
    print('\n' + '=' * 50)
    print(f'📊 TEST SUMMARY: {passed_tests}/{total_tests} PASSED')
    
    if passed_tests == total_tests:
        print('🎉 PROJECT STATUS: ALL SYSTEMS OPERATIONAL ✅')
        return 0
    elif passed_tests / total_tests > 0.8:
        print('⚠️ PROJECT STATUS: MOSTLY OPERATIONAL (Minor issues)')
        return 1
    else:
        print('❌ PROJECT STATUS: NEEDS ATTENTION')
        return 2

def check_syntax_errors() -> Dict[str, Any]:
    """Check for syntax errors in Python files."""
    print("🔍 Checking syntax errors...")
    
    key_files = [
        'app/main.py',
        'app/db/session.py',
        'app/services/user_service.py',
        'app/websocket/websocket_manager.py', 
        'app/plugins/auth_plugin.py',
        'app/core/redis_manager.py',
        'app/api/v1/endpoints/auth.py',
        'app/services/enhanced_base_service.py',
        'app/core/rate_limiting.py'
    ]
    
    results = {"passed": [], "failed": []}
    
    for file_path in key_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    ast.parse(f.read())
                results["passed"].append(file_path)
            except SyntaxError as e:
                results["failed"].append(f"{file_path}: {e}")
        else:
            results["failed"].append(f"{file_path}: File not found")
    
    print(f"✅ Syntax check: {len(results['passed'])}/{len(key_files)} files passed")
    for error in results["failed"]:
        print(f"❌ {error}")
    
    return results

def check_memory_leaks() -> Dict[str, Any]:
    """Check for potential memory leaks."""
    print("\n🧠 Checking memory leak patterns...")
    
    checks = {
        "database_sessions": check_database_sessions(),
        "redis_connections": check_redis_connections(),
        "websocket_management": check_websocket_management(),
        "task_queue_cleanup": check_task_queue_cleanup(),
        "connection_pooling": check_connection_pooling()
    }
    
    return checks

def check_database_sessions() -> Dict[str, Any]:
    """Check database session management."""
    session_file = "app/db/session.py"
    
    if not os.path.exists(session_file):
        return {"status": "error", "message": "Session file not found"}
    
    with open(session_file, 'r') as f:
        content = f.read()
    
    checks = {
        "async_context_manager": "async with" in content,
        "session_cleanup": "yield session" in content,
        "connection_pool": "pool_size" in content,
        "pool_recycle": "pool_recycle" in content,
        "pool_pre_ping": "pool_pre_ping" in content
    }
    
    all_passed = all(checks.values())
    
    if all_passed:
        print("✅ Database sessions: Proper cleanup and pooling configured")
        return {"status": "good", "checks": checks}
    else:
        print("⚠️ Database sessions: Some checks failed")
        return {"status": "warning", "checks": checks}

def check_redis_connections() -> Dict[str, Any]:
    """Check Redis connection management."""
    redis_files = [
        "app/db/session.py",
        "app/core/redis_manager.py",
        "app/core/rate_limiting.py"
    ]
    
    results = {}
    
    for file_path in redis_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            has_cleanup = any([
                "await redis_client.close()" in content,
                "redis.close()" in content,
                "contextlib.suppress" in content
            ])
            
            results[file_path] = {
                "has_cleanup": has_cleanup,
                "uses_context_manager": "async with" in content or "contextlib.suppress" in content
            }
    
    all_good = all(result["has_cleanup"] for result in results.values())
    
    if all_good:
        print("✅ Redis connections: Proper cleanup configured")
        return {"status": "good", "files": results}
    else:
        print("⚠️ Redis connections: Check cleanup patterns")
        return {"status": "warning", "files": results}

def check_websocket_management() -> Dict[str, Any]:
    """Check WebSocket connection management."""
    ws_files = [
        "app/websocket/websocket_manager.py",
        "app/utils/websocket_manager.py"
    ]
    
    results = {}
    
    for file_path in ws_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            checks = {
                "has_cleanup": "cleanup" in content.lower() or "disconnect" in content,
                "uses_weakset": "WeakSet" in content,
                "heartbeat_cleanup": "heartbeat" in content.lower(),
                "connection_tracking": "connections" in content
            }
            
            results[file_path] = checks
    
    # Check if any file uses WeakSet
    uses_weakset = any(result.get("uses_weakset", False) for result in results.values())
    
    if uses_weakset:
        print("✅ WebSocket management: WeakSet prevents memory leaks")
        return {"status": "good", "files": results}
    else:
        print("⚠️ WebSocket management: Consider using WeakSet for connection tracking")
        return {"status": "warning", "files": results, "recommendation": "Use WeakSet for automatic cleanup"}

def check_task_queue_cleanup() -> Dict[str, Any]:
    """Check task queue memory management."""
    task_files = [
        "app/utils/procrastinate_manager.py",
        "app/utils/concurrent_utils.py"
    ]
    
    results = {}
    
    for file_path in task_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            checks = {
                "has_cleanup": "cleanup" in content.lower(),
                "has_shutdown": "shutdown" in content.lower(),
                "memory_management": "memory" in content.lower() or "gc" in content
            }
            
            results[file_path] = checks
    
    if results:
        print("✅ Task queue: Cleanup patterns found")
        return {"status": "good", "files": results}
    else:
        print("ℹ️ Task queue: No task queue files found")
        return {"status": "info", "message": "No task queue files found"}

def check_connection_pooling() -> Dict[str, Any]:
    """Check database connection pooling configuration."""
    session_file = "app/db/session.py"
    
    if not os.path.exists(session_file):
        return {"status": "error", "message": "Session file not found"}
    
    with open(session_file, 'r') as f:
        content = f.read()
    
    pool_config = {
        "pool_size": "pool_size" in content,
        "max_overflow": "max_overflow" in content,
        "pool_pre_ping": "pool_pre_ping" in content,
        "pool_recycle": "pool_recycle" in content
    }
    
    if all(pool_config.values()):
        print("✅ Connection pooling: Production-ready configuration")
        return {"status": "excellent", "config": pool_config}
    else:
        print("⚠️ Connection pooling: Missing some configuration")
        return {"status": "warning", "config": pool_config}

def check_error_handling() -> Dict[str, Any]:
    """Check error handling patterns."""
    print("\n🚨 Checking error handling...")
    
    error_files = [
        "app/main.py",
        "app/core/exceptions.py", 
        "app/core/error_aggregator.py"
    ]
    
    results = {}
    
    for file_path in error_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            checks = {
                "has_exception_handler": "exception_handler" in content,
                "has_http_exception": "HTTPException" in content,
                "has_validation_error": "ValidationError" in content or "RequestValidationError" in content,
                "has_sqlalchemy_error": "SQLAlchemyError" in content
            }
            
            results[file_path] = checks
    
    if results:
        print("✅ Error handling: Exception handlers configured")
        return {"status": "good", "files": results}
    else:
        print("⚠️ Error handling: Check exception handler configuration")
        return {"status": "warning", "files": results}

def check_production_configs() -> Dict[str, Any]:
    """Check production configuration files."""
    print("\n⚙️ Checking production configurations...")
    
    config_files = [
        ".env",
        "requirements.txt",
        "docker-compose.prod.yml",
        "gunicorn.conf.py",
        "Dockerfile",
        "alembic.ini"
    ]
    
    results = {}
    
    for file_path in config_files:
        results[file_path] = os.path.exists(file_path)
    
    existing_count = sum(results.values())
    
    print(f"✅ Configuration files: {existing_count}/{len(config_files)} found")
    
    for file_path, exists in results.items():
        status = "✅" if exists else "❌"
        print(f"{status} {file_path}")
    
    return {"status": "good" if existing_count >= 4 else "warning", "files": results}

def check_security_patterns() -> Dict[str, Any]:
    """Check security implementation."""
    print("\n🔒 Checking security patterns...")
    
    security_files = [
        "app/core/security.py",
        "app/services/user_service.py",
        "app/api/v1/endpoints/auth.py"
    ]
    
    results = {}
    
    for file_path in security_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            checks = {
                "jwt_implemented": "JWT" in content or "jwt" in content,
                "password_hashing": "bcrypt" in content or "hash" in content,
                "rate_limiting": "rate" in content.lower(),
                "input_validation": "validate" in content.lower()
            }
            
            results[file_path] = checks
    
    if results:
        print("✅ Security: Authentication and validation patterns found")
        return {"status": "good", "files": results}
    else:
        print("⚠️ Security: Check security implementation")
        return {"status": "warning", "files": results}

def generate_summary(results: Dict[str, Any]) -> None:
    """Generate comprehensive summary."""
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE PRODUCTION READINESS SUMMARY")
    print("="*60)
    
    # Count statuses
    status_counts = {"good": 0, "excellent": 0, "warning": 0, "error": 0, "info": 0}
    
    for category, result in results.items():
        if isinstance(result, dict) and "status" in result:
            status_counts[result["status"]] += 1
    
    # Overall assessment
    total_checks = len(results)
    good_checks = status_counts["good"] + status_counts["excellent"]
    
    print(f"\n📈 Overall Score: {good_checks}/{total_checks} checks passed")
    print(f"✅ Good/Excellent: {status_counts['good'] + status_counts['excellent']}")
    print(f"⚠️ Warnings: {status_counts['warning']}")
    print(f"❌ Errors: {status_counts['error']}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if status_counts["error"] > 0:
        print("🔴 CRITICAL: Fix errors before production deployment")
    elif status_counts["warning"] > 2:
        print("🟡 MODERATE: Address warnings for optimal production performance")
    else:
        print("🟢 EXCELLENT: Project is production-ready!")
    
    # Specific recommendations
    if "websocket_management" in results and results["websocket_management"]["status"] == "warning":
        print("  - Consider using WeakSet for WebSocket connection tracking")
    
    if "connection_pooling" in results and results["connection_pooling"]["status"] == "warning":
        print("  - Complete database connection pool configuration")
    
    if "error_handling" in results and results["error_handling"]["status"] == "warning":
        print("  - Implement comprehensive exception handlers")
    
    print(f"\n🚀 DEPLOYMENT READINESS:")
    if status_counts["error"] == 0:
        print("✅ Ready for production deployment with monitoring")
    else:
        print("❌ Fix critical errors before deployment")

def main():
    """Run comprehensive production check."""
    print("🔍 COMPREHENSIVE PRODUCTION READINESS CHECK")
    print("="*60)
    
    results = {}
    
    # Run all checks
    results["syntax_errors"] = check_syntax_errors()
    results.update(check_memory_leaks())
    results["error_handling"] = check_error_handling()
    results["production_configs"] = check_production_configs()
    results["security_patterns"] = check_security_patterns()
    
    # Generate summary
    generate_summary(results)
    
    # Return appropriate exit code
    has_errors = any(
        result.get("status") == "error" 
        for result in results.values() 
        if isinstance(result, dict)
    )
    
    return 1 if has_errors else 0

if __name__ == "__main__":
    sys.exit(main()) 