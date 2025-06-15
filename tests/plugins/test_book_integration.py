#!/usr/bin/env python3
"""
TEST BOOK PLUGIN INTEGRATION WITH SYSTEM TEST

PURPOSE:
    Test book plugin integration with system
    
WHEN TO USE:
    Testing book plugin integration
    
WHAT IT TESTS:
    Book plugin routes, database integration
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/plugins/test_book_integration.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

"""Test Book plugin integration with main FastAPI app."""

try:
    from app.plugins.book_plugin import register_plugin
    from app.core.plugin_system import PluginContext
    from fastapi import FastAPI
    
    app = FastAPI()
    context = PluginContext(app)
    result = register_plugin(app, context)
    print(f'✅ Book plugin registration test: {result}')
    
    # Check routes
    book_routes = [r.path for r in app.routes if hasattr(r, 'path') and 'book' in r.path.lower()]
    print(f'📋 Book routes found: {len(book_routes)}')
    for route in book_routes[:5]:
        print(f'  - {route}')
        
    # Try importing main app to see if there are conflicts
    print("\n🔍 Testing main app import...")
    from app.main import app as main_app
    
    print("✅ Main app imported successfully")
    print(f"📊 Main app total routes: {len([r for r in main_app.routes if hasattr(r, 'path')])}")
    
    # Check if Book routes exist in main app
    main_book_routes = [r.path for r in main_app.routes if hasattr(r, 'path') and 'book' in r.path.lower()]
    print(f"📋 Book routes in main app: {len(main_book_routes)}")
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc() 