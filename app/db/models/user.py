from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)  # New username field
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    password = Column(String, nullable=True)  # New plain password field (not recommended for production)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    roles = Column(String, default="user")  # Comma-separated roles
