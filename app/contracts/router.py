import random
from typing import Annotated
from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, insert, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.templating import Jinja2Templates

from app.auth.models import User_model
from app.chat.models import Message_model
from app.contracts.schemas import ContractRequest
from app.models_associations import User_Skin_model
from app.auth.security import get_current_user_or_none
from app.notification.models import Notification_model
from app.skin.models import Skin_model
from db.db_depends import get_db

contractRouter = APIRouter(prefix='/contract', tags=['skins', 'contracts'])
templates = Jinja2Templates(directory='templates')


@contractRouter.get('/')
async def get_contract(request: Request,
                       db: Annotated[AsyncSession, Depends(get_db)],
                       user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/user/login')

    user_skins = await db.scalars(select(User_Skin_model).where(
        User_Skin_model.user_id == user.id,
        User_Skin_model.is_active,
    ).options(selectinload(User_Skin_model.skin))
     .order_by(desc('id')))

    notifications = await db.scalars(select(Notification_model)
                                     .where(Notification_model.notification_receiver_id == user.id,
                                            Notification_model.is_active)
                                     .order_by(desc(Notification_model.created)))

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

    return templates.TemplateResponse('contract.html',
                                      {'request': request,
                                       'user': user,
                                       'user_skins': user_skins.all(),
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })


@contractRouter.post('/')
async def post_contract(db: Annotated[AsyncSession, Depends(get_db)],
                        skins: ContractRequest,
                        user: User_model | None = Depends(get_current_user_or_none),
                        ):
    if not user:
        return RedirectResponse('/user/login')

    total_price = 0
    user_skins = await db.scalars(select(User_Skin_model).where(
        User_Skin_model.user_id == user.id,
        User_Skin_model.id.in_(skins.skins),
        User_Skin_model.is_active
    ).options(selectinload(User_Skin_model.skin)))

    user.contracts_cnt += 1
    user.activity_points += 30

    for skin in user_skins.all():
        skin.is_active = False
        total_price += skin.skin.price
    drop_price = random.randint(int(total_price * 0.6), int(total_price * 1.5))

    dropped_skin = await db.scalar(select(Skin_model).where(
        Skin_model.price < drop_price,
        Skin_model.is_active
    ).order_by(desc(Skin_model.price))
     .limit(1))

    if dropped_skin.price > total_price:
        user.successful_contracts_cnt += 1
        user.activity_points += 15

    result = await db.execute(insert(User_Skin_model).values(
        user_id=user.id,
        skin_id=dropped_skin.id
    ).returning(User_Skin_model.id))
    user_skin_id = result.scalar_one()

    await db.commit()

    dropped_skin_obj = await db.scalar(select(User_Skin_model)
                                       .where(User_Skin_model.id == user_skin_id)
                                       .options(selectinload(User_Skin_model.skin)))
    return {
        'status': status.HTTP_200_OK,
        'dropped_skin': user_skin_id,
        'dropped_skin_image': dropped_skin_obj.skin.image if dropped_skin_obj and dropped_skin_obj.skin else None,
        'dropped_skin_name': dropped_skin_obj.skin.name if dropped_skin_obj and dropped_skin_obj.skin else None,
        'dropped_skin_price': dropped_skin_obj.skin.price if dropped_skin_obj and dropped_skin_obj.skin else None
    }
