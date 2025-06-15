#!/usr/bin/env python3
"""
Test import script for scaffold generator
"""
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("Testing imports...")

try:
    print("1. Testing core imports...")
    from core import FieldValidator, MigrationManager, InfrastructureChecker, PluginValidator
    print("   ✅ Core imports successful")
except ImportError as e:
    print(f"   ❌ Core imports failed: {e}")
    sys.exit(1)

try:
    print("2. Testing template imports individually...")
    
    print("   2a. Testing ModelsTemplate...")
    from templates.models_template import ModelsTemplate
    print("      ✅ ModelsTemplate successful")
    
    print("   2b. Testing SchemasTemplate...")
    from templates.schemas_template import SchemasTemplate
    print("      ✅ SchemasTemplate successful")
    
    print("   2c. Testing ServicesTemplate...")
    from templates.services_template import ServicesTemplate
    print("      ✅ ServicesTemplate successful")
    
    print("   2d. Testing RoutesTemplate...")
    from templates.routes_template import RoutesTemplate
    print("      ✅ RoutesTemplate successful")
    
    print("   2e. Testing EnhancedRoutesTemplate...")
    from templates.enhanced_routes_template import EnhancedRoutesTemplate
    print("      ✅ EnhancedRoutesTemplate successful")
    
    print("   2f. Testing TasksTemplate...")
    from templates.tasks_template import TasksTemplate
    print("      ✅ TasksTemplate successful")
    
    print("   2g. Testing InitTemplate...")
    from templates.init_template import InitTemplate
    print("      ✅ InitTemplate successful")
    
    print("   ✅ All individual template imports successful")
except ImportError as e:
    print(f"   ❌ Individual template imports failed: {e}")
    print(f"      Specific error: {type(e).__name__}: {e}")
    sys.exit(1)

try:
    print("3. Testing enhanced template imports...")
    from templates import RoutesTemplate, EnhancedRoutesTemplate, TasksTemplate, InitTemplate
    print("   ✅ Enhanced template imports successful")
except ImportError as e:
    print(f"   ❌ Enhanced template imports failed: {e}")
    print(f"      Specific error: {type(e).__name__}: {e}")

try:
    print("4. Testing auth template imports...")
    from templates.auth_routes_template import AuthRoutesTemplate
    from templates.auth_models_template import AuthModelsTemplate
    print("   ✅ Auth template imports successful")
except ImportError as e:
    print(f"   ❌ Auth template imports failed: {e}")
    print(f"      Specific error: {type(e).__name__}: {e}")

try:
    print("5. Testing analyzer imports...")
    from analyzers import ArchitectureAnalyzer
    print("   ✅ Analyzer imports successful")
except ImportError as e:
    print(f"   ❌ Analyzer imports failed: {e}")

try:
    print("6. Testing testing module imports...")
    from testing import TestGenerator, TestConfig
    print("   ✅ Testing module imports successful")
except ImportError as e:
    print(f"   ❌ Testing module imports failed: {e}")

try:
    print("7. Testing migration imports...")
    from migrations import SmartMigrationManager
    print("   ✅ Migration imports successful")
except ImportError as e:
    print(f"   ❌ Migration imports failed: {e}")

print("\n🎉 All imports tested successfully!")
print("You can now use the scaffold generator!") 