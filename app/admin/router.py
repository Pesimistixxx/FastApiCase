from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.models import User_model
from app.auth.security import get_current_user_or_none
from app.case.models import Case_model
from app.chat.models import Message_model
from app.notification.models import Notification_model
from db.db_depends import get_db

adminRouter = APIRouter(prefix='/admin', tags=['admin'])
templates = Jinja2Templates(directory='templates')


@adminRouter.get('')
async def get_admin_panel(request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          user: User_model | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        return RedirectResponse('/')

    cases = await db.scalars(select(Case_model)
                             .options(joinedload(Case_model.author))
                             .order_by(Case_model.is_approved))
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
    return templates.TemplateResponse('admin.html',
                                      {'request': request,
                                       'user': user,
                                       'cases': cases.all(),
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })
