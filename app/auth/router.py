import datetime
import secrets
import bcrypt
import re
from fastapi import APIRouter, Depends, status, Response, Path, Request
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from starlette.responses import JSONResponse

from app.auth.models import User_model, Session_model
from app.auth.schemas import UserRegister, UserLogin, user_register_form, user_login_form
from db.db_depends import get_db
from app.auth.security import get_user

authRouter = APIRouter(prefix='/user', tags=['user, auth, profile'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
templates = Jinja2Templates(directory='templates')


@authRouter.get('/list')
async def get_all_users(db: Annotated[AsyncSession, Depends(get_db)]):
    users_list = await db.scalars(select(User_model).where(
        User_model.is_active == True
    ))
    return users_list.all()


@authRouter.get('/register')
async def get_register_page(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})


@authRouter.get('/login')
async def get_login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@authRouter.post('/register')
async def post_create_user(db: Annotated[AsyncSession, Depends(get_db)],
                           register_inp: UserRegister = Depends(user_register_form),
                           ):
    try:
        await db.execute(insert(User_model).values(
            username=register_inp.username,
            name=register_inp.name,
            email=register_inp.email,
            password=bcrypt_context.hash(register_inp.password),
        ))
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        match = re.search(r'Key\s*\((?P<value>[^)]+)\)=\([^)]+\)\s*already exists', str(e.orig))
        if match:
            value = match.group('value')
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={'message': f'Этот {value} уже занят'})

        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={'message': {e.orig}})
    return JSONResponse(
        status_code=200,
        content={"redirectUrl": "/"}
    )


@authRouter.post('/login')
async def post_login_user(db: Annotated[AsyncSession, Depends(get_db)],
                          response: Response,
                          login_inp: UserLogin = Depends(user_login_form)):
    user = await db.scalar(select(User_model)
                           .where(login_inp.username == User_model.username))
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Пользователь не найден"}
        )

    if not bcrypt.checkpw(login_inp.password.encode('utf-8'), user.password.encode('utf-8')):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Неверный пароль"}
        )

    session_token = secrets.token_hex(16)
    await db.execute(insert(Session_model).values(
        session_token=session_token,
        user_id=user.id,
        expires=datetime.datetime.now() + datetime.timedelta(hours=1)
    ))
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        secure=False,
        max_age=3600,
        samesite="strict",
    )
    await db.commit()
    return JSONResponse(
        status_code=200,
        content={"redirectUrl": "/"}
    )


@authRouter.get('/profile')
async def get_user_profile(user: User_model = Depends(get_user)):
    return f"hello {user.name}"


@authRouter.get('/sessions')
async def get_sessions_list(db: Annotated[AsyncSession, Depends(get_db)]):
    sessions = await db.scalars((select(Session_model)))
    return sessions.all()


@authRouter.post('/add_money/{amount}')
async def post_add_money_to_account(db: Annotated[AsyncSession, Depends(get_db)],
                                    user: User_model = Depends(get_user),
                                    amount: int = Path()):

    user.balance += amount
    username = user.username

    await db.commit()

    return {'status': status.HTTP_200_OK,
            'detail': f"Successfully add {amount} to {username}'s balance"}
