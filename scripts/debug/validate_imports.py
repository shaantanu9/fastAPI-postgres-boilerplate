#!/usr/bin/env python3
"""
Import Validation Script
Validates that all imports are working correctly after codebase reorganization.
"""

import sys
import os
import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_import(module_path: str, description: str) -> bool:
    """Test if a module can be imported successfully."""
    try:
        if module_path.endswith('.py'):
            # For file paths, use spec_from_file_location
            spec = importlib.util.spec_from_file_location("test_module", module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"✅ {description}: {module_path}")
                return True
        else:
            # For module names, use standard import
            importlib.import_module(module_path)
            print(f"✅ {description}: {module_path}")
            return True
    except Exception as e:
        print(f"❌ {description}: {module_path} - Error: {e}")
        return False

def main():
    """Run import validation tests."""
    print("🔍 IMPORT VALIDATION AFTER CODEBASE REORGANIZATION")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test core app imports
    core_imports = [
        ("app.main", "Main FastAPI application"),
        ("app.core.config", "Configuration module"),
        ("app.services.auth_service", "Authentication service"),
        ("app.core.middleware_config", "Middleware configuration"),
        ("app.core.system_health", "System health checker"),
        ("app.core.procrastinate_enhanced", "Enhanced Procrastinate manager"),
        ("app.utils.procrastinate_manager", "Procrastinate manager"),
    ]
    
    print("\n📦 Core Application Imports:")
    for module, desc in core_imports:
        if test_import(module, desc):
            tests_passed += 1
        tests_total += 1
    
    # Test moved files exist and are accessible
    moved_files = [
        ("tests/utils/system_verification_test.py", "System verification test"),
        ("queue/procrastinate/workers/procrastinate_worker.py", "Procrastinate worker"),
        ("scripts/setup/gunicorn.conf.py", "Gunicorn configuration"),
        ("scripts/debug/lightweight_error_tracking.py", "Error tracking"),
        ("docs/guides/BOILERPLATE_COMPLETION_SUMMARY.md", "Completion summary"),
        ("docs/deployment/GUNICORN_PRODUCTION_GUIDE.md", "Gunicorn guide"),
    ]
    
    print("\n📁 Moved Files Accessibility:")
    for file_path, desc in moved_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {desc}: {file_path}")
            tests_passed += 1
        else:
            print(f"❌ {desc}: {file_path} - File not found")
        tests_total += 1
    
    # Test configuration files
    config_files = [
        ("docker-compose.procrastinate.yml", "Docker Compose Procrastinate"),
        ("Dockerfile", "Docker configuration"),
        ("production_configs/systemd/fastapi.service", "Systemd service"),
        ("production_configs/supervisor/fastapi.conf", "Supervisor config"),
    ]
    
    print("\n⚙️ Configuration Files:")
    for file_path, desc in config_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {desc}: {file_path}")
            tests_passed += 1
        else:
            print(f"❌ {desc}: {file_path} - File not found")
        tests_total += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 VALIDATION SUMMARY:")
    print(f"✅ Tests Passed: {tests_passed}/{tests_total}")
    print(f"❌ Tests Failed: {tests_total - tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("🎉 All imports and file paths are working correctly!")
        return 0
    else:
        print("⚠️ Some imports or file paths need attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 