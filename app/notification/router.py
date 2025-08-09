from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import RedirectResponse

from app.auth.models import User_model
from app.auth.security import get_current_user_or_none
from app.notification.models import Notification_model
from db.db_depends import get_db

notificationRouter = APIRouter(prefix='/notification', tags=['users', 'notifications'])


@notificationRouter.post('/check')
async def post_check_notifications(db: Annotated[AsyncSession, Depends(get_db)],
                                   user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/', status_code=303)

    await db.execute(update(Notification_model)
                     .where(Notification_model.notification_receiver_id == user.id,
                            ~Notification_model.is_checked,
                            Notification_model.type == 'text')
                     .values(is_checked=True))
    await db.commit()
