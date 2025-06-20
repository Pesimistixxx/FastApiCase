import datetime
import secrets
import bcrypt
from fastapi import APIRouter, Depends, status, HTTPException, Response
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from app.auth.models import User_model, Session_model
from app.auth.schemas import UserRegister, UserLogin
from db.db_depends import get_db
from app.auth.security import get_user

authRouter = APIRouter(prefix='/user', tags=['user, auth, profile'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


@authRouter.get('/list')
async def get_all_users(db: Annotated[AsyncSession, Depends(get_db)]):
    users_list = await db.scalars(select(User_model).where(
        User_model.is_active == True
    ))
    return users_list.all()


@authRouter.post('/register')
async def post_create_user(db: Annotated[AsyncSession, Depends(get_db)],
                           user_inp: UserRegister):
    try:
        await db.execute(insert(User_model).values(
            username=user_inp.username,
            name=user_inp.name,
            email=user_inp.email,
            password=bcrypt_context.hash(user_inp.password),
        ))
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f'{e.orig}')
    return {
        'status_code': status.HTTP_201_CREATED,
        'comment': 'successfully!'
    }


@authRouter.post('/login')
async def post_login_user(db: Annotated[AsyncSession, Depends(get_db)],
                          user_inp: UserLogin,
                          response: Response):
    user = await db.scalar(select(User_model)
                           .where(user_inp.username == User_model.username))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not bcrypt.checkpw(user_inp.password.encode('utf-8'), user.password.encode('utf-8')):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

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
    return "Welcome"


@authRouter.get('/profile')
async def get_user_profile(user: str = Depends(get_user)):
    return f"hello {user}"
