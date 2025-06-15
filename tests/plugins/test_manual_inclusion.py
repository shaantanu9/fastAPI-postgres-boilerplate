#!/usr/bin/env python3
"""
TEST MANUAL PLUGIN INCLUSION TEST

PURPOSE:
    Test manual plugin inclusion
    
WHEN TO USE:
    Testing manual plugin inclusion methods
    
WHAT IT TESTS:
    Manual plugin inclusion processes
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/plugins/test_manual_inclusion.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

import sys

sys.path.append(".")

from app.main import app
from app.plugins.product_plugin import ProductRoutes

# Create and include the product router
routes_instance = ProductRoutes()
router = routes_instance.get_router()
app.include_router(router, prefix="/api/v1", tags=["Product"])

# Check for product routes
product_routes = [
    r.path for r in app.routes if hasattr(r, "path") and "product" in r.path.lower()
]

for _route in sorted(product_routes):
    pass

