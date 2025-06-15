#!/usr/bin/env python3
"""
TEST APPLICATION LIFESPAN EVENTS TEST

PURPOSE:
    Test application lifespan events
    
WHEN TO USE:
    Testing startup and shutdown processes
    
WHAT IT TESTS:
    App startup, shutdown, lifespan events
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/system/test_lifespan.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

"""Test the lifespan function manually."""

import asyncio
import sys
sys.path.append(".")

async def test_lifespan():
    """Test lifespan function execution."""
    
    print("🔍 Testing Lifespan Function...")
    
    try:
        from app.main import lifespan, app
        print("✅ Imports successful")
        
        print("\n🚀 Starting lifespan context...")
        
        # Test the lifespan context manager
        async with lifespan(app):
            print("✅ Lifespan startup completed!")
            
            # Check if plugin system was initialized
            from app.main import _plugin_manager
            if _plugin_manager:
                print(f"✅ Plugin manager initialized!")
                status = _plugin_manager.get_plugin_status()
                print(f"📊 Found {len(status)} plugins:")
                
                for name, info in status.items():
                    print(f"  - {name}: {info['status']}")
                
                # Check app routes
                book_routes = [r for r in app.routes if hasattr(r, 'path') and 'book' in r.path.lower()]
                print(f"\n📋 Found {len(book_routes)} book routes:")
                for route in book_routes[:5]:
                    print(f"  - {route.path}")
                    
            else:
                print("❌ Plugin manager NOT initialized")
            
            print("\n✅ Lifespan test completed successfully!")
    
    except Exception as e:
        print(f"❌ Lifespan test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_lifespan())
