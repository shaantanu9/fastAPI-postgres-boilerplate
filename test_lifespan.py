from fastapi.testclient import TestClient

from app.main import app


def test_lifespan() -> None:

    # Create test client which should trigger lifespan
    with TestClient(app) as client:
        # Check routes after lifespan
        order_routes = [
            r for r in app.routes if hasattr(r, "path") and "/orders" in r.path
        ]

        for route in order_routes:
            (
                ", ".join(route.methods) if hasattr(route, "methods") else "Unknown"
            )

        # Test a simple GET request
        if order_routes:
            response = client.get("/orders/")
            if response.status_code == 200:
                response.json()
            else:
                pass
        else:
            pass


if __name__ == "__main__":
    test_lifespan()
