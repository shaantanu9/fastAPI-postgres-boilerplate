from .models import User
from sqlalchemy.future import select

async def get_users(db):
    result = await db.execute(select(User))
    return result.scalars().all()

async def create_user(db, name: str, email: str):
    user = User(name=name, email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
