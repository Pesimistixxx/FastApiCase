import datetime
import secrets
import bcrypt
import re
from fastapi import APIRouter, Depends, status, Path, Request, Response
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, desc, delete, update, func
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse, RedirectResponse

from app.auth.models import User_model, Session_model, Friends_model
from app.auth.schemas import UserRegister, UserLogin
from app.case.models import Case_model
from app.chat.models import Chat_model, Message_model
from app.notification.models import Notification_model
from db.db_depends import get_db
from app.auth.security import get_user, get_current_user_or_none
from app.models_associations import User_Skin_model, User_Chat_model

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

    notifications = await db.scalars(select(Notification_model)
                                     .where(Notification_model.notification_receiver_id == user.id,
                                            Notification_model.is_active)
                                     .order_by(desc(Notification_model.created))
                                     .options(selectinload(Notification_model.notification_sender)))

    new_notifications = await db.scalars(select(Notification_model)
                                         .where(Notification_model.notification_receiver_id == user.id,
                                                Notification_model.is_active,
                                                ~Notification_model.is_checked)
                                         .order_by(Notification_model.created))
    new_messages = await db.scalars(
        select(
            Message_model.chat_id,
            func.count(Message_model.id).label('unread_count')
        )
        .where(
            Message_model.author_id != user.id,
            ~Message_model.is_checked
        )
        .group_by(Message_model.chat_id)
    )

    return templates.TemplateResponse("my_profile.html",
                                      {
                                          "request": request,
                                          "user": user,
                                          "last_skins": all_skins_list,
                                          "skins_price": total_sum,
                                          "my_cases": my_cases.all(),
                                          'notifications_cnt': len(new_notifications.all()),
                                          'new_messages_cnt': len(new_messages.all()),
                                          'notifications': notifications.all(),
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
        notifications = await db.scalars(select(Notification_model)
                                         .where(Notification_model.notification_receiver_id == user.id,
                                                Notification_model.is_active)
                                         .options(selectinload(Notification_model.notification_sender))
                                         .order_by(desc(Notification_model.created)))

        new_notifications = await db.scalars(select(Notification_model)
                                             .where(Notification_model.notification_receiver_id == user.id,
                                                    Notification_model.is_active,
                                                    ~Notification_model.is_checked)
                                             .order_by(Notification_model.created))

        friend_request = await db.scalar(select(Friends_model)
                                         .where(Friends_model.first_user_id == min(profile_user.id, user.id),
                                                Friends_model.second_user_id == max(profile_user.id, user.id)))
        new_messages = await db.scalars(select(User_Chat_model)
                                        .where(User_Chat_model.user_id == user.id,
                                               User_Chat_model.unread_messages > 0))
        return templates.TemplateResponse('user_profile.html', {'request': request,
                                                                'user': user,
                                                                'profile_user': profile_user,
                                                                'profile_cases': profile_cases.all(),
                                                                'friend_request': friend_request,
                                                                'notifications': notifications.all(),
                                                                'notifications_cnt': len(new_notifications.all()),
                                                                'new_messages_cnt': len(new_messages.all())
                                                                })

    return templates.TemplateResponse('user_profile.html', {'request': request,
                                                            'profile_cases': profile_cases.all(),
                                                            'user': None,
                                                            'profile_user': profile_user,
                                                            })


@authRouter.post('/request/{username}')
async def post_request_friend(db: Annotated[AsyncSession, Depends(get_db)],
                              user: User_model | None = Depends(get_current_user_or_none),
                              username: str = Path()):
    if not user:
        return RedirectResponse('/', status_code=303)

    friend_user = await db.scalar(select(User_model)
                                  .where(User_model.is_active,
                                         User_model.username == username))
    if not friend_user:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'user not found'
        }

    await db.execute(insert(Friends_model)
                     .values(first_user_id=min(friend_user.id, user.id),
                             second_user_id=max(friend_user.id, user.id),
                             requester_id=user.id))
    await db.execute(insert(Notification_model)
                     .values(text=f'{user.username} хочет добавить вас в друзья',
                             type='request',
                             notification_receiver_id=friend_user.id,
                             notification_sender_id=user.id
                             ))
    await db.commit()
    return {'status': status.HTTP_200_OK,
            'detail': 'request created'}


@authRouter.post('/accept/{username}')
async def post_accept_friend(db: Annotated[AsyncSession, Depends(get_db)],
                             user: User_model | None = Depends(get_current_user_or_none),
                             username: str = Path()):
    if not user:
        return RedirectResponse('/', status_code=303)

    friend_user = await db.scalar(select(User_model)
                                  .where(User_model.is_active,
                                         User_model.username == username))

    if not friend_user:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'user not found'
        }

    friend_request = await db.scalar(select(Friends_model)
                                     .where(Friends_model.first_user_id == min(friend_user.id, user.id),
                                            Friends_model.second_user_id == max(friend_user.id, user.id),
                                            ~Friends_model.is_accepted,
                                            Friends_model.requester_id != user.id))
    if not friend_request:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'request not found'
        }
    await db.execute(update(Notification_model)
                     .where(Notification_model.notification_sender_id == friend_user.id,
                            Notification_model.notification_receiver_id == user.id,
                            Notification_model.type == 'request',
                            Notification_model.is_active)
                     .values(is_active=False))
    friend_request.is_accepted = True
    await db.execute(insert(Notification_model)
                     .values(text=f'{user.username} принял вашу заявку в друзья',
                             type='text',
                             notification_receiver_id=friend_user.id,
                             notification_sender_id=user.id
                             ))

    existing_chat_query = (
        select(User_Chat_model.chat_id)
        .where(User_Chat_model.user_id.in_([user.id, friend_user.id]))
        .group_by(User_Chat_model.chat_id)
        .having(func.count() == 2)
    )
    existing_chat = await db.execute(existing_chat_query)
    existing_chat_id = existing_chat.scalar_one_or_none()

    if existing_chat_id is None:
        result = await db.execute(insert(Chat_model).returning(Chat_model.id))
        chat_id = result.scalar_one()
        await db.execute(insert(User_Chat_model).values(
            [
                {'chat_id': chat_id, 'user_id': user.id},
                {'chat_id': chat_id, 'user_id': friend_user.id}
            ]
        ))

    await db.commit()


