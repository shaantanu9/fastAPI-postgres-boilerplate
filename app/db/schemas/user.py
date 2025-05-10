from pydantic import BaseModel

from pydantic import EmailStr, Field, constr

class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    name: constr(min_length=1, max_length=100)
    email: EmailStr
    roles: str = "user"
    is_active: int = 1

class UserCreate(UserBase):
    password: constr(min_length=8, max_length=128)

class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True

class UserInDB(UserRead):
    hashed_password: str
    class Config:
        from_attributes = True
