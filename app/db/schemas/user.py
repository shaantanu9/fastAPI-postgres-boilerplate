from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    name: str
    email: str
    roles: str = "user"
    is_active: int = 1

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    email: str
    name: str
    roles: str
    is_active: int

    class Config:
        from_attributes = True

class UserInDB(UserRead):
    hashed_password: str
    class Config:
        from_attributes = True