@authRouter.post('/reject/{username}')
async def post_reject_friend(db: Annotated[AsyncSession, Depends(get_db)],
                             user: User_model | None = Depends(get_current_user_or_none),
                             username: str = Path()):
    if not user:
        return RedirectResponse('/', status_code=303)

    friend_user = await db.scalar(select(User_model)
                                  .where(User_model.is_active,
                                         User_model.username == username))

    if not friend_user:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'user not found'
        }

    friend_request = await db.scalar(select(Friends_model)
                                     .where(Friends_model.first_user_id == min(friend_user.id, user.id),
                                            Friends_model.second_user_id == max(friend_user.id, user.id),
                                            ~Friends_model.is_accepted,
                                            Friends_model.requester_id != user.id))
    if not friend_request:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'request not found'
        }
    await db.execute(delete(Friends_model)
                     .where(Friends_model.first_user_id == min(friend_user.id, user.id),
                            Friends_model.second_user_id == max(friend_user.id, user.id),
                            ~Friends_model.is_accepted,
                            Friends_model.requester_id != user.id))

    await db.execute(update(Notification_model)
                     .where(Notification_model.notification_sender_id == friend_user.id,
                            Notification_model.notification_receiver_id == user.id,
                            Notification_model.type == 'request',
                            Notification_model.is_active)
                     .values(is_active=False))

    await db.execute(insert(Notification_model)
                     .values(text=f'{user.username} отклонил вашу заявку в друзья',
                             type='text',
                             notification_receiver_id=friend_user.id,
                             notification_sender_id=user.id
                             ))

    await db.commit()


@authRouter.post('/cancel/{username}')
async def post_request_friend_cancel(db: Annotated[AsyncSession, Depends(get_db)],
                                     user: User_model | None = Depends(get_current_user_or_none),
                                     username: str = Path()):
    if not user:
        return RedirectResponse('/', status_code=303)

    friend_user = await db.scalar(select(User_model)
                                  .where(User_model.is_active,
                                         User_model.username == username))
    if not friend_user:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'user not found'
        }

    await db.execute(delete(Friends_model)
                     .where(Friends_model.first_user_id == min(friend_user.id, user.id),
                            Friends_model.second_user_id == max(friend_user.id, user.id),
                            Friends_model.requester_id == user.id))

    await db.execute(delete(Notification_model)
                     .where(Notification_model.notification_receiver_id == friend_user.id,
                            Notification_model.text == f'{user.username} хочет добавить вас в друзья',
                            Notification_model.is_active))
    await db.commit()
    return {'status': status.HTTP_200_OK,
            'detail': 'request created'}


@authRouter.post('/friend/delete/{username}')
async def post_friend_delete(db: Annotated[AsyncSession, Depends(get_db)],
                             user: User_model | None = Depends(get_current_user_or_none),
                             username: str = Path()):
    if not user:
        return RedirectResponse('/', status_code=303)

    friend_user = await db.scalar(select(User_model)
                                  .where(User_model.is_active,
                                         User_model.username == username))
    if not friend_user:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'user not found'
        }

    friend_record = await db.scalar(select(Friends_model).where(
        Friends_model.first_user_id == min(user.id, friend_user.id),
        Friends_model.second_user_id == max(user.id, friend_user.id),
        Friends_model.is_accepted
    ))

    if not friend_record:
        return {
            'status': status.HTTP_404_NOT_FOUND,
            'detail': 'friendship not found'
        }

    await db.delete(friend_record)

    await db.execute(insert(Notification_model)
                     .values(text=f'{user.username} удалил вас из друзей :(',
                             type='text',
                             notification_receiver_id=friend_user.id,
                             notification_sender_id=user.id
                             ))
    await db.commit()
