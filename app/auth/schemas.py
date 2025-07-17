from fastapi import Form, HTTPException, status
from pydantic import BaseModel, Field, EmailStr, ValidationError


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
    try:
        return UserRegister(
            username=username,
            name=name,
            email=email,
            password=password
        )
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = error["loc"][0]
            msg = error["msg"]
            error_type = error["type"]

            if error_type == "string_too_short":
                if field == "username":
                    msg = "Имя пользователя должно содержать минимум 3 символа"
                elif field == "password":
                    msg = "Пароль должен содержать минимум 8 символов"
                elif field == "name":
                    msg = "Имя должно содержать минимум 3 символа"
            elif error_type == "string_too_long":
                if field == "username":
                    msg = "Имя пользователя должно содержать максимум 30 символов"
                elif field == "password":
                    msg = "Пароль должен содержать максимум 30 символов"
                elif field == 'name':
                    msg = "Имя должно содержать максимум 30 символов"
            elif error_type == "too_short":
                if field == 'email':
                    msg = "Почта должна содержать минимум 10 символов"
            elif error_type == "too_long":
                if field == 'email':
                    msg = "Почта должна содержать максимум 40 символов"
            else:
                msg = 'Ошибка валидации'

            errors.append({
                "field": field,
                "message": msg,
                "type": error_type
            })

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Ошибка валидации данных",
                "errors": [errors]
            }
        )



class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=30)


async def user_login_form(
        username: str = Form(),
        password: str = Form(),

) -> UserLogin:
    try:
        return UserLogin(
            username=username,
            password=password
        )
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = error["loc"][0]
            msg = error["msg"]
            error_type = error["type"]

            if error_type == "string_too_short":
                if field == "username":
                    msg = "Имя пользователя должно содержать минимум 3 символа"
                elif field == "password":
                    msg = "Пароль должен содержать минимум 8 символов"
            elif error_type == "string_too_long":
                if field == "username":
                    msg = "Имя пользователя должно содержать максимум 30 символов"
                elif field == "password":
                    msg = "Пароль должен содержать максимум 30 символов"

            errors.append({
                "field": field,
                "message": msg,
                "type": error_type
            })

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Ошибка валидации данных",
                "errors": [errors]
            }
        )
