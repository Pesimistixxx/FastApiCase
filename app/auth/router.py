import datetime
import secrets
import bcrypt
import re
from fastapi import APIRouter, Depends, status, Path, Request, Response
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, desc, delete
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse, RedirectResponse

from app.auth.models import User_model, Session_model
from app.auth.schemas import UserRegister, UserLogin
from app.case.models import Case_model
from db.db_depends import get_db
from app.auth.security import get_user, get_current_user_or_none
from app.models_associations import User_Skin_model

authRouter = APIRouter(prefix='/user', tags=['user, auth, profile'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
templates = Jinja2Templates(directory='templates')


@authRouter.get('/list')
async def get_all_users(db: Annotated[AsyncSession, Depends(get_db)],
                        user: User_model | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        return RedirectResponse('/')
    users_list = await db.scalars(select(User_model).where(
        User_model.is_active
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
                           register_inp: UserRegister,
                           ):
    try:
        user = User_model(
            username=register_inp.username,
            name=register_inp.name,
            email=register_inp.email,
            password=bcrypt_context.hash(register_inp.password),
        )
        db.add(user)
        await db.flush()

    except IntegrityError as e:
        await db.rollback()
        match = re.search(r'Key\s*\((?P<value>[^)]+)\)=\([^)]+\)\s*already exists', str(e.orig))
        if match:
            value = match.group('value')
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={'message': f'Этот {value} уже занят'})

        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={'message': {e.orig}})

    session_token = secrets.token_hex(16)
    await db.execute(insert(Session_model).values(
        session_token=session_token,
        user_id=user.id,
        expires=datetime.datetime.now() + datetime.timedelta(hours=24)
    ))
    await db.commit()
    response = RedirectResponse('/', status_code=303)
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        secure=True,
        max_age=86400,
        samesite="lax",
        path='/'
    )

    return response


@authRouter.post('/login')
async def post_login_user(db: Annotated[AsyncSession, Depends(get_db)],
                          login_inp: UserLogin):
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
        expires=datetime.datetime.now() + datetime.timedelta(hours=24)
    ))
    await db.commit()

    response = RedirectResponse('/', status_code=303)
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        secure=False,
        max_age=86400,
        samesite="lax",
        path='/'
    )

    return response


@authRouter.get('/profile')
async def get_user_profile(request: Request,
                           db: Annotated[AsyncSession, Depends(get_db)],
                           user: User_model = Depends(get_current_user_or_none)
                           ):
    if not user:
        return RedirectResponse('/')
    all_skins = await db.scalars(
        select(User_Skin_model)
        .where(
            User_Skin_model.user_id == user.id,
            User_Skin_model.is_active
        )
        .options(selectinload(User_Skin_model.skin))
        .order_by(desc(User_Skin_model.id))
    )
    all_skins_list = all_skins.all()
    my_cases = await db.scalars(select(Case_model)
                                .where(Case_model.author_id == user.id)
                                .order_by(Case_model.is_approved))
    total_sum = sum(skin.skin.price for skin in all_skins_list)

    return templates.TemplateResponse("my_profile.html",
                                      {
                                          "request": request,
                                          "username": user.username,
                                          "balance": user.balance,
                                          "last_skins": all_skins_list,
                                          "skins_price": total_sum,
                                          "avatar": user.avatar,
                                          "my_cases": my_cases.all(),
                                          'is_admin': user.is_admin
                                      })


@authRouter.get('/sessions')
async def get_sessions_list(db: Annotated[AsyncSession, Depends(get_db)],
                            user: User_model | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        return RedirectResponse('/')
    sessions = await db.scalars((select(Session_model)))
    return sessions.all()


@authRouter.post('/add_money/{amount}')
async def post_add_money_to_account(db: Annotated[AsyncSession, Depends(get_db)],
                                    user: User_model = Depends(get_user),
                                    amount: float = Path()):
    new_balance = user.balance + amount
    user.balance = new_balance
    username = user.username

    await db.commit()

    return {'status': status.HTTP_200_OK,
            'new_balance': new_balance,
            'detail': f"Successfully add {amount} to {username}'s balance"}


@authRouter.post('/logout')
async def logout_user(db: Annotated[AsyncSession, Depends(get_db)],
                      response: Response,
                      user: User_model = Depends(get_user)
                      ):
    await db.execute(delete(Session_model).where(
        Session_model.user_id == user.id
    ))
    await db.commit()

    response.delete_cookie(
        key='session_id',
        path='/',
        samesite='lax',
        httponly=True,
        secure=False
    )

    return RedirectResponse('/user/login', status_code=303)


@authRouter.get('/profile/{username}')
async def get_another_user_profile(request: Request,
                                   db: Annotated[AsyncSession, Depends(get_db)],
                                   user: User_model | None = Depends(get_current_user_or_none),
                                   username: str = Path()):
    profile_user = await db.scalar(select(User_model)
                                   .where(User_model.is_active,
                                          User_model.username == username))
    if not profile_user:
        return RedirectResponse('/')

    profile_cases = await db.scalars(select(Case_model)
                                     .where(Case_model.author_id == profile_user.id,
                                            Case_model.is_active,
                                            Case_model.is_approved))

    if user:
        return templates.TemplateResponse('user_profile.html', {'request': request,
                                                                'user': user,
                                                                'balance': user.balance,
                                                                'user_username': user.username,
                                                                'user_avatar': user.avatar,
                                                                'is_admin': user.is_admin,
                                                                'profile_cases': profile_cases.all(),
                                                                'profile_username': profile_user.username,
                                                                'name': profile_user.name,
                                                                'profile_avatar': profile_user.avatar,
                                                                'activity': profile_user.activity_points,
                                                                'cases_opened': profile_user.case_opened,
                                                                'upgrades_cnt': profile_user.upgrades_cnt,
                                                                'contracts_cnt': profile_user.contracts_cnt,
                                                                })
    return templates.TemplateResponse('user_profile.html', {'request': request,
                                                            'profile_cases': profile_cases.all(),
                                                            'profile_username': profile_user.username,
                                                            'name': profile_user.name,
                                                            'profile_avatar': profile_user.avatar,
                                                            'activity': profile_user.activity_points,
                                                            'cases_opened': profile_user.case_opened,
                                                            'upgrades_cnt': profile_user.upgrades_cnt,
                                                            'contracts_cnt': profile_user.contracts_cnt,
                                                            })
