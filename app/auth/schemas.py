from fastapi import Form
from pydantic import BaseModel, Field, EmailStr


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    name: str = Field(min_length=3, max_length=30)
    email: EmailStr = Field(min_length=10, max_length=40)
    password: str = Field(min_length=8, max_length=30)


async def user_register_form(
        username: str = Form(),
        name: str = Form(),
        email: str = Form(),
        password: str = Form(),

) -> UserRegister:
    return UserRegister(
        username=username,
        name=name,
        email=email,
        password=password
    )


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=30)


async def user_login_form(
        username: str = Form(),
        password: str = Form(),

) -> UserLogin:
    return UserLogin(
        username=username,
        password=password
    )
