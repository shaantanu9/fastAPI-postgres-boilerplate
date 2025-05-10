import pytest
from app.db.crud.user import create_user, get_users
from app.db.models.user import User

@pytest.mark.asyncio
async def test_create_and_get_user_crud_file(db_session):
    # Create user
    user = await create_user(db_session, name="Carol", email="carol@example.com")
    assert isinstance(user, User)
    assert user.name == "Carol"
    assert user.email == "carol@example.com"

    # Get users
    users = await get_users(db_session)
    assert any(u.email == "carol@example.com" for u in users)
