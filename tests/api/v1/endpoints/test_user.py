import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_and_get_user_endpoint(client):
    # Create user
    response = await client.post("/api/v1/users", json={"name": "Alice", "email": "alice@example.com"})
    assert response.status_code == 200 or response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"

    # Get users
    response = await client.get("/api/v1/users")
    assert response.status_code == 200
    users = response.json()
    assert any(u["email"] == "alice@example.com" for u in users)
