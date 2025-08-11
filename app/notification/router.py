from typing import Annotated

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.auth.models import UserModel
from app.auth.security import get_current_user_or_none
from app.notification.models import NotificationModel
from db.db_depends import get_db

notificationRouter = APIRouter(prefix='/notification', tags=['users', 'notifications'])


@notificationRouter.post('/check')
async def post_check_notifications(db: Annotated[AsyncSession, Depends(get_db)],
                                   user: UserModel | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/', status_code=303)

    await db.execute(update(NotificationModel)
                     .where(NotificationModel.notification_receiver_id == user.id,
                            ~NotificationModel.is_checked,
                            NotificationModel.type != 'request')
                     .values(is_checked=True))
    await db.commit()
