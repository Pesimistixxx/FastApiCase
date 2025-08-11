import datetime
import json
from typing import Annotated
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Request, Path, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect, WebSocket
from fastapi.websockets import WebSocketState

from app.achievement.models import AchievementModel
from app.auth.models import UserModel, FriendsModel
from app.auth.security import get_current_user_or_none, verify_session
from app.chat.chat_manager import chat_manager
from app.chat.models import ChatModel, MessageModel
from app.chat.schemas import SendMessage, EditMessage
from app.models_associations import UserChatModel, UserAchievementModel
from app.notification.models import NotificationModel
from app.utils.db_queries import get_user_notifications, get_unread_messages, get_user_new_notifications
from db.db_depends import get_db
from wordle_tracker.models import WordleModel

chatRouter = APIRouter(prefix='/chat', tags=['user, chat, messages'])
templates = Jinja2Templates(directory='templates')


@chatRouter.get('/list')
async def get_chat_list(db: Annotated[AsyncSession, Depends(get_db)],
                        request: Request,
                        user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    last_msg_subquery = (
        select(
            MessageModel.chat_id,
            func.max(MessageModel.id).label('last_msg_id')
        )
        .group_by(MessageModel.chat_id)
        .subquery()
    )

    unread_count_subquery = (
        select(
            MessageModel.chat_id,
            func.count(MessageModel.id).label('unread_count')  # pylint: disable=not-callable
        )
        .where(
            MessageModel.author_id != user.id,
            ~MessageModel.is_checked
        )
        .group_by(MessageModel.chat_id)
        .subquery()
    )

    stmt = (
        select(
            ChatModel,
            UserChatModel.unread_messages,
            MessageModel.message,
            MessageModel.message_date,
            MessageModel.author_id,
            func.coalesce(unread_count_subquery.c.unread_count, 0).label('unread_count')
        )
        .join(UserChatModel, UserChatModel.chat_id == ChatModel.id)
        .outerjoin(last_msg_subquery, last_msg_subquery.c.chat_id == ChatModel.id)
        .outerjoin(MessageModel, MessageModel.id == last_msg_subquery.c.last_msg_id)
        .outerjoin(unread_count_subquery, unread_count_subquery.c.chat_id == ChatModel.id)
        .where(UserChatModel.user_id == user.id)
        .options(
            selectinload(ChatModel.users_associations).joinedload(UserChatModel.user)
        )
    )

    result = await db.execute(stmt)
    chat_data = []

    for row in result:
        chat = row[0]
        last_msg = row[2]
        last_msg_date = row[3]
        last_author_id = row[4]
        unread_count = row[5]

        other_user = next(
            (assoc.user for assoc in chat.users_associations
             if assoc.user_id != user.id),
            None
        )

        chat_data.append({
            'id': chat.id,
            'other_user': other_user,
            'unread_count': unread_count,
            'last_message': {
                'message': last_msg,
                'message_date': last_msg_date,
                'author_id': last_author_id
            } if last_msg else None
        })

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('chat_list.html', {
        'datetime': datetime.datetime,
        'request': request,
        'user': user,
        'chats': chat_data,
        'notifications': notifications.all(),
        'notifications_cnt': len(new_notifications.all()),
        'new_messages_cnt': len(new_messages.all())
    })


@chatRouter.get('/{chat_id}')
async def get_chat_by_id(db: Annotated[AsyncSession, Depends(get_db)],
                         request: Request,
                         user: UserModel | None = Depends(get_current_user_or_none),
                         chat_id: int = Path()):
    if not user:
        return RedirectResponse('/')

    chat = await db.scalar(select(ChatModel)
                           .where(ChatModel.id == chat_id)
                           .options(selectinload(ChatModel.users_associations)
                                    .selectinload(UserChatModel.user)))
    if not chat:
        return RedirectResponse('/')

    users = [user.user_id for user in chat.users_associations]
    if user.id not in users:
        return RedirectResponse('/')

    friends = await db.scalar(select(FriendsModel)
                              .where(FriendsModel.first_user_id == min(users),
                                     FriendsModel.second_user_id == max(users),
                                     FriendsModel.is_accepted))

    other_user = None
    for association in chat.users_associations:
        if association.user.id != user.id:
            other_user = association.user
            break

    result = await db.execute(
        select(MessageModel)
        .where(MessageModel.chat_id == chat_id,
               ~MessageModel.is_checked,
               MessageModel.author_id != user.id)
    )
    updated_messages = result.scalars().all()

    for message in updated_messages:
        message.is_checked = True
        await chat_manager.broadcast(
            chat_id=chat_id,
            message={
                "type": "message_read",
                "data": {"id": message.id}
            }
        )

    await db.commit()

    messages = await db.scalars(
        select(MessageModel)
        .where(MessageModel.chat_id == chat_id,
               MessageModel.is_active)
        .order_by(MessageModel.message_date.asc())
    )
    messages = messages.all()

    await db.refresh(user)
    await db.refresh(chat)
    await db.refresh(other_user)

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('chat.html',
                                      {'request': request,
                                       'user': user,
                                       'other_user': other_user,
                                       'messages': messages,
                                       'chat_id': chat.id,
                                       'is_active': friends is not None,
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@chatRouter.post('/{chat_id}/send')
async def post_send_message(db: Annotated[AsyncSession, Depends(get_db)],
                            message: SendMessage,
                            user: UserModel | None = Depends(get_current_user_or_none),
                            chat_id: int = Path(),
                            ):
    if not user:
        return RedirectResponse('/', status_code=303)

    chat = await db.scalar(select(ChatModel)
                           .where(ChatModel.id == chat_id)
                           .options(selectinload(ChatModel.users_associations)
                                    .selectinload(UserChatModel.user)))
    if not chat:
        return RedirectResponse('/', status_code=303)

    users = [user.user_id for user in chat.users_associations]

    friends = await db.scalar(select(FriendsModel)
                              .where(FriendsModel.first_user_id == min(users),
                                     FriendsModel.second_user_id == max(users),
                                     FriendsModel.is_accepted))
    if not friends:
        return RedirectResponse('/chat/list', status_code=303)

    if user.id not in users:
        return RedirectResponse('/', status_code=303)

    result = await db.execute(insert(MessageModel).values(
        chat_id=chat.id,
        author_id=user.id,
        message=message.message,
        message_date=datetime.datetime.now()
    ).returning(MessageModel.id))
    message_id = result.scalars().one()

    wordle_word = await db.scalar(
        select(WordleModel)
        .order_by(WordleModel.created.desc())
        .limit(1)
    )
    if message.message == wordle_word.word:
        achievement = await db.scalar(
            select(AchievementModel).where(AchievementModel.name == 'Пользователь @WordleCrackerBot')
        )
        exists_query = select(UserAchievementModel).where(
            UserAchievementModel.achievement_id == achievement.id,
            UserAchievementModel.user_id == user.id
        )
        user_achievement = await db.scalar(exists_query)
        if not user_achievement:
            await db.execute(
                insert(NotificationModel).values(
                    notification_receiver_id=user.id,
                    type='achievement',
                    text='Поздравляем, вы получили достижение Пользователь @WordleCrackerBot'
                )
            )
            user.achievements_cnt += 1
            await db.execute(
                insert(UserAchievementModel).values(
                    user_id=user.id,
                    achievement_id=achievement.id
                )
            )

    message_response = {
        "type": "new_message",
        "data": {
            "id": message_id,
            "chat_id": chat.id,
            "author_id": user.id,
            "message": message.message,
            "message_date": datetime.datetime.now().isoformat(),
            "is_edited": False
        }
    }
    await chat_manager.broadcast(chat_id=chat_id, message=message_response, exclude_user_id=user.id)
    await db.commit()
    return {'status': status.HTTP_201_CREATED,
            'id': message_id}


@chatRouter.delete('/{message_id}/delete')
async def delete_message(db: Annotated[AsyncSession, Depends(get_db)],
                         user: UserModel | None = Depends(get_current_user_or_none),
                         message_id: int = Path()):
    if not user:
        return RedirectResponse('/', status_code=303)

    message = await db.scalar(select(MessageModel)
                              .where(MessageModel.id == message_id))

    if not message or message.author_id != user.id:
        return RedirectResponse('/', status_code=303)

    message.is_active = False
    chat_id = message.chat_id

    delete_response = {
        "type": "delete_message",
        "data": {
            "id": message_id
        }
    }

    await chat_manager.broadcast(chat_id=chat_id, message=delete_response)
    await db.commit()


@chatRouter.patch('/{message_id}/edit')
async def patch_edit_message(db: Annotated[AsyncSession, Depends(get_db)],
                             edit_message: EditMessage,
                             user: UserModel | None = Depends(get_current_user_or_none),
                             message_id: int = Path()):
    if not user:
        return RedirectResponse('/', status_code=303)

    message = await db.scalar(select(MessageModel)
                              .where(MessageModel.id == message_id))

    if not message or message.author_id != user.id:
        return RedirectResponse('/', status_code=303)

    message.message = edit_message.message
    message.is_edited = True

    update_response = {
        "type": "update_message",
        "data": {
            "id": message_id,
            "message": edit_message.message,
            "is_edited": True,
            "new_date": datetime.datetime.now().isoformat()
        }
    }

    chat_id = message.chat_id
    await chat_manager.broadcast(chat_id=chat_id, message=update_response)
    await db.commit()


@chatRouter.websocket('/{chat_id}/ws')
async def websocket_chat(websocket: WebSocket,
                         db: AsyncSession = Depends(get_db),
                         chat_id: int = Path()):
    cookies = websocket.cookies
    session_cookie = cookies.get('session_id')
    if not session_cookie:
        await websocket.close(code=1008)
        return

    try:
        user = await verify_session(session_cookie, db)
        if not user:
            await websocket.close(code=1008)
            return

    except Exception as e:
        print(f"Session verification error: {e}")
        await websocket.close(code=1008)
        return

    chat = await db.scalar(
        select(ChatModel)
        .where(ChatModel.id == chat_id)
        .options(selectinload(ChatModel.users_associations))
    )
    if not chat:
        await websocket.close(code=1003)
        return

    user_in_chat = any(assoc.user_id == user.id for assoc in chat.users_associations)
    if not user_in_chat:
        await websocket.close(code=1008)
        return

    await chat_manager.connect(chat_id, websocket, user.id)
    await chat_manager.send_user_activity(chat_id, user.id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)

                if message.get("type") == "typing":
                    await chat_manager.send_typing_status(
                        chat_id,
                        user.id,
                        message.get("is_typing", False)
                    )

                elif message.get("type") == "new_message":
                    text = message.get("text", "").strip()
                    if text:
                        new_message = MessageModel(
                            chat_id=chat_id,
                            author_id=user.id,
                            message=text,
                            is_checked=False
                        )
                        db.add(new_message)
                        await db.commit()
                        await db.refresh(new_message)

                        await chat_manager.broadcast(
                            chat_id=chat_id,
                            message={
                                "type": "new_message",
                                "data": {
                                    "id": new_message.id,
                                    "author_id": user.id,
                                    "message": text,
                                    "message_date": new_message.message_date.isoformat(),
                                    "is_edited": False,
                                    "is_checked": False
                                }
                            }
                        )
                if message.get("type") == "activity":
                    await chat_manager.send_user_activity(chat_id, user.id)

                if message.get("type") == "read_messages":
                    await db.execute(
                        update(MessageModel)
                        .where(
                            MessageModel.chat_id == chat_id,
                            MessageModel.author_id != user.id,
                            ~MessageModel.is_checked
                        )
                        .values(is_checked=True)
                    )
                    await db.commit()

                    await chat_manager.broadcast(
                        chat_id=chat_id,
                        message={"type": "messages_read", "user_id": user.id}
                    )

            except json.JSONDecodeError:
                print("Invalid JSON received")

    except WebSocketDisconnect as e:
        if e.code not in (1000, 1001):
            await chat_manager.schedule_disconnect(chat_id, user.id)
    except Exception as e:
        print(f"Unexpected error in WebSocket: {e}")
        await chat_manager.schedule_disconnect(chat_id, user.id)
    finally:
        await chat_manager.disconnect_by_user(chat_id, user.id)

        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=1000)
            except Exception:
                pass


@chatRouter.post('/{chat_id}/mark_read')
async def mark_messages_read(
        db: Annotated[AsyncSession, Depends(get_db)],
        user: UserModel | None = Depends(get_current_user_or_none),
        chat_id: int = Path()
):
    if not user:
        return {"status": "error", "message": "Unauthorized"}

    result = await db.execute(
        select(MessageModel)
        .where(
            MessageModel.chat_id == chat_id,
            ~MessageModel.is_checked,
            MessageModel.author_id != user.id
        )
    )
    unread_messages = result.scalars().all()

    if not unread_messages:
        return {"status": "success", "message": "No unread messages"}

    message_ids = [msg.id for msg in unread_messages]
    await db.execute(
        update(MessageModel)
        .where(MessageModel.id.in_(message_ids))
        .values(is_checked=True)
    )
    await db.commit()

    await chat_manager.broadcast(
        chat_id=chat_id,
        message={
            "type": "messages_read",
            "data": {"ids": message_ids}
        }
    )

    return {"status": "success", "count": len(message_ids)}
