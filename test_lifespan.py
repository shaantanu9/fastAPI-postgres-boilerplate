import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test_lifespan():
    print('🚀 Testing Lifespan and Plugin Initialization')
    print('=' * 50)
    
    # Create test client which should trigger lifespan
    print('Creating TestClient to trigger lifespan...')
    with TestClient(app) as client:
        # Check routes after lifespan
        order_routes = [r for r in app.routes if hasattr(r, 'path') and '/orders' in r.path]
        print(f'📍 Order routes after TestClient: {len(order_routes)}')
        
        for route in order_routes:
            methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'Unknown'
            print(f'  - {route.path} [{methods}]')
        
        # Test a simple GET request
        if order_routes:
            print('\n🧪 Testing Order API endpoint...')
            response = client.get('/orders/')
            print(f'GET /orders/ -> Status: {response.status_code}')
            if response.status_code == 200:
                data = response.json()
                print(f'Response: {len(data)} orders found')
            else:
                print(f'Error: {response.text}')
        else:
            print('\n❌ No order routes found to test')

if __name__ == "__main__":
    test_lifespan() 