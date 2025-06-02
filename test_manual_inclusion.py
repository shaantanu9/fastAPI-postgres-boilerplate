#!/usr/bin/env python3
import sys
sys.path.append('.')

from app.main import app
from app.plugins.product_plugin import ProductRoutes

print("🧪 Testing Manual Product Router Inclusion")
print("=" * 45)

# Create and include the product router
routes_instance = ProductRoutes()
router = routes_instance.get_router()
app.include_router(router, prefix='/api/v1', tags=['Product'])

# Check for product routes
product_routes = [r.path for r in app.routes if hasattr(r, 'path') and 'product' in r.path.lower()]

print(f"✅ Product routes after manual inclusion ({len(product_routes)}):")
for route in sorted(product_routes):
    print(f"  - {route}")

print(f"\n📊 Total app routes: {len(app.routes)}") 