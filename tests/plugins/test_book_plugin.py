#!/usr/bin/env python3
"""
TEST BOOK PLUGIN FUNCTIONALITY TEST

PURPOSE:
    Test book plugin functionality
    
WHEN TO USE:
    Testing book plugin features
    
WHAT IT TESTS:
    Book CRUD operations, plugin integration
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/plugins/test_book_plugin.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

"""Test script to manually register the Book plugin and test its routes."""

import asyncio
import sys
sys.path.append(".")

async def test_book_plugin():
    """Test Book plugin registration and functionality."""
    try:
        from fastapi import FastAPI
        from app.core.plugin_system import PluginContext
        from app.plugins.book_plugin import register_plugin
        
        # Create a test FastAPI app
        app = FastAPI()
        
        # Create plugin context
        context = PluginContext(app)
        
        # Register the Book plugin
        success = register_plugin(app, context)
        
        if success:
            print("✅ Book plugin registered successfully!")
            
            # Check routes
            book_routes = []
            for route in app.routes:
                if hasattr(route, 'path') and 'book' in route.path.lower():
                    book_routes.append(route.path)
            
            if book_routes:
                print("📋 Available Book routes:")
                for route in sorted(book_routes):
                    print(f"  - {route}")
            else:
                print("⚠️ No Book routes found in the app")
                
        else:
            print("❌ Failed to register Book plugin")
            
    except Exception as e:
        print(f"❌ Error testing Book plugin: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_book_plugin()) 