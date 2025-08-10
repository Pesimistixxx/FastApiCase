from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.models import UserModel
from app.auth.security import get_current_user_or_none
from app.case.models import CaseModel
from app.utils.db_queries import get_user_notifications, get_user_new_notifications, get_unread_messages
from db.db_depends import get_db

adminRouter = APIRouter(prefix='/admin', tags=['admin'])
templates = Jinja2Templates(directory='templates')


@adminRouter.get('')
async def get_admin_panel(request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          user: UserModel | None = Depends(get_current_user_or_none)):
    if not user or not user.is_admin:
        return RedirectResponse('/')

    cases = await db.scalars(select(CaseModel)
                             .options(joinedload(CaseModel.author))
                             .order_by(CaseModel.is_approved))

    notifications = await get_user_notifications(db, user.id)
    new_notifications = await get_user_new_notifications(db, user.id)
    new_messages = await get_unread_messages(db, user.id)

    return templates.TemplateResponse('admin.html',
                                      {'request': request,
                                       'user': user,
                                       'cases': cases.all(),
                                       'notifications': notifications.all(),
                                       'notifications_cnt': len(new_notifications.all()),
                                       'new_messages_cnt': len(new_messages.all())
                                       })
