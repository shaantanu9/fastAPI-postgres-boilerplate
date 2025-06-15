#!/usr/bin/env python3
"""
TEST MANUAL REGISTRATION MECHANISMS TEST

PURPOSE:
    Test manual registration mechanisms
    
WHEN TO USE:
    Testing manual registration flows
    
WHAT IT TESTS:
    Manual registration processes
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/plugins/test_manual_registration.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

"""Manually register Book plugin and test routes."""

import asyncio
import sys
sys.path.append(".")

async def test_manual_registration():
    """Test manual Book plugin registration."""
    
    print("🔍 Testing Manual Book Plugin Registration...")
    
    try:
        from fastapi import FastAPI
        from app.core.plugin_system import PluginContext
        from app.plugins.book_plugin import register_plugin
        
        # Create a fresh FastAPI app
        app = FastAPI(title="Test App with Book Plugin")
        context = PluginContext(app)
        
        print("✅ Created test app and context")
        
        # Manually register Book plugin
        success = register_plugin(app, context)
        print(f"✅ Book plugin registration: {success}")
        
        # Check routes
        book_routes = [r for r in app.routes if hasattr(r, 'path') and 'book' in r.path.lower()]
        print(f"📋 Found {len(book_routes)} book routes:")
        for route in book_routes:
            print(f"  - {route.path} ({route.methods})")
        
        # Test with actual server startup
        print("\n🚀 Testing with test server...")
        
        import uvicorn
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            print("🔧 Test lifespan: Starting up...")
            # Register Book plugin during lifespan
            success = register_plugin(app, context)
            print(f"🔧 Test lifespan: Book plugin registered: {success}")
            yield
            print("🔧 Test lifespan: Shutting down...")
        
        # Create app with lifespan
        test_app = FastAPI(title="Test App", lifespan=lifespan)
        
        # Check routes after manual registration
        register_plugin(test_app, PluginContext(test_app))
        book_routes = [r for r in test_app.routes if hasattr(r, 'path') and 'book' in r.path.lower()]
        print(f"📋 Test app has {len(book_routes)} book routes:")
        for route in book_routes[:5]:
            print(f"  - {route.path}")
        
        # Generate OpenAPI spec to see if routes are included
        openapi_spec = test_app.openapi()
        book_paths = [path for path in openapi_spec.get('paths', {}).keys() if 'book' in path.lower()]
        print(f"📄 OpenAPI spec has {len(book_paths)} book paths:")
        for path in book_paths:
            print(f"  - {path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Manual registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_manual_registration())
    if success:
        print("\n✅ Manual registration test PASSED!")
    else:
        print("\n❌ Manual registration test FAILED!") 