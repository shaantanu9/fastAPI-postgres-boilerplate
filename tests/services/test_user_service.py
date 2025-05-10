import pytest
from app.services.user_service import UserService
from app.db.models.user import User

@pytest.mark.asyncio
async def test_create_and_get_user_service(db_session):
    # Create user
    user = await UserService.create_user(db_session, name="Bob", email="bob@example.com")
    assert isinstance(user, User)
    assert user.name == "Bob"
    assert user.email == "bob@example.com"

    # Get users
    users = await UserService.get_users(db_session)
    assert any(u.email == "bob@example.com" for u in users)
