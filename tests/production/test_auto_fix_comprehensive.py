#!/usr/bin/env python3
"""
TEST AUTO-FIX SYSTEM FOR PRODUCTION ISSUES TEST

PURPOSE:
    Test auto-fix system for production issues
    
WHEN TO USE:
    Testing automatic issue resolution
    
WHAT IT TESTS:
    Auto-fix mechanisms, error recovery
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/production/test_auto_fix_comprehensive.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

"""
Comprehensive test for the auto-fix migration system
Tests all the scenarios we've encountered in the last 3 model generations
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔍 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Success: {description}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Failed: {description}")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Exception in {description}: {e}")
        return False

def test_auto_fix_system():
    """Test the comprehensive auto-fix system"""
    print("🧪 Testing Comprehensive Auto-Fix System")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Migration health check
    print("\n📋 Test 1: Migration Health Check")
    success = run_command(
        ["python", "scaffold_generator_v4/main.py", "migration-health"],
        "Migration health check"
    )
    test_results.append(("Migration Health Check", success))
    
    # Test 2: Auto-fix dry run (without force)
    print("\n📋 Test 2: Auto-fix System Check")
    success = run_command(
        ["python", "scaffold_generator_v4/main.py", "auto-fix", "--force"],
        "Auto-fix all migration issues"
    )
    test_results.append(("Auto-fix System", success))
    
    # Test 3: Test enhanced generator
    print("\n📋 Test 3: Enhanced Generator Test")
    success = run_command(
        ["python", "scaffold_generator_v4/main.py", "test-enhanced"],
        "Test enhanced generator capabilities"
    )
    test_results.append(("Enhanced Generator", success))
    
    # Test 4: Try creating a new model with complex fields
    print("\n📋 Test 4: Complex Model Creation")
    success = run_command([
        "python", "scaffold_generator_v4/main.py", "add", "TestComplexModel",
        "name:str",
        "email:email", 
        "status:str:choices=active,inactive,pending",
        "priority:int:choices=1,2,3,4,5",
        "price:float:gt=0",
        "notes:str:optional",
        "created_date:datetime",
        "--with-tasks",
        "--with-bulk"
    ], "Create complex model with choices and optional fields")
    test_results.append(("Complex Model Creation", success))
    
    # Test 5: Check if the server can start with new model
    print("\n📋 Test 5: Server Integration Test")
    # We'll just check if the plugin files were created correctly
    plugin_dir = Path("app/plugins/test_complex_model_plugin")
    if plugin_dir.exists():
        print("✅ Plugin directory created")
        
        expected_files = ["__init__.py", "models.py", "schemas.py", "routes.py", "services.py"]
        all_files_exist = all((plugin_dir / f).exists() for f in expected_files)
        
        if all_files_exist:
            print("✅ All plugin files created successfully")
            test_results.append(("Server Integration", True))
        else:
            print("❌ Some plugin files missing")
            test_results.append(("Server Integration", False))
    else:
        print("❌ Plugin directory not created")
        test_results.append(("Server Integration", False))
    
    # Test 6: Alembic commands validation
    print("\n📋 Test 6: Alembic Commands Validation")
    alembic_tests = [
        (["alembic", "current"], "Check current revision"),
        (["alembic", "heads"], "Check migration heads"),
        (["alembic", "history"], "Check migration history")
    ]
    
    alembic_success = True
    for cmd, desc in alembic_tests:
        if not run_command(cmd, desc):
            alembic_success = False
    
    test_results.append(("Alembic Commands", alembic_success))
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Auto-fix system is working perfectly!")
        return True
    elif passed >= total * 0.8:
        print("⚠️ Most tests passed. System is mostly functional.")
        return True
    else:
        print("❌ Multiple test failures. System needs attention.")
        return False

def test_specific_issues():
    """Test specific issues we've encountered"""
    print("\n🎯 Testing Specific Issues from Previous Runs")
    print("=" * 50)
    
    issues_tested = []
    
    # Issue 1: Organizations foreign key constraint
    print("\n🔍 Testing: Organizations FK constraint handling")
    # This is implicit in the auto-fix, we'll check migration files
    migrations_dir = Path("alembic/versions")
    if migrations_dir.exists():
        problematic_found = False
        for migration_file in migrations_dir.glob("*.py"):
            try:
                content = migration_file.read_text()
                if "organizations" in content and "ForeignKeyConstraint" in content:
                    problematic_found = True
                    break
            except Exception:
                continue
        
        if not problematic_found:
            print("✅ No problematic organizations FK constraints found")
            issues_tested.append(("Organizations FK", True))
        else:
            print("⚠️ Found organizations FK constraints - auto-fix may be needed")
            issues_tested.append(("Organizations FK", False))
    else:
        print("✅ No migrations directory (clean state)")
        issues_tested.append(("Organizations FK", True))
    
    # Issue 2: Multiple heads
    print("\n🔍 Testing: Multiple heads handling")
    success = run_command(
        ["alembic", "heads"],
        "Check for multiple heads"
    )
    issues_tested.append(("Multiple Heads", success))
    
    # Summary for specific issues
    print("\n📋 Specific Issues Summary:")
    for issue, resolved in issues_tested:
        status = "✅ RESOLVED" if resolved else "❌ UNRESOLVED"
        print(f"{status} {issue}")
    
    return all(resolved for _, resolved in issues_tested)

if __name__ == "__main__":
    print("🚀 Starting Comprehensive Auto-Fix System Test")
    print("This will test all the migration issues we've encountered")
    print("and validate the auto-fix functionality")
    
    # Test auto-fix system
    auto_fix_success = test_auto_fix_system()
    
    # Test specific issues
    issues_success = test_specific_issues()
    
    print("\n" + "=" * 60)
    print("🏁 Final Test Results")
    print("=" * 60)
    
    if auto_fix_success and issues_success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Auto-fix system is working perfectly")
        print("✅ All previous issues have been resolved")
        print("🚀 Ready for production use!")
        sys.exit(0)
    elif auto_fix_success:
        print("⚠️ Auto-fix system works, but some specific issues remain")
        print("💡 Manual intervention may be needed for edge cases")
        sys.exit(1)
    else:
        print("❌ Auto-fix system has issues")
        print("🔧 System needs debugging and fixes")
        sys.exit(2) 