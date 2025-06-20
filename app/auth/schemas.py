from pydantic import BaseModel, Field, EmailStr


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    name: str = Field(min_length=3, max_length=30)
    email: EmailStr = Field(min_length=10, max_length=40)
    password: str = Field(min_length=8, max_length=30)


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=30)